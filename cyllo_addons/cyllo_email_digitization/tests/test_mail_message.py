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
import email
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError  # ✅ import added


@tagged('post_install', '-at_install')
class TestMailMessageCreateDigitization(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env['ir.model']._get('sale.order')

    # --------------------------------------------------
    # TEST: valid email should be accepted
    # --------------------------------------------------
    @patch(
        'odoo.addons.cyllo_email_digitization.models.email_digitization_config.validate_email')
    def test_valid_email_passes_constraint(self, mock_validate):
        mock_validate.return_value = True  #force pass

        config = self.env['email.digitization.config'].create({
            'email': 'digitize@example.com',
            'model_id': self.model.id,
            'digitize_type': 'use_keyword',
            'active_configuration': True,
        })

        self.assertTrue(config)
        self.assertEqual(config.email, 'digitize@example.com')

    # --------------------------------------------------
    # TEST: invalid email should raise ValidationError
    # --------------------------------------------------
    def test_invalid_email_raises_validation_error(self):
        """Invalid email should raise ValidationError"""
        with self.assertRaises(ValidationError):
            self.env['email.digitization.config'].with_context(
                test_enable=False  # ✅ enforce real SMTP validation
            ).create({
                'email': 'invalid-email',
                'model_id': self.model.id,
                'digitize_type': 'use_keyword',
                'active_configuration': True,
            })
