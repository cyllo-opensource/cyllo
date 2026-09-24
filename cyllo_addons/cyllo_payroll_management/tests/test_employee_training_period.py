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
import logging

from odoo.exceptions import ValidationError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestEmployeeTrainingPeriod(TestPayrollManagementBase):
    """Test for employee training period"""

    def test_onchange_start_date(self):
        _logger.info('Test for onchange start date')
        with self.assertRaises(ValidationError) as VE:
            self.employee_training_period = self.env[
                'employee.training.period'].create({
                'employee_id': self.employee_01.id,
                'start_date': '2018-02-02',
                'end_date': '2018-01-01',
                'state': 'new'
            })
            self.employee_training_period._onchange_start_date()
        self.assertEqual(VE.exception.args[0],'End date must be grater than the start date')
        _logger.info('Test success for onchange start date')

    def test_onchange_employee_id(self):
        _logger.info('Test for onchange existing training period')
        with self.assertRaises(ValidationError) as VE:
            self.employee_training_period = self.env[
                'employee.training.period'].create({
                'employee_id': self.employee_01.id,
                'start_date': '2018-01-01',
                'end_date': '2018-02-02',
                'state': 'new'
            })
            existing_period = self.employee_training_period
            existing_period._onchange_employee_id()
        self.assertEqual(VE.exception.args[0],'This employee already has a training period.')
        _logger.info('Test success for onchange existing training period')


