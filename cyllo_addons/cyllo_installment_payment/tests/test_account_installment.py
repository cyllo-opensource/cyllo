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
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase


class TestAccountInstallment(TransactionCase):
    """
    Test suite for the Account Installment model.

    This class contains unit tests that verify the creation of installments
    and their integration with invoices and payment actions. It ensures that
    installment records are properly linked to invoices and that the payment
    creation action works as expected.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up initial test data for the test cases.

        Steps:
            1. Create a test partner.
            2. Create a customer invoice (`account.move` of type `out_invoice`).
            3. Create an installment record linked to the invoice.

        Objects created:
            - `cls.invoice`: Invoice record for the test partner.
            - `cls.installment`: Installment record with amount, sequence, and
            payment date.
        """
        super().setUpClass()
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.env['res.partner'].create(
                {'name': 'Test Partner'}).id,

        })
        cls.installment = cls.env['account.installment'].create({
            'name': 'First Installment',
            'payment_date': date.today() + relativedelta(months=1),
            'sequence': 1,
            'pay_amount': 500.0,
            'move_id': cls.invoice.id,
        })
    def test_action_payment(self):
        """
        Test the action that creates installment payment.

        Validates that:
            - The returned action is of type `ir.actions.act_window`.
            - The correct form view is opened (`form` view_mode and view_type).
            - The target window is set to `new` (popup form).
            - The action opens the correct model (`installment.payment`).
            - The action name is `Installment Payment`.
        """
        action = self.installment.action_create_payment()
        self.assertEqual(action['name'], 'Installment Payment')
        self.assertEqual(action['view_type'], 'form')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_model'], 'installment.payment')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['target'], 'new')
