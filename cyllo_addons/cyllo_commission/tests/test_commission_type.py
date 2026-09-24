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
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCommissionType(TransactionCase):
    """
    Test suite for the 'commission.type' model.

    This class covers the following features:
    1. Validation of domain syntax for CRM and Sale rules.
    2. Onchange behavior for the 'type' field to ensure irrelevant fields
       are cleared when switching between 'crm' and 'sale' types.

    Test Scenarios:
        - Creating a commission.type with valid domain expressions.
        - Creating a commission.type with invalid domain expressions and
          expecting a ValidationError.
        - Ensuring that empty domain fields are allowed.
        - Testing onchange behavior when type is changed to 'crm' or 'sale'.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env['res.users'].create({
            'name': 'Test New User',
            'login': 'test_new_user',
        })

    def test_validate_domain_syntax(self):
        """
        Test validation of CRM and Sales domain expressions.

        1. Creating a commission.type with valid domain expressions should succeed.
        2. Creating a commission.type with an invalid domain expression should
           raise a ValidationError.
        3. Creating a commission.type with empty domain fields should succeed.
        """
        commission_type = self.env['commission.type'].create({
            'name': 'Valid Commission Type',
            'crm_rule_to_apply': "'dummy' == 'dummy'",
            'sales_rule_to_apply': "1 < 2",
            'user_id': self.user.id
        })
        self.assertEqual(commission_type.crm_rule_to_apply, "'dummy' == 'dummy'")
        self.assertEqual(commission_type.sales_rule_to_apply, "1 < 2")
        with self.assertRaises(ValidationError) as e:
            self.env['commission.type'].create({
                'name': 'Invalid Commission Type',
                'crm_rule_to_apply': "non_existing_var >= 50",
                'sales_rule_to_apply': "amount_untaxed >= 1000",
                'user_id': self.user.id
            })
        self.assertIn("Invalid domain syntax in field 'crm_rule_to_apply'", str(e.exception))

        new_commission_type = self.env['commission.type'].create({
            'name': 'New Commission Type',
            'crm_rule_to_apply':"",
            'sales_rule_to_apply': "",
            'user_id': self.user.id
        })
        self.assertEqual(new_commission_type.crm_rule_to_apply, "")
        self.assertEqual(new_commission_type.sales_rule_to_apply, "")

    def test_onchange_type(self):
        """
         Test the onchange behavior for the 'type' field.

        When the type is 'crm':
            - sales_rule_to_apply should be cleared.
            - crm_rule_to_apply should remain unchanged.

        When the type is 'sale':
            - crm_rule_to_apply should be cleared.
            - sales_rule_to_apply should remain unchanged.

        Uses `new()` to simulate form behavior and manually calls `_onchange_type`.
        """
        onchange_commission_type = self.env['commission.type'].new({
            'name': 'CRM Commission',
            'type': 'crm',
            'sales_rule_to_apply': 'amount_untaxed > 1000',
            'crm_rule_to_apply': 'probability >= 50',
            'user_id': self.user.id,
        })
        onchange_commission_type._onchange_type()
        self.assertEqual(onchange_commission_type.sales_rule_to_apply, "")
        self.assertEqual(onchange_commission_type.crm_rule_to_apply, 'probability >= 50')
        onchange_commission_type_sales = self.env['commission.type'].new({
            'name': 'Sales Commission',
            'type': 'sales',
            'sales_rule_to_apply': 'amount_untaxed > 1000',
            'crm_rule_to_apply': 'probability >= 50',
            'user_id': self.user.id,
        })
        onchange_commission_type_sales._onchange_type()
        self.assertEqual(onchange_commission_type_sales.sales_rule_to_apply, 'amount_untaxed > 1000')
        self.assertEqual(onchange_commission_type_sales.crm_rule_to_apply, "")
