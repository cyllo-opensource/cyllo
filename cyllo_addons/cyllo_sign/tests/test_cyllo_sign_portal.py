# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64
import uuid
from unittest.mock import patch, MagicMock

from odoo import http
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.addons.cyllo_sign.controllers import cyllo_sign_portal
from odoo.addons.cyllo_sign.controllers.cyllo_sign_portal import SignRequestPortal


@tagged('-at_install', 'post_install')
class TestCylloSignPortal(HttpCase):
    """
    Test suite for verifying portal functionality in the Sign Request module.
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepare test data for all portal sign request routes.

        Creates:
            - Portal user linked to a partner.
            - Sign role and sign template with PDF data.
            - Multiple sign requests in different states.
            - An unauthorized sign request for access validation.
        """
        super().setUpClass()
        unique_login = f"portal_user_{uuid.uuid4().hex[:6]}"
        cls.partner = cls.env['res.partner'].create({'name': 'Portal Partner', 'email': 'portal@example.com'})
        cls.user_portal = cls.env['res.users'].create({
            'name': 'Portal User',
            'login': unique_login,
            'password': 'portal_user',
            'email': 'portal@example.com',
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })
        cls.role = cls.env['sign.role'].create({'name': 'Approver'})
        pdf_data = base64.b64encode(b"%PDF-1.4 dummy content%EOF")
        cls.template = cls.env['sign.template'].create({
            'name': 'Portal Template',
            'data': pdf_data,
        })

        cls.requests = cls.env['sign.request']
        states = ['draft', 'partial', 'signed', 'cancel']
        for i, state in enumerate(states):
            req = cls.env['sign.request'].create({
                'name': f'{state.title()} Request',
                'template_id': cls.template.id,
                'state': state,
            })
            cls.env['sign.requester'].create({
                'partner_id': cls.partner.id,
                'role_id': cls.role.id,
                'request_id': req.id,
            })
            cls.requests += req

        other_partner = cls.env['res.partner'].create({'name': 'Other Partner'})
        cls.unauthorized_request = cls.env['sign.request'].create({
            'name': 'Unauthorized Request',
            'template_id': cls.template.id,
        })
        cls.env['sign.requester'].create({
            'partner_id': other_partner.id,
            'role_id': cls.role.id,
            'request_id': cls.unauthorized_request.id,
        })


    def test_sign_request_portal_access(self):
        """Verify that portal users can access `/sign_request` and unauthenticated users are redirected."""
        self.authenticate(self.user_portal.login, 'portal_user')
        response = self.url_open('/sign_request')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Draft Request', response.content)
        self.assertIn(b'Partial Request', response.content)
        self.assertIn(b'Signed Request', response.content)
        self.assertIn(b'Cancel Request', response.content)
        self.assertIn(b'sign_request', response.content)

        self.logout()
        response = self.url_open('/sign_request', allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('/web/login', response.headers.get('Location', ''))

    def test_sign_request_details_access(self):
        """Ensure `/sign_request/details/<id>` works for valid and invalid cases."""
        self.authenticate(self.user_portal.login, 'portal_user')
        first_req = self.requests[0]

        with patch(
                'odoo.addons.cyllo_sign.controllers.cyllo_sign_portal.SignRequestPortal._document_check_access',
                return_value=self.requests[0]
        ), patch.object(http.Request, 'render', return_value="Fake Rendered Template"), patch(
            'odoo.addons.cyllo_sign.models.sign_request.SignRequesters.search'
        ) as mock_search:
            mock_search.return_value.request_id.ids = [first_req.id]

            response = self.url_open(f'/sign_request/details/{first_req.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Fake Rendered Template", response.content)

        invalid_id = self.requests[-1].id + 9999
        with patch(
                'odoo.addons.cyllo_sign.controllers.cyllo_sign_portal.SignRequestPortal._document_check_access',
                side_effect=AccessError("Unauthorized")
        ):
            response_unauth = self.url_open(f'/sign_request/details/{invalid_id}', allow_redirects=False)
            self.assertEqual(response_unauth.status_code, 303)
            self.assertIn('/my', response_unauth.headers.get('Location', ''))

    def test_action_sign_requests(self):
        """Ensure `/sign_request/sign/<id>` handles valid, unauthorized, and access error cases."""
        portal_controller = cyllo_sign_portal.SignRequestPortal()
        first_req = self.requests[0]
        signer_partner = first_req.requester_ids[0].partner_id

        mock_user = MagicMock()
        mock_user.partner_id = signer_partner

        mock_request = MagicMock()
        mock_request.env.user = mock_user

        with patch.object(
                cyllo_sign_portal.SignRequestPortal, "_document_check_access", return_value=first_req
        ), patch.object(
            cyllo_sign_portal, "request", mock_request
        ), patch.object(
            first_req.env, "user", mock_user
        ), patch("odoo.http.Response.load") as mock_response_load:
            mock_response_load.side_effect = lambda x: x

            result = portal_controller.action_sign_requests(first_req.id)

            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("tag"), "sign_configure")
            self.assertIn("params", result)
            self.assertEqual(result["params"]["res_model"], "sign.template")

        stranger = self.env["res.partner"].create({"name": "Unauthorized Partner"})
        mock_user.partner_id = stranger

        with patch.object(
                cyllo_sign_portal.SignRequestPortal, "_document_check_access", return_value=first_req
        ), patch.object(
            cyllo_sign_portal, "request", mock_request
        ), patch.object(
            first_req.env, "user", mock_user
        ), patch("odoo.http.Response.load") as mock_response_load:
            mock_response_load.side_effect = lambda x: x

            result = portal_controller.action_sign_requests(first_req.id)

            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("tag"), "display_notification")
            self.assertIn("not allowed", result["params"]["message"].lower())
            self.assertEqual(result["params"]["type"], "warning")

        mock_request = MagicMock()
        mock_request.redirect.return_value = "Redirected"


    def test_portal_sign_route(self):
        """Test `/web/portal/sign` renders correctly with provided params."""
        self.authenticate(self.user_portal.login, 'portal_user')
        url = "/web/portal/sign?res_id=10&request_id=5&to_sign=yes&requester_ids=1,2&role=approver&res_model=sign.template"
        with patch.object(
            http.Request, "render", return_value=b"Fake Portal Sign Render"
        ) as mock_render:

            response = self.url_open(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Fake Portal Sign Render", response.content)
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[0], 'cyllo_sign.root')

            expected_context = {
                'res_id': '10',
                'request_id': '5',
                'to_sign': 'yes',
                'requester_ids': '1,2',
                'role': 'approver',
                'res_model': 'sign.template',
            }
            self.assertEqual(args[1], expected_context)
        self.logout()
        response2 = self.url_open(url, allow_redirects=False)
        self.assertEqual(response2.status_code, 303)
        self.assertIn('/web/login', response2.headers.get('Location', ''))

    def test_portal_sign_download(self):
        """Test `/web/sign/download` to ensure signed PDF is returned correctly and missing data is handled."""
        self.authenticate(self.user_portal.login, 'portal_user')
        pdf_bytes = b"%PDF-1.4 signed document data%EOF"
        pdf_b64 = base64.b64encode(pdf_bytes)
        sign_req = self.env['sign.request'].create({
            'name': 'SignedDoc.pdf',
            'data': pdf_b64,
        })
        url = f"/web/sign/download?res_id={sign_req.id}"

        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
        content_disposition = response.headers.get('Content-Disposition', '')
        self.assertTrue(
            'filename="SignedDoc.pdf"' in content_disposition
            or "filename*=UTF-8''SignedDoc.pdf" in content_disposition,
            f"Unexpected Content-Disposition header: {content_disposition}"
        )
        self.assertEqual(response.content, pdf_bytes)
        sign_req_no_data = self.env['sign.request'].create({
            'name': 'NoData.pdf',
            'data': False,
        })

        url_no_data = f"/web/sign/download?res_id={sign_req_no_data.id}"
        response_no_data = self.url_open(url_no_data)
        self.assertEqual(response_no_data.status_code, 404)
        self.assertIn(b"not found", response_no_data.content.lower())
        self.logout()
        response_redirect = self.url_open(url, allow_redirects=False)
        self.assertEqual(response_redirect.status_code, 303)
        self.assertIn('/web/login', response_redirect.headers.get('Location', ''))
