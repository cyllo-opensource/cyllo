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

from odoo import fields
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestHrEmployee(TestPayrollManagementBase):
    """Test for hr employee"""

    def test_compute_payslip_count(self):
        _logger.info('Test for compute payslip count')
        self.employee_01._compute_payslip_count()
        self.assertEqual(self.employee_01.payslip_count, 1)
        _logger.info('Test success for compute payslip count')

    def test_update_state(self):
        _logger.info('Test for updating state')
        today = fields.Date.today()
        self.resignation_02 = self.env['employee.resignation'].create({
            'employee_id': self.employee_01.id,
            'contract_id': self.contract_01.id,
            'joining_date': self.contract_01.date_start,
            'end_date': self.contract_01.date_end,
            'department_id': self.department.id,
            'resignation_type_id': self.resignation_type.id,
            'reason': 'Sick',
            'state': 'approved',
            'approved_date': '2024-04-19',
            'notice_period': 1,
        })
        self.resignation_02._compute_leaving_date()
        resignation_to_update = self.resignation_02.sudo().search(
            [('leaving_date', '<=', today), ('state', '=', 'approved')])
        resignation_to_update.employee_id.update_employee_state()
        self.assertFalse(resignation_to_update.employee_id.active)
        _logger.info('Test success for updating state')
