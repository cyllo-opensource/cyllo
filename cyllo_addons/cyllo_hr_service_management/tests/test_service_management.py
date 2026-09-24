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
from odoo.tests.common import HttpCase, tagged
from werkzeug.datastructures import FileStorage
import io
import base64
import re


@tagged('post_install', '-at_install')
class TestServiceManagement(HttpCase):
    """
    Test class for the Service Management portal in Odoo.

    This class uses HttpCase to simulate user interaction with the
    service management website routes, including:
    - Viewing user service requests
    - Accessing the service request creation form
    - Submitting service requests via direct route calls
    - Uploading attachments with service requests
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment before running tests.

        Creates:
        - A test user and linked employee
        - A service category
        - A service handler (employee)
        - Sample service records to test form display and submission
        """
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'password': 'test_user',
            'email': 'test@example.com',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.user.id,
        })
        cls.category = cls.env['hr.service.category'].create({
            'name': 'Test Category',
        })
        cls.handler = cls.env['hr.employee'].create({
            'name': 'Test Handler',
        })
        cls.env['hr.service'].create({
            'name': 'Test Service',
            'employee_id': cls.employee.id,
            'service_category_id': cls.category.id,
            'state': 'draft',
            'service_handler_id': cls.handler.id,
            'maintenance_type': 'corrective',
        })
        cls.service = cls.env['hr.service'].create({
            'name': 'Test Service',
            'employee_id': cls.employee.id,
            'service_category_id': cls.category.id,
            'state': 'draft',
            'service_handler_id': cls.handler.id,
            'maintenance_type': 'corrective',
        })

    def test_get_user_service_requests(self):
        """
        Test viewing the user's service requests.

        Steps:
        - Authenticate as test user
        - Open the '/service_management' route
        - Verify the response is successful (HTTP 200)
        - Check that expected HTML elements are present
        """
        self.authenticate('test_user', 'test_user')
        response = self.url_open('/service_management')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cy-create_btn', response.text)
        self.assertIn("cy-support_service-ticket-state-btn",
                      response.text)

    def test_service_request_form(self):
        """
        Test accessing the service request creation form.

        Steps:
        - Authenticate as test user
        - Open the '/service_management/create' route
        - Verify the response is successful (HTTP 200)
        - Ensure the form contains relevant fields and existing data
        """
        self.authenticate('test_user', 'test_user')
        response = self.url_open('/service_management/create')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Service Management Request', response.content)
        self.assertIn(b'cy-support_service-ticket_form', response.content)
        self.assertIn(b'Test Employee', response.content)
        self.assertIn(b'Test Category', response.content)

    def test_hr_service_submit(self):
        """
        Test submitting an existing service request by ID.

        Steps:
        - Authenticate as test user
        - Ensure service is initially in 'draft' state
        - Submit the service using the '/service_request/submit/<id>' route
        - Verify the response is successful
        - Check that the service state has changed to 'submit'
        """
        self.authenticate('test_user', 'test_user')
        self.assertEqual(self.service.state, 'draft',
                         "Service should start as draft")
        url = f'/service_request/submit/{self.service.id}'
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'service_request_submitting_template',
                      response.content)
        self.assertEqual(self.service.state, 'submit')

    def test_submit_request(self):
        """
        Test submitting a new service request with POST data and file attachment.

        Steps:
        - Authenticate as test user
        - Get CSRF token from the form page
        - Prepare a dummy attachment
        - Prepare POST data for the request (service type, category, handler, etc.)
        - Open the '/request/submit' route using url_open with POST data and file
        - Verify that the HTTP response is successful (status code 200)
        - Check that a new service record is created for the user
        - Confirm that the service state is set to 'submit'
        - Verify that the uploaded attachment is correctly linked and contains
         the correct data
        """
        self.authenticate('test_user', 'test_user')

        # First, get the form page to extract CSRF token
        form_response = self.url_open('/service_management/create')
        self.assertEqual(form_response.status_code, 200)

        # Extract CSRF token from the form
        csrf_match = re.search(r'name="csrf_token".*?value="([^"]+)"', form_response.text)
        csrf_token = csrf_match.group(1) if csrf_match else None
        self.assertTrue(csrf_token, "CSRF token not found in form")

        file_content = b"Dummy attachment content"
        test_file = FileStorage(
            stream=io.BytesIO(file_content),
            filename="test_file.txt",
            content_type="text/plain"
        )

        post_data = {
            'csrf_token': csrf_token,
            'request_type': 'service',
            'requester_dept': False,
            'category': str(self.category.id),
            'service_equipment': '',
            'maintenance_type': 'corrective',
            'expected_return_date': '',
            'handler': str(self.handler.id),
            'handlers_dept': False,
        }

        response = self.url_open(
            '/request/submit',
            data=post_data,
            files={'attachment_id': test_file}
        )
        self.assertEqual(response.status_code, 200, "Request submission failed")
        service_records = self.env['hr.service'].search(
            [('employee_id', '=', self.employee.id)])
        self.assertTrue(service_records, "Service record was not created")
        service = service_records[-1]
        self.assertEqual(service.state, 'submit',
                         "Service state should be 'submit'")
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.service'),
            ('res_id', '=', service.id)
        ])
        self.assertTrue(attachments, "Attachment was not created")
        self.assertEqual(base64.b64decode(attachments[0].datas), file_content)
