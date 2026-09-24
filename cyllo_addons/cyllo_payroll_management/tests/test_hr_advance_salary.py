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


class TestHrAdvanceSalary(TestPayrollManagementBase):
    """Tests for advance salary requests and schedules."""

    def _create_advance(self, **values):
        vals = {
            'employee_id': self.employee_01.id,
            'amount': 1000.0,
            'deduction_type': 'fixed',
            'deduction_amount': 250.0,
            'reason': 'Test advance salary',
        }
        vals.update(values)
        return self.env['hr.advance.salary'].create(vals)

    def test_create_assigns_sequence_and_remaining_amount(self):
        advance = self._create_advance()

        self.assertNotEqual(advance.name, 'New')
        self.assertEqual(advance.remaining_amount, 1000.0)
        self.assertEqual(advance.deducted_amount, 0.0)

    def test_approve_generates_deduction_schedule(self):
        advance = self._create_advance()

        advance.action_submit()
        advance.action_approve()

        self.assertEqual(advance.state, 'approved')
        self.assertTrue(advance.approval_date)
        self.assertEqual(len(advance.line_ids), 4)
        self.assertEqual(sum(advance.line_ids.mapped('amount')), 1000.0)
        self.assertTrue(all(line.state == 'planned' for line in advance.line_ids))

    def test_percentage_deduction_uses_open_contract_wage(self):
        advance = self._create_advance(
            amount=2000.0,
            deduction_type='percentage',
            deduction_amount=0.0,
            deduction_percentage=10.0,
        )

        self.assertEqual(advance.monthly_deduction_amount, 500.0)

    def test_fixed_monthly_deduction_must_be_less_than_amount(self):
        with self.assertRaises(UserError):
            self._create_advance(amount=500.0, deduction_amount=500.0)

    def test_line_state_tracks_payslip_and_cancel_flag(self):
        advance = self._create_advance()
        line = self.env['hr.advance.salary.line'].create({
            'advance_id': advance.id,
            'date': '2026-07-01',
            'amount': 100.0,
        })

        self.assertEqual(line.state, 'planned')

        line.payslip_id = self.employee_payslip.id
        self.assertEqual(line.state, 'paid')

        line.is_canceled = True
        self.assertEqual(line.state, 'canceled')

