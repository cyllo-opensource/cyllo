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
from dateutil.relativedelta import relativedelta

from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestEmployeePayslipFlow(TestPayrollManagementBase):
    # For employee payslip
    def test_compute_to_date(self):
        _logger.info("Starts tests for Payslip")
        self.employee_payslip._compute_to_date()
        self.assertEqual(self.employee_payslip.to_date,
                         datetime.date(2024, 4, 30))
        _logger.info("End Test for compute to date")

    def test_get_date_from_schedule_pay_daily(self):
        _logger.info("Starts tests for daily schedule pay")
        self.salary_structure.write({
            'schedule_pay': 'daily'
        })
        date_from_schedule = self.employee_payslip.get_date_from_schedule_pay()
        self.assertEqual(date_from_schedule, datetime.timedelta(days=1))
        _logger.info("Schedule Pay daily Success")

    def test_get_date_from_schedule_pay_weekly(self):
        _logger.info("Starts tests for weekly schedule pay")
        self.salary_structure.write({
            'schedule_pay': 'weekly'
        })
        date_from_schedule = self.employee_payslip.get_date_from_schedule_pay()
        self.assertEqual(date_from_schedule, relativedelta(weeks=1, days=-1))
        _logger.info("Schedule Pay weekly Success")

    def test_get_date_from_schedule_pay_monthly(self):
        _logger.info("Starts tests for monthly schedule pay")
        self.salary_structure.write({
            'schedule_pay': 'monthly'
        })
        date_from_schedule = self.employee_payslip.get_date_from_schedule_pay()
        self.assertEqual(date_from_schedule, relativedelta(months=1, days=-1))
        _logger.info("Schedule Pay months Success")

    def test_compute_payslip_name(self):
        _logger.info('Tests for the payslip name')
        self.employee_payslip._compute_payslip_name()
        expected_name = f"Pay Slip - {self.employee_payslip.employee_id.name} - {self.employee_payslip.start_date.strftime('%B %Y')}"
        self.assertEqual(self.employee_payslip.payslip_name, expected_name)
        _logger.info('Tests for the payslip name Success')

    def test_compute_attendance_count(self):
        _logger.info("Testes for attendance count")
        self.employee_payslip._compute_attendance_count()
        self.assertIsNotNone(self.employee_payslip.attendance_count)
        _logger.info("Attendance Count Success")

    def test_compute_entry_count(self):
        _logger.info("Testes for Entry count")
        work_entries = self.employee_payslip.contract_id.generate_work_entries(
            self.employee_payslip.start_date, self.employee_payslip.to_date)
        self.employee_payslip._compute_work_entry_ids()
        self.assertIsNotNone(work_entries)
        _logger.info("Entry Count Success")

    def test_compute_total_amount(self):
        _logger.info('Tests for compute total amount')
        worked_days = self.employee_payslip.get_worked_day_lines(
            self.employee_01, self.employee_payslip.start_date,
            self.employee_payslip.to_date, self.contract_01)
        self.employee_payslip.employee_worked_days_ids = self.env[
            'employee.worked.days'].create({
            'type': worked_days[0].get('type'),
            'days': worked_days[0].get('days'),
            'hour': worked_days[0].get('hour'),
            'work_entry_type_id': worked_days[0].get('work_entry_type_id'),
            'code': worked_days[0].get('code'),
            'contract_id': worked_days[0].get('contract_id'),
            'amount': self.contract_01.wage
        })
        expected_total_amount = sum(
            self.employee_payslip.employee_worked_days_ids.mapped('amount'))
        self.employee_payslip._compute_total_amount()
        self.assertEqual(self.employee_payslip.total_amount,
                         expected_total_amount)
        _logger.info('Compute Total Amount Success')

    def test_compute_total_worked_hours(self):
        _logger.info('Test for total hour')
        worked_days = self.employee_payslip.get_worked_day_lines(
            self.employee_01, self.employee_payslip.start_date,
            self.employee_payslip.to_date, self.contract_01)
        self.employee_payslip.employee_worked_days_ids = self.env[
            'employee.worked.days'].create({
            'type': worked_days[0].get('type'),
            'days': worked_days[0].get('days'),
            'hour': worked_days[0].get('hour'),
            'work_entry_type_id': worked_days[0].get('work_entry_type_id'),
            'code': worked_days[0].get('code'),
            'contract_id': worked_days[0].get('contract_id'),
            'amount': self.contract_01.wage
        })
        self.employee_payslip._compute_total_worked_hours()
        expected_total_hour = sum(
            self.employee_payslip.employee_worked_days_ids.mapped('hour'))
        self.assertEqual(self.employee_payslip.total_worked_hours,
                         expected_total_hour)
        _logger.info('Test for Total Hour Success')

    def test_get_employee_contract(self):
        _logger.info('Test for employee contract')
        contract = self.contract_01.ids
        employee_id = self.employee_01
        start_date = self.employee_payslip.start_date
        to_date = self.employee_payslip.to_date
        contract_ids = self.employee_payslip.get_employee_contract(employee_id,
                                                                   start_date,
                                                                   to_date)
        self.assertEqual(contract_ids, contract)
        _logger.info('Test case for contract success')

    def test_onchange_employee_id(self):
        _logger.info('Tetes for onchange employee function')
        self.employee_payslip._onchange_employee_id()
        self.assertEqual(self.employee_payslip.contract_id, self.contract_01)
        self.assertEqual(self.employee_payslip.structure_id,
                         self.contract_01.employee_salary_structure_id)
        self.assertTrue(self.employee_payslip.employee_worked_days_ids)
        self.assertTrue(self.employee_payslip.employee_payslip_input_ids)
        _logger.info('Test success for onchange employee id')

    def test_action_compute_sheet(self):
        _logger.info('Test for action compute sheet')
        self.employee_payslip.action_compute_sheet()
        self.assertTrue(self.employee_payslip.structure_id)
        _logger.info('Test for action compute sheet success')

    def test_action_cancel(self):
        _logger.info('Test action cancel')
        self.employee_payslip.action_cancel()
        self.assertEqual(self.employee_payslip.state, 'cancel')
        _logger.info('Test action cancel success')

    def test_action_set_draft(self):
        _logger.info('Test for action draft')
        self.employee_payslip.action_set_draft()
        self.assertEqual(self.employee_payslip.state, 'draft')
        _logger.info('Test action draft success')

    def test_action_create_entry(self):
        _logger.info('Test for action entry')
        self.employee_payslip.action_create_entry()
        self.assertEqual(self.employee_payslip.state, 'done')
        _logger.info('Test action entry success')
