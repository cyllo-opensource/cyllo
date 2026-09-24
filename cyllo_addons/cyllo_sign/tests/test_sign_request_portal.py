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

from odoo.tests import HttpCase, tagged
from odoo.addons.cyllo_sign.controllers.main import SignRequestPortal


@tagged('-at_install', 'post_install')
class TestSignPortalHomeCount(HttpCase):
    """
    Test suite for validating the sign request counter appearing
    on the portal home dashboard.

    This test ensures that:
        * The count includes only sign requests linked to the logged-in partner.
        * Duplicate requester entries do not increase the count.
        * Requests assigned to other partners are not included.
        * The counter is added only when explicitly requested.
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepare test data for sign request counter verification.

        Creates:
            - A portal user and its linked partner.
            - A sign template used for generating requests.
            - Multiple sign requests:
                * Two requests belonging to the portal user.
                * One duplicate entry (should not affect count).
                * One request assigned to a different partner.
        """
        super().setUpClass()

        unique_login = f"portal_user_{uuid.uuid4().hex[:6]}"
        cls.partner = cls.env['res.partner'].create({
            'name': 'Portal User Partner',
            'email': 'portalhome@example.com',
        })
        cls.user_portal = cls.env['res.users'].create({
            'name': 'Portal User Home',
            'login': unique_login,
            'password': 'portal_user',
            'email': 'portalhome@example.com',
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })
        pdf_data = base64.b64encode(b"%PDF dummy%EOF")
        cls.template = cls.env['sign.template'].create({
            'name': 'Test Template',
            'data': pdf_data,
        })
        cls.req1 = cls.env['sign.request'].create({
            'name': 'Req1',
            'template_id': cls.template.id,
        })
        cls.req2 = cls.env['sign.request'].create({
            'name': 'Req2',
            'template_id': cls.template.id,
        })
        cls.env['sign.requester'].create({
            'partner_id': cls.partner.id,
            'request_id': cls.req1.id,
        })
        cls.env['sign.requester'].create({
            'partner_id': cls.partner.id,
            'request_id': cls.req2.id,
        })
        cls.env['sign.requester'].create({
            'partner_id': cls.partner.id,
            'request_id': cls.req1.id,
        })
        other_partner = cls.env['res.partner'].create({'name': 'Other'})
        cls.env['sign.requester'].create({
            'partner_id': other_partner.id,
            'request_id': cls.req1.id,
        })

    def test_home_portal_sign_request_count(self):
        """
        Validate that `sign_request_count` is correctly computed
        when requested in the counter list and verify that no counter is added when 'sign_request_count'
        is not included in the counters list.

        Ensures:
            - Only sign requests belonging to the logged-in partner are counted.
            - Duplicate entries for the same request do not increase the count.
            - The mocked `request` object correctly simulates HTTP context.
        """
        self.authenticate(self.user_portal.login, 'portal_user')
        controller = SignRequestPortal()
        mock_request = MagicMock()
        mock_request.env = self.env
        mock_request.env.user = self.user_portal
        with patch("odoo.addons.cyllo_sign.controllers.main.request", mock_request):
            vals = controller._prepare_home_portal_values(['sign_request_count'])
        self.assertEqual(vals.get('sign_request_count'), 2)

        self.authenticate(self.user_portal.login, 'portal_user')
        controller = SignRequestPortal()
        mock_request = MagicMock()
        mock_request.env = self.env
        mock_request.env.user = self.user_portal
        with patch("odoo.addons.cyllo_sign.controllers.main.request", mock_request):
            vals = controller._prepare_home_portal_values([])
        self.assertNotIn('sign_request_count', vals)
