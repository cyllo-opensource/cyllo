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
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSignGenerate(TransactionCase):
    """
    Test suite for validating the functionality of the `SignGenerate` wizard.

    This suite ensures:
        * Computed methods correctly manage signer assignment and activation.
        * Sign request generation creates valid linked records.
        * Email sending operations are invoked with appropriate context.
        * Proper error handling occurs when invalid or missing users exist.
    """

    @classmethod
    def setUpClass(cls):
        """
        Initialize shared test data for all test cases.

        Creates:
            - A partner and corresponding user for signing actions.
            - A sign role and field to define signature properties.
            - A valid sign template with sample PDF data and an item field.
            - A `sign.generate` wizard linked to the created template.
            - A default signer record to simulate signers for generation and sending.
        """
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'John Doe', 'email': 'john@example.com'})
        cls.user = cls.env['res.users'].create({
            'name': 'John User',
            'login': 'john@example.com',
            'partner_id': cls.partner.id,
        })
        cls.role = cls.env['sign.role'].create({'name': 'Manager'})
        cls.field = cls.env['sign.field'].create({'name': 'Signature Field', 'field_type': 'signature'})
        cls.template = cls.env['sign.template'].create({'name': 'Contract Template'})

        cls.item = cls.env['sign.template.item'].create({
            'template_id': cls.template.id,
            'field_id': cls.field.id,
            'role_id': cls.role.id,
            'name': 'Manager Signature',
            'page': 1,
            'position_x': 10,
            'position_y': 20,
        })

        cls.sign_generate = cls.env['sign.generate'].create({
            'template_id': cls.template.id,
            'subject': 'Please sign',
            'message': '<p>Kindly review and sign.</p>'
        })

        cls.signer = cls.env['sign.signers'].create({
            'partner_id': cls.partner.id,
            'role_id': cls.role.id,
            'sign_generate_id': cls.sign_generate.id,
        })

    def test_action_send(self):
        """
        Validate that `action_send()` properly creates sign requests
        and triggers email notifications via the mail template.

        Ensures:
            - `send_sign_request_email()` is invoked once during execution.
            - `sign.request` is correctly created with expected details.
            - Raises `ValidationError` when no valid users are found.
        """
        self.sign_generate.signer_ids = [self.signer.id]

        with patch('odoo.addons.cyllo_sign.models.sign_request.SignRequest.send_sign_request_email',
                   return_value=True) as mock_email:
            result = self.sign_generate.action_send()
            mock_email.assert_called_once()
            self.assertTrue(result)

            sign_request = self.env['sign.request'].search([('template_id', '=', self.template.id)], limit=1)
            self.assertTrue(sign_request.exists())

        self.sign_generate.signer_ids = [fields.Command.clear()]
        with self.assertRaises(ValidationError):
            self.sign_generate.action_send()

    def test_action_generate_sign(self):
        """
        Verify that `action_generate_sign()` correctly creates sign requests
        and triggers the signing action for authorized users.

        Validations:
            - Creates a valid `sign.request` record linked to the template.
            - Returns a client action dictionary when user is authorized.
            - Raises `ValidationError` when no valid signers are found.
        """
        self.sign_generate.signer_ids = [self.signer.id]

        with patch('odoo.addons.cyllo_sign.models.sign_request.SignRequest.action_sign',
                   return_value={'type': 'ir.actions.client', 'tag': 'sign_configure'}) as mock_action:
            action = self.sign_generate.with_user(self.user).action_generate_sign()
            self.assertIsInstance(action, dict)
            self.assertIn('tag', action)
            mock_action.assert_called_once()

            sign_request = self.env['sign.request'].search([('template_id', '=', self.template.id)], limit=1)
            self.assertTrue(sign_request.exists())

        self.sign_generate.signer_ids = [fields.Command.clear()]
        with self.assertRaises(ValidationError):
            self.sign_generate.action_generate_sign()

    def test_compute_is_active(self):
        """
        Validate the behavior of `_compute_is_active()` method.

        Ensures:
            - Existing signers are cleared before regeneration.
            - `is_active` flag is correctly set when valid roles exist.
            - New signer records are linked with correct roles.
        """
        old_signer = self.env['sign.signers'].create({
            'role_id': self.role.id,
            'sign_generate_id': self.sign_generate.id,
        })
        self.sign_generate.signer_ids = [old_signer.id]
        self.assertEqual(len(self.sign_generate.signer_ids), 1)
        self.sign_generate._compute_is_active()
        self.assertTrue(self.sign_generate.is_active)
        self.assertGreater(len(self.sign_generate.signer_ids), 0)
        self.assertNotIn(old_signer.id, self.sign_generate.signer_ids.ids)
        new_signer = self.sign_generate.signer_ids[0]
        self.assertEqual(new_signer.role_id.id, self.role.id)
        created_signers = self.env['sign.signers'].search([('sign_generate_id', '=', self.sign_generate.id)])
        self.assertTrue(created_signers)
        self.assertEqual(created_signers[0].role_id.id, self.role.id)





