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
from odoo.addons.cyllo_field_service.tests.common import TestCylloFieldService


class TestFieldServiceWorker(TestCylloFieldService):
    """Test case for verifying _compute_employee_ids logic in Field Service Worker."""

    def test_compute_employee_ids(self):
        """Ensure only available employees with matching skills are suggested."""
        worker = self.field_service_worker
        matching_employee = self.env['hr.employee'].create({
            'name': 'Employee Match',
            'skill_ids': [(4, self.hr_skill.id)],
            'availability_status': 'available',
        })
        unavailable_employee = self.env['hr.employee'].create({
            'name': 'Employee Not Available',
            'skill_ids': [(4, self.hr_skill.id)],
            'availability_status': 'not_available',
        })
        other_skill_employee = self.env['hr.employee'].create({
            'name': 'Employee Other Skill',
            'skill_ids': [(4, self.hr_skill_2.id)],
            'availability_status': 'available',
        })
        matching_employee.write({'availability_status': 'available'})
        unavailable_employee.write({'availability_status': 'not_available'})
        other_skill_employee.write({'availability_status': 'available'})
        worker._compute_employee_ids()
        self.assertIn(matching_employee, worker.employee_ids)
        self.assertNotIn(unavailable_employee, worker.employee_ids)
        self.assertNotIn(other_skill_employee, worker.employee_ids)
