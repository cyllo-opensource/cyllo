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
from odoo.tests.common import TransactionCase


class TestHrServicePrint(TransactionCase):
    """
    Test case for verifying the functionality of the custom report
    `hr_service_report_document` defined in the
    `cyllo_hr_service_management` module.

    This test ensures that the report correctly fetches and returns
    service request records to be rendered in the PDF/portal reports.

    """
    @classmethod
    def setUpClass(cls):
        """
        Set up test data required for report testing.

        Steps:
        1. Create an employee requester (the one who requests a service).
        2. Create an employee handler (the one assigned to handle the service).
        3. Create a service category (e.g., IT Support).
        4. Create a service request (`hr.service`) with required fields:
           - employee_id
           - service_handler_id
           - service_category_id
           - service_request_type
           - maintenance_type
        5. Initialize the report model reference for
           `hr_service_report_document`.

        This setup ensures that we have a valid service request
        to pass into the report generation method.

        """
        super().setUpClass()
        cls.employee_requester = cls.env['hr.employee'].create({
            'name': 'Requester',
            'work_email': 'requester@example.com',
        })
        cls.employee_handler = cls.env['hr.employee'].create({
            'name': 'Handler',
            'work_email': 'handler@example.com',
        })
        cls.service_category = cls.env['hr.service.category'].create({
            'name': 'IT Support',
        })
        cls.hr_service = cls.env['hr.service'].create({
            'name': 'Test Service Request',
            'employee_id': cls.employee_requester.id,
            'service_handler_id': cls.employee_handler.id,
            'service_category_id': cls.service_category.id,
            'service_request_type': 'service',
            'maintenance_type': 'corrective',
        })
        cls.report_model = cls.env[('report.cyllo_hr_service_management.'
                                    'hr_service_report_document')]

    def test_get_report_values(self):
        """
        Test the `_get_report_values` method of the report model.

        Purpose:
        - Ensure that when `docids` (IDs of service requests) are passed,
          the method returns a dictionary containing:
            - `hr_service_request` → the recordset of those service requests.

        Assertions:
        1. The result must contain the key `'hr_service_request'`.
        2. The `ids` of the returned recordset must match the docids.
        3. The `name` of the returned service request must match
           "Test Service Request".

        This guarantees that the report fetches the correct
        service request data for rendering in the PDF/portal view.
        """
        docids = [self.hr_service.id]
        result = self.report_model._get_report_values(docids)
        self.assertIn('hr_service_request', result)
        self.assertEqual(result['hr_service_request'].ids, docids)
        self.assertEqual(result['hr_service_request'].name,
                         'Test Service Request')
