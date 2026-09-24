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
from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSignRequest(TransactionCase):
    """
    Test suite for verifying the functionality of the `SignRequest` model.

    This test ensures:
        * User and role retrieval methods work as expected.
        * Signing URL is correctly generated.
        * Access validation and error handling are enforced during signing.
        * Document actions (cancel, print, etc.) behave properly.
        * Email sending via templates works correctly with proper context.
        * Expiration logic updates request states as expected.
    """

    @classmethod
    def setUpClass(cls):
        """
        Test data setup executed once for the entire test class.

        Creates:
            - Partner record for sign requester.
            - Sign template record.
            - Sign role record.
            - Sign request and requester linked together.
            - Sets web base URL for generating sign links.
        """
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test.partner@example.com',
        })

        cls.template = cls.env['sign.template'].create({
            'name': 'Test Template',
        })

        cls.sign_request = cls.env['sign.request'].create({
            'name': 'Test Request',
            'template_id': cls.template.id,
        })

        cls.role = cls.env['sign.role'].create({
            'name': 'Approver',
        })

        cls.requester = cls.env['sign.requester'].create({
            'partner_id': cls.partner.id,
            'role_id': cls.role.id,
            'request_id': cls.sign_request.id,
        })

        cls.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://localhost:8017')

    def test_get_user(self):
        """
        Verify that `get_user()` returns correct partner details.

        Ensures:
            - Returned value is a list containing a dictionary.
            - The partner's name and ID match the expected values.
        """
        result = self.sign_request.get_user(self.partner.id)
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        self.assertEqual(result[0]['id'], self.partner.id)
        self.assertEqual(result[0]['name'], self.partner.name)

    def test_get_roles(self):
        """
        Validate `get_roles()` method retrieves the correct role
        for the currently logged-in user acting as a signer.
        """
        self.requester.partner_id = self.env.user.partner_id.id

        result = self.sign_request.get_roles()
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        data = result[0]
        self.assertEqual(data['partner_id'][0], self.env.user.partner_id.id)
        self.assertEqual(data['role_id'][1], 'Approver')

    def test_get_sign_url(self):
        """
        Ensure `get_sign_url()` constructs a valid and complete signing URL.

        Verifies:
            - The generated URL starts with the correct base URL.
            - Contains expected query parameters like partner_id, role, and request_id.
        """
        url = self.sign_request.get_sign_url(self.partner.id, self.role.id)
        self.assertTrue(url.startswith('http://localhost:8017/web/portal/sign'))
        self.assertIn(f"partner_id={self.partner.id}", url)
        self.assertIn(f"role={self.role.id}", url)
        self.assertIn(f"request_id={self.sign_request.id}", url)
        self.assertIn("to_sign=True", url)

    def test_action_sign_authorized(self):
        """
        Test that authorized users can access the sign action.

        Ensures:
            - Action returns a client configuration for signing.
            - Required keys like 'type', 'tag', and 'params' exist.
        """
        self.requester.partner_id = self.env.user.partner_id.id
        action = self.sign_request.action_sign()
        self.assertEqual(action.get("type"), "ir.actions.client")
        self.assertEqual(action.get("tag"), "sign_configure")
        self.assertIn("params", action)

    def test_action_sign_unauthorized(self):
        """
        Test that unauthorized users are restricted from signing.

        Ensures:
            - Raises ValidationError when user is not in the requester list.
        """
        self.requester.partner_id = self.partner.id
        with self.assertRaises(ValidationError):
            self.sign_request.action_sign()

    def test_action_cancel(self):
        """
        Validate `action_cancel()` correctly updates the request state to 'cancel'.
        """
        self.assertNotEqual(self.sign_request.state, 'cancel')
        self.sign_request.action_cancel()
        self.assertEqual(self.sign_request.state, 'cancel')

    def test_action_print_signed_document_with_data(self):
        """
        Ensure `action_print_signed_document()` returns a valid
        download action when document data exists.
        """
        self.sign_request.data = base64.b64encode(b"PDF binary data")

        action = self.sign_request.action_print_signed_document()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertIn('/web/content/sign.request', action.get('url'))
        self.assertIn('?download=true', action.get('url'))
        self.assertEqual(action.get('target'), 'self')

    def test_action_print_signed_document_no_data(self):
        """
        Ensure `action_print_signed_document()` displays an error
        notification when no document data is available.
        """
        self.sign_request.data = False
        action = self.sign_request.action_print_signed_document()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'display_notification')

        params = action.get('params', {})
        self.assertEqual(params.get('title'), 'Error')
        self.assertIn('No data available', params.get('message'))

    def test_send_sign_request_email(self):
        """
        Test the `send_sign_request_email()` method to ensure that
        sign request emails are sent correctly using the email template.

        Validations:
            - send_mail is called once per requester.
            - The call includes correct record ID and force_send flag.
            - The email template reference exists.
        """
        partner_cc = self.env['res.partner'].create({
            'name': 'CC Partner',
            'email': 'cc.partner@example.com',
        })

        self.sign_request.write({
            'email_cc_ids': [(6, 0, [partner_cc.id])],
            'custom_subject': 'Custom Subject Test',
            'custom_message': '<p>Custom message for signers</p>',
        })
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            self.sign_request.send_sign_request_email()
            self.assertTrue(mock_send_mail.called)
            self.assertEqual(mock_send_mail.call_count, len(self.sign_request.requester_ids))
            args, kwargs = mock_send_mail.call_args
            self.assertEqual(args[0], self.sign_request.id)
            self.assertIn('force_send', kwargs)
            self.assertTrue(kwargs['force_send'])
            template = self.env.ref('cyllo_sign.email_template_sign_request')
            self.assertTrue(template)


    def test_expire_request(self):
        """
        Verify that `_expire_request()` correctly updates the state of
        sign requests whose validity date has passed.

        Validations:
            - Requests with expired validity are marked as 'expired'.
            - Requests with future validity remain unchanged.
            - Signed and cancelled requests are ignored.
        """
        past_date = date.today() - timedelta(days=1)
        future_date = date.today() + timedelta(days=2)
        expired_request = self.env['sign.request'].create({
            'name': 'Expired Request',
            'template_id': self.template.id,
            'validity': past_date,
        })

        active_request = self.env['sign.request'].create({
            'name': 'Active Request',
            'template_id': self.template.id,
            'validity': future_date,
        })

        signed_request = self.env['sign.request'].create({
            'name': 'Signed Request',
            'template_id': self.template.id,
            'validity': past_date,
            'state': 'signed',
        })

        cancelled_request = self.env['sign.request'].create({
            'name': 'Cancelled Request',
            'template_id': self.template.id,
            'validity': past_date,
            'state': 'cancel',
        })

        self.sign_request._expire_request()
        self.assertEqual(expired_request.state, 'expired')
        self.assertEqual(active_request.state, 'draft')
        self.assertEqual(signed_request.state, 'signed')
        self.assertEqual(cancelled_request.state, 'cancel')
