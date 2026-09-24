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
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import TransactionCase


class TestHrIncident(TransactionCase):
    """
    Test suite for the HR Incident model and its related logic.

    This class validates the behavior of incident management,
    including user roles, stage transitions, access rights,
    onchange methods, and reporting.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up the initial data required for all test cases.

        Creates:
        - A test company
        - A default incident category
        - Email template for notifications
        - HR manager and HR user groups
        - HR manager and employee users
        - Employees linked to users
        - Configuration parameters for emails
        """
        super().setUpClass()

        # Use existing test company (IMPORTANT)
        cls.company = cls.env.company

        # Incident model reference (USED IN TESTS)
        cls.incident_model = cls.env['hr.incident']

        # Category
        cls.category = cls.env['hr.incident.category'].create({
            'name': 'Safety'
        })

        # Mail template fix
        template = cls.env.ref(
            "cyllo_hr_incident_management.mail_template_incident_receptor_notification_email"
        )
        template.write({"email_from": "noreply@example.com"})

        # Groups
        cls.hr_manager_group = cls.env.ref('hr.group_hr_manager')
        cls.hr_user_group = cls.env.ref('hr.group_hr_user')

        # Users
        cls.user_manager = cls.env['res.users'].create({
            'name': 'HR Manager User',
            'login': 'hrmanager@test.com',
            'email': 'hrmanager@test.com',
            'groups_id': [(6, 0, [cls.hr_manager_group.id])],
            'company_id': cls.company.id,
        })

        cls.user_employee = cls.env['res.users'].create({
            'name': 'Normal User',
            'login': 'normaluser@test.com',
            'email': 'normaluser@test.com',
            'groups_id': [(6, 0, [cls.hr_user_group.id])],
            'company_id': cls.company.id,
        })

        # Employees (THIS FIXES THE ERROR)
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Employee Manager',
            'user_id': cls.user_manager.id,
            'company_id': cls.company.id,
        })

        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Employee User',
            'user_id': cls.user_employee.id,
            'company_id': cls.company.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.company.id,
        })

        # Mail config (used by notifications)
        cls.env['ir.config_parameter'].sudo().set_param(
            "mail.catchall.domain", "example.com"
        )
        cls.env['ir.config_parameter'].sudo().set_param(
            "mail.default.from", "noreply@example.com"
        )

    def test_compute_is_hr_manager(self):
        """
        Test the computed field `is_hr_manager`.

        Ensures:
        - Incidents created by HR manager users set `is_hr_manager=True`.
        - Incidents created by normal HR users set `is_hr_manager=False`.
        """
        self.env = self.env(user=self.user_manager)
        incident = self.env['hr.incident'].create({
            'incident_category_id': self.env['hr.incident.category'].create({
                'name': 'Saftey'
            }).id,
            'incident_initiator_id': self.employee_manager.id,
            'incident_receptor_id': self.employee_manager.id,
        })
        self.assertTrue(incident.is_hr_manager)
        self.env = self.env(user=self.user_employee)
        incident = self.env['hr.incident'].create({
            'incident_category_id': self.env['hr.incident.category'].sudo().create({
                'name': 'Discipline'
            }).id,
            'incident_initiator_id': self.employee_user.id,
            'incident_receptor_id': self.employee_manager.id,
        })
        self.assertFalse(incident.is_hr_manager)

    def test_read_group_stage(self):
        """
        Test `_read_group_stage` method.

        Ensures the correct stage dictionary is returned
        with expected keys and labels: New, Submitted, Assigned, Ongoing, Completed.
        """
        stages = self.incident_model._read_group_stage([], [], [])
        expected_stages = {
            'new': 'New',
            'submitted': 'Submitted',
            'assigned': 'Assigned',
            'ongoing': 'Ongoing',
            'completed': 'Completed',
        }
        self.assertEqual(stages, expected_stages)
        self.assertIn('assigned', stages)
        self.assertEqual(len(stages), 5)

    def test_unlink_except_posted(self):
        """
        Test `unlink` restrictions on incidents.

        Validates:
        - Incidents in 'new' stage cannot be deleted (raises UserError).
        - Incidents in 'cancel' stage can be deleted.
        - Incidents in 'new' stage can be deleted if `force_delete=True` in context.
        """
        incident = self.env['hr.incident'].create({
            'incident_category_id': self.category.id,
            'incident_initiator_id': self.employee.id,
            'incident_receptor_id': self.employee.id,
            'incident_stage': 'new',
        })
        with self.assertRaises(UserError):
            incident.unlink()

        incident = self.env['hr.incident'].create({
            'incident_category_id': self.category.id,
            'incident_initiator_id': self.employee.id,
            'incident_receptor_id': self.employee.id,
            'incident_stage': 'cancel',
        })
        incident.unlink()
        self.assertFalse(
            self.env['hr.incident'].search([('id', '=', incident.id)]))

        incident = self.env['hr.incident'].create({
            'incident_category_id': self.category.id,
            'incident_initiator_id': self.employee.id,
            'incident_receptor_id': self.employee.id,
            'incident_stage': 'new',
        })
        incident.with_context(force_delete=True).unlink()
        self.assertFalse(
            self.env['hr.incident'].search([('id', '=', incident.id)]))

    def test_onchange_incident_initiator_id(self):
        """
        Test `_onchange_incident_initiator_id` logic.

        Validates:
        - If initiator has a parent, parent is set as receptor.
        - If initiator has a department with a manager, manager is set as receptor.
        - If neither exists, raises ValidationError.
        """
        self.manager = self.env['res.users'].create({
            'name': 'Dept Manager',
            'login': 'manager@example.com',
        })
        self.employee_manager = self.env['hr.employee'].create({
            'name': 'Dept Manager Emp',
            'user_id': self.manager.id,
        })
        self.department = self.env['hr.department'].create({
            'name': 'IT Department',
            'manager_id': self.employee_manager.id,
        })
        self.employee_initiator = self.env['hr.employee'].create({
            'name': 'John Doe',
            'department_id': self.department.id,
        })
        self.incident = self.env['hr.incident'].create({
            'name': 'Test Incident',
            'incident_initiator_id': self.employee_initiator.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': self.employee_manager.id,
        })
        parent_emp = self.env['hr.employee'].create({'name': 'Parent Manager'})
        self.employee_initiator.parent_id = parent_emp
        self.incident.incident_initiator_id = self.employee_initiator
        self.incident._onchange_incident_initiator_id()
        self.assertEqual(self.incident.incident_receptor_id.id, parent_emp.id)
        self.employee_initiator.parent_id = False
        self.incident.incident_initiator_id = self.employee_initiator
        self.incident._onchange_incident_initiator_id()
        self.assertEqual(self.incident.incident_receptor_id.id,
                         self.department.manager_id.id)
        self.employee_initiator.parent_id = False
        self.employee_initiator.department_id.manager_id = False

        self.incident.incident_initiator_id = self.employee_initiator
        with self.assertRaises(ValidationError):
            self.incident._onchange_incident_initiator_id()

    def test_action_submit_incident_request(self):
        """
        Test `action_submit_incident_request`.

        Ensures:
        - Initiator can submit incident (stage changes to 'submitted').
        - HR Manager can also submit.
        - Outsider user receives a warning notification.
        """
        manager_user = self.env['res.users'].create({
            'name': 'Dept Manager',
            'login': 'manager@example.com',
        })
        employee_manager = self.env['hr.employee'].create({
            'name': 'Dept Manager Emp',
            'user_id': manager_user.id,
        })
        department = self.env['hr.department'].create({
            'name': 'IT Department',
            'manager_id': employee_manager.id,
        })
        employee_initiator = self.env['hr.employee'].create({
            'name': 'John Doe',
            'department_id': department.id,
        })
        incident = self.env['hr.incident'].with_user(manager_user).create({
            'incident_initiator_id': employee_initiator.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': employee_manager.id,
        })
        incident.current_user_employee_id = employee_initiator
        incident.is_hr_manager = False
        result1 = incident.action_submit_incident_request()
        self.assertEqual(incident.incident_stage, "submitted")
        self.assertTrue(incident.is_submitted)
        self.assertIsNone(result1, "Initiator should be able to submit")
        incident2 = incident.copy()
        incident2.current_user_employee_id = employee_manager
        incident2.is_hr_manager = True
        result2 = incident2.action_submit_incident_request()
        self.assertEqual(incident2.incident_stage, "submitted")
        self.assertTrue(incident2.is_submitted)
        self.assertIsNone(result2, "HR Manager should be able to submit")
        outsider_user = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider@example.com',
        })
        outsider_emp = self.env['hr.employee'].create({
            'name': 'Outsider Emp',
            'user_id': outsider_user.id,
        })
        incident3 = incident.copy()
        incident3.current_user_employee_id = outsider_emp
        incident3.is_hr_manager = False
        result3 = incident3.action_submit_incident_request()
        self.assertIsInstance(result3, dict)
        self.assertEqual(result3["tag"], "display_notification")

    def test_action_assign_to_me(self):
        """
        Test `action_assign_to_me`.

        Validates:
        - Receptor can assign the incident to themselves.
        - HR Manager can also assign to themselves.
        - Outsiders receive a warning notification.
        """
        hr_manager_user = self.env['res.users'].create({
            'name': 'HR Manager',
            'login': 'hrmanager2@example.com',
            'email': 'hrmanager2@example.com',
        })
        hr_manager_emp = self.env['hr.employee'].create({
            'name': 'HR Manager Emp',
            'user_id': hr_manager_user.id,
        })
        receptor_user = self.env['res.users'].create({
            'name': 'Receptor User',
            'login': 'receptor@example.com',
            'email': 'receptor@example.com',
        })
        receptor_emp = self.env['hr.employee'].create({
            'name': 'Receptor Emp',
            'user_id': receptor_user.id,
        })
        outside_user = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider@example.com'
        })
        outside_emp = self.env['hr.employee'].create({
            'name': 'Outside Emp',
            'user_id': outside_user.id,
        })
        incident = self.env['hr.incident'].with_user(receptor_user).create({
            'incident_initiator_id': receptor_emp.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': receptor_emp.id,
        })
        incident.current_user_employee_id = receptor_emp
        incident.is_hr_manager = False
        result1 = incident.action_assign_to_me()
        self.assertEqual(incident.incident_stage, "assigned")
        self.env.user = receptor_user.sudo()
        self.assertEqual(incident.incident_handler_id, self.env.user.employee_id)
        self.assertIsNone(result1)
        incident2 = incident.copy()
        incident2.current_user_employee_id = hr_manager_emp
        incident2.is_hr_manager = True
        result2 = incident2.action_assign_to_me()
        self.assertEqual(incident2.incident_stage, "assigned")
        self.assertEqual(incident2.incident_handler_id, self.env.user.employee_id)
        self.assertIsNone(result2)
        incident3 = incident.copy()
        incident3.current_user_employee_id = outside_emp
        incident3.is_hr_manager = False
        result3 = incident3.action_assign_to_me()
        self.assertIsInstance(result3, dict)
        self.assertEqual(result3["tag"], "display_notification")
        self.assertIn('Only the receptor or administrator',
                      result3['params']['message'])

    def test_action_assign_handler(self):
        """
        Test `action_assign_handler`.

        Ensures:
        - Receptor/HR manager can assign a handler.
        - If handler is missing, a warning notification is raised.
        - Outsiders cannot assign and receive a warning.
        """
        hr_manager_user = self.env['res.users'].create({
            'name': 'HR Manager',
            'login': 'hrmanager3@example.com',
            'email': 'hrmanager3@example.com',
        })
        hr_manager_emp = self.env['hr.employee'].create({
            'name': 'HR Manager Emp',
            'user_id': hr_manager_user.id,
        })
        receptor_user = self.env['res.users'].create({
            'name': 'Receptor User',
            'login': 'receptor2@example.com',
            'email': 'receptor2@example.com',
        })
        receptor_emp = self.env['hr.employee'].create({
            'name': 'Receptor Emp',
            'user_id': receptor_user.id,
        })
        handler_user = self.env['res.users'].create({
            'name': 'Handler User',
            'login': 'handler@example.com',
            'email': 'handler@example.com',
        })
        handler_emp = self.env['hr.employee'].create({
            'name': 'Handler Emp',
            'user_id': handler_user.id,
        })
        outside_user = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider2@example.com'
        })
        outside_emp = self.env['hr.employee'].create({
            'name': 'Outside Emp',
            'user_id': outside_user.id,
        })
        incident = self.env['hr.incident'].with_user(receptor_user).create({
            'incident_initiator_id': receptor_emp.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': receptor_emp.id,
        })
        incident.current_user_employee_id = receptor_emp
        incident.is_hr_manager = True
        result1 = incident.action_assign_to_me()
        self.assertEqual(incident.incident_stage, "assigned")
        self.assertIsNone(result1)
        incident2 = incident.copy()
        incident2.current_user_employee_id = receptor_emp
        incident2.is_hr_manager = False
        result2 = incident2.action_assign_handler()
        self.assertEqual(incident2.incident_stage, "assigned")
        self.assertIsNone(result2)
        incident3 = self.env['hr.incident'].create({
            'incident_initiator_id': receptor_emp.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': receptor_emp.id,
        })
        incident3.current_user_employee_id = hr_manager_emp
        incident3.is_hr_manager = True
        result3 = incident3.action_assign_handler()
        self.assertIsInstance(result3, dict)
        self.assertEqual(result3["tag"], "display_notification")
        self.assertIn("Please assign an employee",
                      result3["params"]["message"])

        incident4 = incident.copy()
        incident4.current_user_employee_id = outside_emp
        incident4.is_hr_manager = False
        result4 = incident4.action_assign_handler()
        self.assertIsInstance(result4, dict)
        self.assertEqual(result4["tag"], "display_notification")
        self.assertIn("Only the receptor or administrator",
                      result4["params"]["message"])

    def test_action_start_incident_enquiry(self):
        """
        Test `action_start_incident_enquiry`.

        Ensures:
        - Handler can start enquiry (stage → ongoing).
        - HR Manager can also start enquiry.
        - Outsiders receive a warning notification.
        """
        hr_manager_user = self.env['res.users'].create({
            'name': 'HR Manager',
            'login': 'hrmanager@example.com',
            'email': 'hrmanager@example.com',
        })
        hr_manager_emp = self.env['hr.employee'].create({
            'name': 'HR Manager Emp',
            'user_id': hr_manager_user.id,
        })
        handler_user = self.env['res.users'].create({
            'name': 'Handler User',
            'login': 'handler@example.com',
            'email': 'handler@example.com',
        })
        handler_emp = self.env['hr.employee'].create({
            'name': 'Handler Emp',
            'user_id': handler_user.id,
        })
        receptor_user = self.env['res.users'].create({
            'name': 'Receptor User',
            'login': 'receptor@example.com',
        })
        receptor_emp = self.env['hr.employee'].create({
            'name': 'Receptor Emp',
            'user_id': receptor_user.id,
        })
        incident = self.env['hr.incident'].create({
            'incident_initiator_id': receptor_emp.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': receptor_emp.id,
            'incident_handler_id': handler_emp.id,
            'incident_stage': 'assigned',
        })
        incident = incident.with_user(handler_user)
        incident.current_user_employee_id = handler_emp
        incident.is_hr_manager = False
        result1 = incident.action_start_incident_enquiry()
        self.assertEqual(incident.incident_stage, "ongoing")

        incident.write({'incident_stage': 'assigned'})
        incident = incident.with_user(hr_manager_user)
        incident.current_user_employee_id = hr_manager_emp
        incident.is_hr_manager = True
        result2 = incident.action_start_incident_enquiry()
        self.assertEqual(incident.incident_stage, "ongoing")

        outside_user = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider@example.com'
        })
        outside_emp = self.env['hr.employee'].create({
            'name': 'Outside Emp',
            'user_id': outside_user.id,
        })
        incident.write({'incident_stage': 'assigned'})
        incident = incident.with_user(outside_user)
        incident.current_user_employee_id = outside_emp
        incident.is_hr_manager = False
        result3 = incident.action_start_incident_enquiry()
        self.assertIsInstance(result3, dict)
        self.assertEqual(result3["tag"], "display_notification")
        self.assertEqual(result3["type"], 'ir.actions.client')

    def test_action_mark_as_done(self):
        """
        Test `action_mark_as_done`.

        Validates:
        - Handler can mark an incident as done (stage → completed, date_done set).
        - HR Manager can also mark as done.
        - Outsiders receive a warning notification.
        """
        hr_manager_user = self.env['res.users'].create({
            'name': 'HR Manager',
            'login': 'hrmanager3@example.com',
            'email': 'hrmanager3@example.com',
        })
        hr_manager_emp = self.env['hr.employee'].create({
            'name': 'HR Manager Emp',
            'user_id': hr_manager_user.id,
        })
        handle_user = self.env['res.users'].create({
            'name': 'Handle User',
            'login': 'handle@example.com',
            'email': 'handle@example.com',
        })
        handle_emp = self.env['hr.employee'].create({
            'name': 'handle Emp',
            'user_id': handle_user.id,
        })
        outside_user = self.env['res.users'].create({
            'name': 'Outsider',
            'login': 'outsider3@example.com',
            'email': 'outsider3@example.com'
        })
        outside_emp = self.env['hr.employee'].create({
            'name': 'Outside Emp',
            'user_id': outside_user.id,
        })
        incident = self.env['hr.incident'].create({
            'incident_initiator_id': handle_emp.id,
            'incident_category_id': self.category.id,
            'incident_receptor_id': hr_manager_emp.id,
            'incident_handler_id': handle_emp.id,
            'incident_stage': 'ongoing',
        })
        incident.current_user_employee_id = handle_emp
        incident.is_hr_manager = False
        result1 = incident.action_mark_as_done()
        self.assertEqual(incident.incident_stage, "completed")
        self.assertIsNotNone(incident.date_done)
        self.assertIsNone(result1)

        incident2 = incident.copy()
        incident2.current_user_employee_id = hr_manager_emp
        incident2.is_hr_manager = True
        result2 = incident2.action_mark_as_done()
        self.assertEqual(incident2.incident_stage, "completed")
        self.assertIsNotNone(incident2.date_done)
        self.assertIsNone(result2)

        incident3 = incident.copy()
        incident3.current_user_employee_id = outside_emp
        incident3.is_hr_manager = False
        result3 = incident3.action_mark_as_done()
        self.assertIsInstance(result3, dict)
        self.assertEqual(result3["tag"], "display_notification")
        self.assertEqual(result3['params']['type'], "warning")

    def test_compute_access_url(self):
        """
        Test `_compute_access_url`.

        Ensures the access URL is correctly generated
        as `/incident_management/details/request/<incident_id>`.
        """
        category = self.env['hr.incident.category'].create({
            'name': 'Test Category'
        })
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee'
        })
        incident = self.env['hr.incident'].create({
            'name': 'Test Incident',
            'incident_category_id': category.id,
            'incident_receptor_id': employee.id,
            'incident_initiator_id': employee.id,
        })
        incident._compute_access_url()
        expected_url = (f'/incident_management/details/request/{incident.id}')
        self.assertEqual(incident.access_url, expected_url)

    def test_get_report_base_filename(self):
        """
        Test `_get_report_base_filename`.

        Ensures:
        - A proper filename is generated with incident name.
        - Raises ValueError if called on multiple records.
        """
        incident = self.env['hr.incident'].create({
            'name': 'Network Failure',
            'incident_category_id': self.category.id,
            'incident_receptor_id': self.employee.id,
            'incident_initiator_id': self.employee.id,
        })
        filename = incident._get_report_base_filename()
        expected_filename = "Incident Management - Network Failure"
        self.assertEqual(filename, expected_filename)
        incident2 = self.env['hr.incident'].create({
            'name': 'Test Incident',
            'incident_category_id': self.category.id,
            'incident_receptor_id': self.employee.id,
            'incident_initiator_id': self.employee.id,
        })
        incidents = incident | incident2
        with self.assertRaises(ValueError):
            incidents._get_report_base_filename()

    def test_action_cancel(self):
        """
        Test `action_cancel`.

        Ensures:
        - Initiator can cancel incident (stage → cancel).
        - Unauthorized users receive a warning notification.
        """
        employee_initiator = self.env['hr.employee'].create({
            'name': 'Initiator',
        })
        employee_receptor = self.env['hr.employee'].create({
            'name': 'Receptor',
        })
        employee_handler = self.env['hr.employee'].create({
            'name': 'Handler',
        })
        employee_other = self.env['hr.employee'].create({
            'name': 'Other',
        })
        user_initiator = self.env['res.users'].create({
            'name': 'User Initiator',
            'login': 'initiator@example.com',
            'employee_id': employee_initiator.id,
        })
        user_other = self.env['res.users'].create({
            'name': 'User Other',
            'login': 'other@example.com',
        })
        employee_other.user_id = user_other.id

        incident = self.env['hr.incident'].create({
            'name': 'Test Incident',
            'incident_initiator_id': employee_initiator.id,
            'incident_receptor_id': employee_receptor.id,
            'incident_handler_id': employee_handler.id,
            'incident_stage': 'new',
            'incident_category_id': self.category.id,
        })
        self.env.user = user_initiator
        incident.action_cancel()
        self.assertEqual(incident.incident_stage, 'cancel')
        self.env.user = user_other
        incident.is_hr_manager = False
        result = incident.action_cancel()
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn("not allowed", result['params']['message'])

    def test_action_set_to_new(self):
        """
        Test `action_set_to_new`.

        Ensures:
        - Authorized user (initiator or HR manager) can reset incident to 'new'.
        - Outsiders receive a warning notification.
        """
        employee_initiator = self.env['hr.employee'].create(
            {'name': 'Initiator'})
        employee_receptor = self.env['hr.employee'].create({'name': 'Receptor'})
        employee_handler = self.env['hr.employee'].create({'name': 'Handler'})
        employee_other = self.env['hr.employee'].create({'name': 'Other'})
        user_initiator = self.env['res.users'].create({
            'name': 'User Initiator',
            'login': 'initiator@example.com',
            'employee_id': employee_initiator.id,
        })
        user_other = self.env['res.users'].create({
            'name': 'User Other',
            'login': 'other@example.com',
            'groups_id': [(6, 0, [])],
        })
        employee_other.user_id = user_other.id

        incident = self.env['hr.incident'].create({
            'name': 'Test Incident',
            'incident_initiator_id': employee_initiator.id,
            'incident_receptor_id': employee_receptor.id,
            'incident_handler_id': employee_handler.id,
            'incident_stage': 'cancel',
            'incident_category_id': self.category.id,
        })

        self.env.user = user_initiator
        result = incident.action_set_to_new()
        self.assertIsNone(result, "Authorized user should not return a dict")
        self.assertEqual(incident.incident_stage, 'new',
                         "Incident should be reset to 'new'")
        self.env.user = user_other
        incident.is_hr_manager = False
        result = incident.action_set_to_new()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'warning')
        self.assertEqual(result['params']['title'], 'Warning')
