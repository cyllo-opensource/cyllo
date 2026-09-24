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
from odoo.exceptions import UserError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase


class TestHrExpenseSheet(TestPayrollManagementBase):
    """Tests for reporting approved expense sheets to payslips."""

    def _create_expense_sheet(self, state='draft', report_to_payslip=False):
        sheet = self.env['hr.expense.sheet'].create({
            'name': 'Payroll Expense Sheet',
            'employee_id': self.employee_01.id,
            'report_to_payslip': report_to_payslip,
        })
        sheet.state = state
        return sheet

    def test_action_report_to_payslip_requires_approved_sheet(self):
        sheet = self._create_expense_sheet(state='draft')

        with self.assertRaises(UserError):
            sheet.action_report_to_payslip()

    def test_action_report_to_payslip_marks_approved_sheet(self):
        sheet = self._create_expense_sheet(state='approve')

        self.assertTrue(sheet.action_report_to_payslip())
        self.assertTrue(sheet.report_to_payslip)

    def test_action_report_to_payslip_rejects_already_reported_sheet(self):
        sheet = self._create_expense_sheet(
            state='approve',
            report_to_payslip=True,
        )

        with self.assertRaises(UserError):
            sheet.action_report_to_payslip()

