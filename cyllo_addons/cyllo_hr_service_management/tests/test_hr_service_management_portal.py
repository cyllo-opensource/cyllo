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
from odoo.tests.common import TransactionCase, new_test_user
from odoo.addons.cyllo_hr_service_management.controllers.main import \
            HrServicePortal
from unittest.mock import patch, MagicMock


class TestHrServiceManagementPortal(TransactionCase):
    """
    Test suite for the HrServicePortal controller.

    This class validates that the portal correctly prepares home portal values
    for HR Service requests, specifically ensuring that the service counter
    logic works as expected.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment with demo data.

        - Creates a test user assigned to 'base.group_user'
        - Links an employee record to this user
        - Creates a service category
        - Creates a handler employee
        - Creates two HR Service requests assigned to the employee and handler

        These records simulate real business data required for testing the
        portal's `_prepare_home_portal_values` method.
        """
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='test_portal',
                                 groups='base.group_user')
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.user.id,
        })
        cls.category = cls.env['hr.service.category'].create({
            'name': 'Test Category',
        })
        cls.handler = cls.env['hr.employee'].create({
            'name': "Handler Employee",
            'work_email': 'handler@test.com',
        })
        cls.services = cls.env['hr.service'].create([
            {
                'name': 'Service Request 1',
                'employee_id': cls.employee.id,
                'service_handler_id': cls.handler.id,
                'service_category_id': cls.category.id,
                'service_request_type': 'service',
                'maintenance_type': 'corrective',
            },
            {
                'name': 'Service Request 2',
                'employee_id': cls.employee.id,
                'service_handler_id': cls.handler.id,
                'service_category_id': cls.category.id,
                'service_request_type': 'service',
                'maintenance_type': 'corrective',
            }
        ])
    def test_prepare_home_portal_values(self):
        """
        Test that `_prepare_home_portal_values` returns the correct service count.

        Steps:
        - Mock the `odoo.http.request` object to inject a fake environment
          containing the test user and employee.
        - Call the portal method `_prepare_home_portal_values` with the
          `service_count` counter.
        - Assert that:
            1. The key `'service_count'` is present in the returned values.
            2. The value is equal to 2, since we created two HR Service records.
        """

        portal = HrServicePortal()
        fake_request = MagicMock()
        fake_request.env = self.env(user=self.user)
        fake_request.env.user.employee_ids = self.employee

        with patch(
                'odoo.addons.cyllo_hr_service_management.controllers.main.request',
                fake_request):
            counters = ['service_count']
            values = portal._prepare_home_portal_values(counters)

        self.assertIn('service_count', values)
        self.assertEqual(values['service_count'], 2)
