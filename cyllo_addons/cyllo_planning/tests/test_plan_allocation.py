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
from odoo.addons.cyllo_planning.tests.common import TestCyPlanning

_logger = logging.getLogger(__name__)

class TestPlanAllocation(TestCyPlanning):

    def test_compute_name(self):
        plan = self.plan_allocation

        # Normal case
        plan._compute_name()
        expected_name = (
            (plan.employee_id.name + ' ' if plan.employee_id else '') +
            (plan.allocation_type_id.name if plan.allocation_type_id else '')
        ).strip() or 'New'
        self.assertEqual(plan.name, expected_name, msg='Error in _compute_name')

        # No employee
        plan.employee_id = False
        plan._compute_name()
        expected_name = plan.allocation_type_id.name if plan.allocation_type_id else 'New'
        self.assertEqual(plan.name, expected_name, msg='Error in _compute_name')

        # No allocation type
        plan.allocation_type_id = False
        plan._compute_name()
        self.assertEqual(plan.name, 'New', msg='Error in _compute_name')

        _logger.info('Ends test_compute_name')

    def test_get_duration(self):
        plan = self.plan_allocation

        # No start date
        plan.start_datetime = False
        result = plan._get_duration(plan.start_datetime, plan.end_datetime)
        self.assertEqual(result, 0)

        # No end date
        plan.start_datetime = '2025-01-01 09:33:43'
        plan.end_datetime = False
        result = plan._get_duration(plan.start_datetime, plan.end_datetime)
        self.assertEqual(result, 0)

        # Valid range
        plan.end_datetime = '2025-01-01 12:33:43'
        result = plan._get_duration(plan.start_datetime, plan.end_datetime)

        from odoo.fields import Datetime
        start = Datetime.to_datetime(plan.start_datetime)
        end = Datetime.to_datetime(plan.end_datetime)

        expected = round((end - start).total_seconds() / 3600, 2)
        self.assertEqual(result, expected)

    def test_compute_duration(self):
        plan = self.plan_allocation
        plan._compute_duration()
        expected = plan._get_duration(plan.start_datetime, plan.end_datetime)
        self.assertEqual(plan.duration, expected, msg='Error in _compute_duration')
        _logger.info('Ends test_compute_duration')
