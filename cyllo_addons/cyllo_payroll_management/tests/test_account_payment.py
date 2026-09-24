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
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase


class TestAccountPayment(TestPayrollManagementBase):
    """Tests for payroll payment registration context."""

    def test_payroll_register_payment_allows_current_liability_account(self):
        payment_model = self.env['account.payment'].with_context(
            payroll_register_payment=True
        )

        account_types = payment_model._get_valid_payment_account_types()

        self.assertIn('liability_current', account_types)

