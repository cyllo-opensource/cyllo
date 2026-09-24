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
from datetime import timedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import TransactionCase
from unittest.mock import patch
from odoo import fields


class TestHrService(TransactionCase):
    """
    Test suite for the HR Service model (`hr.service`).

    These tests validate the business logic, workflow states,
    computed fields, onchange methods, mail notifications, and
    integration with related models such as `maintenance.request`
    and `hr.employee`.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up demo data for HR Service tests.

        Creates:
        - HR manager and employee users with respective groups.
        - Employee records for manager, requester, handler, and executor.
        - HR service categories and service requests.
        - Mail templates for notifications.
        - A sample service in 'ongoing' state for workflow testing.
        """
        super().setUpClass()
        cls.hr_manager_group = cls.env.ref('hr.group_hr_manager')
        cls.hr_user_group = cls.env.ref('hr.group_hr_user')
        cls.user_manager = cls.env['res.users'].create({
            'name': 'HR Manager User',
            'login': 'hrmanager@test.com',
            'groups_id': [(6, 0, [cls.hr_manager_group.id])],
        })
        cls.user_employee = cls.env['res.users'].create({
            'name': 'Normal Employee User',
            'login': 'employee@test.com',
            'groups_id': [(6, 0, [cls.hr_user_group.id])],
        })
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'HR Manager Employee',
            'user_id': cls.user_manager.id,
        })
        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Normal Employee',
            'user_id': cls.user_employee.id,
        })
        cls.service_category = cls.env['hr.service.category'].create({
            'name': 'IT Support'
        })
        cls.service_request = cls.env['hr.service'].create({
            'service_category_id': cls.service_category.id,
            'employee_id': cls.employee_user.id,
            'service_handler_id': cls.employee_manager.id,
        })
        cls.company = cls.env.company
        cls.employee_requester = cls.env['hr.employee'].create({
            'name': 'Requester',
            'work_email': 'requester@example.com'
        })
        cls.employee_handler = cls.env['hr.employee'].create({
            'name': 'Handler',
            'work_email': 'handler@example.com',
        })
        cls.employee_executor = cls.env['hr.employee'].create({
            'name': 'Executor',
            'work_email': 'executor@example.com',
        })
        cls.mail_template_requester = cls.env.ref(
            'cyllo_hr_service_management.mail_template_request_submitted')
        cls.mail_template_handler = cls.env.ref(
            'cyllo_hr_service_management.mail_template_request_for_service')
        cls.service = cls.env['hr.service'].create({
            'name': 'Test Service',
            'state': 'draft',
            'is_equipment_required': False,
            'employee_id': cls.employee_user.id,
            'service_handler_id': cls.employee_handler.id,
            'service_category_id': cls.service_category.id,
        })
        cls.service_handler = cls.env['hr.employee'].create({
            'name': 'Service Handler',
            'work_email': 'handler@example.com',
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee',
            'work_email': 'employee@example.com',
        })
        cls.service = cls.env['hr.service'].create({
            'name': 'Test Service',
            'service_handler_id': cls.service_handler.id,
            'employee_id': cls.employee.id,
            'state': 'ongoing',
        })

    def test_compute_is_hr_manager(self):
        """
        Test the `_compute_is_hr_manager` method on `service_request`.

        This test verifies that the computed fields `is_hr_manager` and
        `current_user_employee_id` are correctly set based on the current user.

        Scenarios tested:
        1. When the current user belongs to the HR manager group (`user_manager`):
           - `is_hr_manager` should be True.
           - `current_user_employee_id` should match the manager's employee record.

        2. When the current user is a regular employee (`user_employee`):
           - `is_hr_manager` should be False.
           - `current_user_employee_id` should match the employee's own record.
        """
        service = self.service_request.with_user(self.user_manager)
        service._compute_is_hr_manager()
        self.assertTrue(service.is_hr_manager)
        self.assertEqual(service.current_user_employee_id, self.employee_manager)
        service = self.service_request.with_user(self.user_employee)
        service._compute_is_hr_manager()
        self.assertFalse(service.is_hr_manager)
        self.assertEqual(service.current_user_employee_id, self.employee_user)

    def test_action_submit(self):
        """
        Test `action_submit` transition.

        Verifies:
        - Draft service request moves to 'submit' state.
        - Name changes from 'New'.
        - Date is set.
        - Requester and handler mail templates exist.
        - Works for both 'service' and 'custody' request types.
        """
        service_request = self.env['hr.service'].create({
            'service_request_type': 'service',
            'employee_id': self.employee_requester.id,
            'service_handler_id': self.employee_handler.id,
            'service_category_id': self.service_category.id,
        })
        self.assertEqual(service_request.state, 'draft')
        service_request.action_submit()
        self.assertEqual(service_request.state, 'submit')
        self.assertNotEqual(service_request.name, 'New')
        self.assertIsNotNone(service_request.date)
        self.assertTrue(self.mail_template_requester.exists())
        self.assertTrue(self.mail_template_handler.exists())
        custody_request = self.env['hr.service'].create({
            'service_request_type': 'custody',
            'employee_id': self.employee_requester.id,
            'service_handler_id': self.employee_handler.id,
            'service_category_id': self.service_category.id,
        })
        custody_request.action_submit()
        self.assertEqual(custody_request.state, 'submit')
        self.assertNotEqual(custody_request.name, 'New')
        self.assertIsNotNone(custody_request.date)

    def test_action_assign(self):
        """
        Test `action_assign` workflow.

        Verifies:
        - Service request transitions to 'assign'.
        - Executor is correctly assigned.
        - Chatter log contains assignment message.
        - Raises ValidationError if no executor is defined.
        """
        service_request = self.env['hr.service'].create({
            'employee_id': self.employee_requester.id,
            'service_handler_id': self.employee_handler.id,
            'service_executor_id': self.employee_executor.id,
            'service_category_id': self.service_category.id,
        })
        self.assertNotEqual(service_request.state, 'assign')
        service_request.action_assign()
        self.assertEqual(service_request.state, 'assign')
        last_message = service_request.message_ids[0].body
        self.assertIn("Service request have been assigned to", last_message)
        self.assertIn(self.employee_executor.name, last_message)
        service_request_no_id = self.env['hr.service'].create({
            'employee_id': self.employee_requester.id,
            'service_handler_id': self.employee_handler.id,
            'service_category_id': self.service_category.id,
        })
        with self.assertRaises(ValidationError):
            service_request_no_id.action_assign()

    def test_action_start(self):
        """
        Test `action_start` workflow.

        Ensures:
        - Service state changes to 'ongoing'.
        """
        self.service.action_start()
        self.assertEqual(self.service.state, 'ongoing')

    def test_action_done(self):
        """
        Test `action_done` workflow.

        Ensures:
        - Service state changes to 'done'.
        - Date done is set.
        - Mail templates are sent to requester and handler.
        """
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.'
                   'send_mail',
                   return_value=True) as mock_send_mail:
            self.service.action_done()
            self.assertEqual(self.service.state, 'done')
            self.assertIsNotNone(self.service.date_done)
            self.assertEqual(mock_send_mail.call_count, 2)
            messages = [str(m) for m in self.service.message_ids.mapped('body')]
            self.assertTrue(
                any("Service have been completed" in msg for msg in messages),
                f"Expected completion message not found in: {messages}"
            )

    def test_action_approve(self):
        """
        Test `action_approve`.

        Verifies:
        - Equipment assigned to service employee.
        - Service moves to 'approved'.
        - `date_done` is set.
        """
        equipment = self.env['maintenance.equipment'].create({
            'name': 'Test Equipment'
        })
        self.service.equipment_id = equipment
        self.service.employee_id = self.employee_user
        self.service.action_approve()
        self.assertEqual(equipment.employee_id, self.employee_user)
        self.assertEqual(self.service.state, 'approved')
        self.assertIsNotNone(self.service.date_done)

    def test_action_return(self):
        """
        Test `action_return`.

        Ensures:
        - If `expected_return_date` is past, opens late return wizard.
        - If `expected_return_date` is future, service moves to 'quality'.
        - `return_date` is recorded.
        """
        self.service.expected_return_date = (fields.Datetime.now() -
                                             timedelta(days=1))
        result = self.service.action_return()
        self.assertEqual(result['res_model'], 'late.return.reason')
        self.assertEqual(result['target'], 'new')
        self.service.expected_return_date = (fields.Datetime.now() +
                                             timedelta(days=1))
        result2 = self.service.action_return()
        self.assertIsNone(result2)
        self.assertEqual(self.service.state, "quality")
        self.assertIsNotNone(self.service.return_date)

    def test_action_cancel(self):
        """
        Test `action_cancel`.

        Ensures:
        - State changes to 'cancel'.
        - Cancellation message is posted in chatter.
        - Two notification emails are sent (mocked).
        """
        with patch('odoo.addons.mail.models.mail_template.'
                   'MailTemplate.send_mail',
                   return_value=True) as mock_send_mail:
            self.service.action_cancel()
            self.assertEqual(self.service.state, 'cancel')
            self.assertEqual(mock_send_mail.call_count, 2)
            messages = [str(m) for m in self.service.message_ids.mapped('body')]
            self.assertTrue(
                any("Service request have been canceled" in msg for msg
                    in messages),
                f"Expected completion message not found in: {messages}"
            )
    
    def test_action_quality(self):
        """
        Test `action_approve_quality`.

        Verifies:
        - State transitions to 'returned'.
        - Equipment unassigned from employee.
        - Return message is logged.
        - One email notification is sent.
        """
        self.service.equipment_id = self.env['maintenance.equipment'].create({
            'name': 'Test Equipment',
            'employee_id': self.employee_user.id,
        })
        with patch('odoo.addons.mail.models.mail_template.'
                   'MailTemplate.send_mail',
                   return_value=True) as mock_send_mail:
            self.service.action_approve_quality()
            self.assertEqual(self.service.state, 'returned')
            self.assertFalse(self.service.equipment_id.employee_id)
            self.assertEqual(mock_send_mail.call_count, 1)
            messages = [str(m) for m in self.service.message_ids.mapped('body')]
            self.assertTrue(
                any("Equipment have been returned" in msg for msg
                    in messages),
                f"Expected completion message not found in: {messages}"
            )

    def test_action(self):
        """
        Test `action_draft`.

        Ensures:
        - Service in 'ongoing' state can be reset back to 'draft'.
        """
        self.assertEqual(self.service.state, 'ongoing')
        self.service.action_draft()
        self.assertEqual(self.service.state, 'draft')

    def test_action_to_me(self):
        """
        Test `action_assign_to_me`.

        Scenarios:
        - HR Manager assigns service to self → state becomes 'assign'.
        - Normal employee tries → warning client action is returned.
        """
        service = self.service_request.with_user(self.user_manager)
        service.is_hr_manager = True
        with patch(
                'odoo.addons.mail.models.mail_template.MailTemplate.send_mail',
                return_value=True) as mock_send_mail:
            service.action_assign_to_me()
            self.assertEqual(service.service_executor_id,
                             self.user_manager.employee_id)
            self.assertEqual(service.state, 'assign')
            self.assertEqual(mock_send_mail.call_count, 1)
        service = self.service_request.with_user(self.user_employee)
        service.is_hr_manager = False
        service.current_user_employee_id = self.employee_user
        result = service.action_assign_to_me()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn('Only the receptor or administrator',
                      result['params']['message'])

    def test_create_request(self):
        """
        Test `_create_request` method.

        Ensures:
        - Maintenance request is created with proper links.
        - Name, employee, service, date, user, equipment,
          and maintenance_type match the originating service.
        """
        self.service.equipment_id = self.env['maintenance.equipment'].create({
            'name': 'Test Equipment',
        })
        self.service.maintenance_type = 'corrective'
        self.service._create_request()
        maintenance_request = (self.env['maintenance.request'].
                               browse(self.service.maintenance_request_id.id))
        self.assertTrue(maintenance_request.exists)
        self.assertEqual(maintenance_request.name, self.service.name)
        self.assertEqual(maintenance_request.service_id, self.service)
        self.assertEqual(maintenance_request.employee_id,
                         self.service.employee_id)
        self.assertEqual(maintenance_request.request_date,
                         fields.Datetime.today().date())
        self.assertEqual(maintenance_request.user_id, self.env.user)
        self.assertEqual(maintenance_request.equipment_id,
                         self.service.equipment_id)
        self.assertEqual(maintenance_request.maintenance_type,
                         self.service.maintenance_type)

    def test_onchange_employee_id(self):

        """
        Test `_onchange_employee_id`.

        Scenarios:
        - If employee has parent → handler = parent.
        - Else if department manager exists → handler = department manager.
        - Else → handler is cleared (False).
        """
        self.employee.parent_id = self.employee_manager
        self.service.employee_id = self.employee
        self.service._onchange_employee_id()
        self.assertEqual(self.service.service_handler_id, self.employee_manager)

        self.employee.parent_id = False
        self.employee.department_id.manager_id = self.employee
        self.service._onchange_employee_id()
        self.assertEqual(self.service.service_handler_id,
                         self.employee.department_id.manager_id)

        self.employee.parent_id = False
        self.employee.department_id.manager_id = False
        self.service.employee_id = self.employee
        self.service._onchange_employee_id()
        self.assertFalse(self.service.service_handler_id)

    def test_compute_access_url(self):
        """
        Test `_compute_access_url`.

        Ensures:
        - Correct portal URL is generated based on service ID.
        Example: `/service_management/details/request/<id>`.
        """
        service = self.service_request
        service._compute_access_url()
        expected_url = f"/service_management/details/request/{service.id}"
        self.assertEqual(service.access_url, expected_url)

    def test_get_report_base_filename(self):
        """
        Test `_get_report_base_filename`.

        Verifies:
        - Generates filename: "Service Management - <service name>".
        - Raises ValueError if called on multiple records
          (due to `ensure_one`).
        """
        service = self.service_request
        service.name = "Test Service Request"
        filename = service._get_report_base_filename()
        expected_filename = "Service Management - Test Service Request"
        self.assertEqual(filename, expected_filename)
        service1 = self.service_request
        service2 = self.env['hr.service'].create({
            'service_category_id': self.service_category.id,
            'employee_id': self.employee_user.id,
            'service_handler_id': self.employee_manager.id,
            'name': "Another Service Request"
        })
        services = service1 | service2
        with self.assertRaises(ValueError):
            services._get_report_base_filename()
