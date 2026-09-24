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
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestResignationRequestConfirm(TestPayrollManagementBase):
    """Test for resignation request confirm"""

    def test_action_confirm(self):
        _logger.info('Test for action confirm')
        self.confirm = self.env['resignation.request.confirm'].create({
            'employee_id': self.employee_01.id,
            'department_id': self.employee_01.department_id.id
        })
        self.confirm.action_confirm_resignation()
        self.assertTrue(self.employee_01.is_resigned)
        _logger.info('Test success for action confirm')
