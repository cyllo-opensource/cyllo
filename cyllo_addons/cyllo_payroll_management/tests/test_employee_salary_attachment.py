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
import datetime
import logging

from odoo.exceptions import UserError, ValidationError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestSalaryAttachment(TestPayrollManagementBase):
    """Test for employee salary attachment"""

    def test_check_month_amount(self):
        _logger.info('Test for check month amount')
        self.employee_salary_attachment._check_month_amount()
        self.assertTrue(self.employee_salary_attachment.month_amount)
        _logger.info('Test success for for check month amount')

    def test_check_month_amount_validation(self):
        _logger.info('Test for check validation')
        with self.assertRaises(ValidationError) as VE:
            self.employee_salary_attachment_01 = self.env[
                'employee.salary.attachment'].create({
                'employee_id': self.employee_01.id,
                'description': 'Attachment',
                'employee_payslip_other_input_id': self.employee_other_input.id,
                'start_date': '2020-01-01',
                'end_date': '2024-01-01',
                'month_amount': 0,
                'state': 'running',
                'total_amount': 7000,
            })
            self.employee_salary_attachment_01._check_month_amount()
        self.assertEqual(VE.exception.args[0],
                         'Monthly amount should be positive')
        _logger.info('Test success for check validation')

    def test_compute_end_date(self):
        _logger.info('Test for compute date with the amount')
        self.employee_salary_attachment.write({
            'start_date': '2022-01-01',
            'month_amount': 1000,
            'total_amount': 2000,
        })
        self.employee_salary_attachment._compute_end_date()
        self.assertEqual(self.employee_salary_attachment.end_date,
                         datetime.date(2022, 3, 1))
        _logger.info('Test success for compute date with the amount')

    def test_compute_is_total_amount(self):
        _logger.info('Test for compute is total')
        self.employee_salary_attachment._compute_is_total_amount()
        self.assertTrue(self.employee_salary_attachment.is_total_amount)
        _logger.info('Test success for compute is total')

    def test_compute_balance(self):
        _logger.info('Test for compute balance')
        balance = max(0,
                      self.employee_salary_attachment.total_amount - self.employee_salary_attachment.paid_amount)
        self.assertEqual(self.employee_salary_attachment.balance, balance)
        _logger.info('Test success for compute balance')

    def test_compute_active_amount(self):
        _logger.info('Test for active amount')
        active_amount = min(self.employee_salary_attachment.month_amount,
                            self.employee_salary_attachment.balance)
        self.assertEqual(self.employee_salary_attachment.active_amount,
                         active_amount)
        _logger.info('Test success for active amount')

    def test_unlink(self):
        _logger.info('Test for unlink')
        with self.assertRaises(UserError) as UE:
            self.employee_salary_attachment_03 = self.env[
                'employee.salary.attachment'].create({
                'employee_id': self.employee_01.id,
                'description': 'Attachment',
                'employee_payslip_other_input_id': self.employee_other_input.id,
                'start_date': '2020-01-01',
                'end_date': '2024-01-01',
                'month_amount': 500,
                'state': 'running',
                'total_amount': 7000,
            })
            self.employee_salary_attachment_03.unlink()
        self.assertEqual(UE.exception.args[0],
                         'You cannot delete a running salary attachment!')
        _logger.info('Test success for check user error')

    def test_action_done(self):
        _logger.info('Test for action done')
        self.employee_salary_attachment.action_done()
        self.assertEqual(self.employee_salary_attachment.state, 'completed')
        _logger.info('Test success for action done')

    def test_action_cancel(self):
        _logger.info('Test for action cancel')
        self.employee_salary_attachment.action_cancel()
        self.assertEqual(self.employee_salary_attachment.state, 'cancelled')
        _logger.info('Test success for action cancel')

    def test_action_open(self):
        _logger.info('Test for action open')
        self.employee_salary_attachment.action_open()
        self.assertEqual(self.employee_salary_attachment.state, 'running')
        _logger.info('Test success for action open')
