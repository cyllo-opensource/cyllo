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
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestEmployeePayslipBatch(TestPayrollManagementBase):

    def test_action_draft(self):
        _logger.info('Test action draft')
        self.employee_batch.action_draft()
        self.assertEqual(self.employee_batch.state, 'draft')
        _logger.info('Test success for action draft')

    def test_action_close(self):
        _logger.info('Test for action close')
        self.employee_batch.action_paid()
        self.assertEqual(self.employee_batch.state, 'paid')
        _logger.info('Test success for action close')

    def test_action_generate_batch(self):
        _logger.info('Test for action generate batch')
        self.employee_batch.action_generate_batch()
        self.assertTrue(self.employee_batch.is_batch_payslip)
        _logger.info('Test success for action generate batch')

    def test_action_create_entry(self):
        _logger.info('Test for action create entry')
        self.employee_batch.action_create_entry()
        self.assertEqual(self.employee_batch.state, 'done')
        _logger.info('Test success for entry')

    def test_action_paid(self):
        _logger.info('Test for action paid')
        self.employee_batch.action_paid()
        self.assertEqual(self.employee_batch.state, 'paid')
        _logger.info('Test success for action paid')

    def test_compute_end_date(self):
        _logger.info("Test for end date")
        self.employee_batch._compute_end_date()
        self.assertEqual(self.employee_batch.end_date,
                         datetime.date(2024, 4, 30))
        _logger.info("Test success for compute end date")
