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


class TestHrContract(TestPayrollManagementBase):
    """Test for hr contract"""

    def test_compute_yearly_wage(self):
        _logger.info('Test for yearly wage')
        self.contract_01._compute_yearly_wage()
        self.assertEqual(self.contract_01.yearly_wage, 60000)
        _logger.info('Test success for yearly wage')

    def test_action_approve_contract_validation(self):
        _logger.info('Test for approve contract')
        self.employee_02 = self.env['hr.employee'].create({'name': 'Johnson'})
        with self.assertRaises(ValidationError) as VE:
            self.contract_02 = self.env['hr.contract'].create({
                'date_start': '2018-01-01',
                'name': 'Contract for Johnson',
                'state': 'draft',
                'wage': 5000,
                'employee_id': self.employee_02.id,
                'resource_calendar_id': self.calendar_40h.id,
                'employee_salary_structure_id': self.salary_structure.id
            })
            self.contract_02.action_approve_contract()
        self.assertEqual(VE.exception.args[0],
                         'Please add the Training Start Date and End Date')
        _logger.info('Test success for approve contract validation')

    def test_action_approve_contract_training(self):
        _logger.info('Test for approve contract training')
        self.employee_03 = self.env['hr.employee'].create({'name': 'Michel'})
        self.contract_03 = self.env['hr.contract'].create({
            'training_date_from': '2017-12-31',
            'training_date_to': '2018-01-01',
            'date_start': '2018-01-01',
            'name': 'Contract for Michel',
            'state': 'draft',
            'wage': 5000,
            'employee_id': self.employee_03.id,
            'resource_calendar_id': self.calendar_40h.id,
            'employee_salary_structure_id': self.salary_structure.id
        })
        self.contract_03.action_approve_contract()
        self.assertEqual(self.contract_03.state, 'open')
        _logger.info('Test success for approve contract training')
