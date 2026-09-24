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


class TestHrEmployeeAvailability(TestCylloFieldService):
    """Test case for verifying the automatic computation of employee availability.

    This test ensures that the `availability_status` field on `hr.employee`
    updates correctly based on the related field service worker records.
    It covers three main scenarios:
      1. When a related service request is 'in_progress' → employee is 'not_available'
      2. When a related service request is 'assigned' → employee is 'reserved'
      3. When no active assignment or request is present → employee is 'available'
    """

    def test_availability_status(self):
        """Check that employee availability is computed correctly in all cases."""
        request = self.env['field.service.request'].create({
            'name': 'FS001',
            'state': 'in_progress',
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
        })
        self.env['field.service.worker'].create({
            'employee_id': self.employee.id,
            'field_service_request_id': request.id,
        })
        self.employee._compute_availability_status()
        self.assertEqual(self.employee.availability_status, 'not_available')
        request.state = 'assigned'
        self.employee._compute_availability_status()
        self.assertEqual(self.employee.availability_status, 'reserved')
        request.state = 'completed'
        self.employee._compute_availability_status()
        self.assertNotIn(request.state, ['assigned', 'in_progress'])
        self.assertEqual(self.employee.availability_status, 'available')
