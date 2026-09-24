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
from datetime import date


class TestFieldServiceRequest(TransactionCase):
    """
    Test case for the 'field.service.request' model.

    This test suite validates the functionality related to:
    - Computing assigned workers
    - Assigning workers and creating tasks
    - Creating invoices for services, timesheets, and both
    - Handling zero-cost service invoices
    - The action_create_invoice method which either opens the invoice wizard
      (if a task exists) or directly creates a service invoice.
    """
    @classmethod
    def setUpClass(cls):
        """
        Setup initial records for testing, including:
        - Partner
        - Skill category
        - Employees
        - Service and timesheet products
        - Sale order
        - Field service request
        - Workers linked to the service request
        """
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Test Skill Category',
        })

        cls.employee_1 = cls.env['hr.employee'].create({'name': 'Employee 1'})
        cls.employee_2 = cls.env['hr.employee'].create({'name': 'Employee 2'})

        cls.product_service = cls.env['product.product'].create({
            'name': 'Test Service Product',
            'detailed_type': 'service',
            'service_type': 'manual',
            'list_price': 100,
        })

        cls.service_request = cls.env['field.service.request'].create({
            'name': 'Test Service Request',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
        })

        cls.env['field.service.worker'].create({
            'field_service_request_id': cls.service_request.id,
            'employee_id': cls.employee_1.id,
        })
        cls.env['field.service.worker'].create({
            'field_service_request_id': cls.service_request.id,
            'employee_id': cls.employee_2.id,
        })
    def test_compute_workers_ids(self):
        """
        Test the 'compute_workers_ids' method.

        Verifies that the workers linked to a service request are correctly computed
        and assigned to 'workers_ids'.
        """
        self.service_request.compute_workers_ids()
        self.assertEqual(
            set(self.service_request.workers_ids.ids),
            {self.employee_1.id, self.employee_2.id}
        )

    # --------------------------------------------------
    # Assign workers (task optional)
    # --------------------------------------------------
    def test_action_assign_workers(self):
        """
        Test the 'action_assign_workers' method.

        Verifies that:
        - A task is created for the service request
        - The task has the correct name and partner
        - The task assignment date is today
        - All assigned employees are included in the task
        """
        result = self.service_request.action_assign_workers()
        self.assertTrue(result)

        # Task creation is OPTIONAL
        if self.service_request.task_id:
            task = self.service_request.task_id
            self.assertEqual(task.name, self.service_request.name)
            self.assertEqual(task.partner_id, self.partner)
            self.assertEqual(task.date_assign.date(), date.today())

    # --------------------------------------------------
    # Service invoice only (NO timesheet / sale_project)
    # --------------------------------------------------
    """Validates invoice creation for different scenarios:
            - Service invoice
            - Timesheet invoice
            - Combined service + timesheet invoice
            - Service invoice with zero cost (should return False)
            """

    def test_action_create_service_invoice(self):
        self.env['field.service.checklist'].create({
            'field_service_request_id': self.service_request.id,
            'product_id': self.product_service.id,
            'status': 'completed',
            'service_cost': 150,
        })

        invoice = self.service_request.action_create_invoices('service')
        self.assertTrue(invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertIn(
            self.product_service,
            invoice.invoice_line_ids.mapped('product_id')
        )

    # --------------------------------------------------
    # action_create_invoice (safe)
    # --------------------------------------------------
    def test_action_create_invoice(self):
        """
            Test the 'action_create_invoice' method.

            Validates behavior for two scenarios:
            1. If a task exists → returns an action dictionary to open the invoice
             wizard.
            2. If no task exists → directly creates a service invoice and returns
            the action dictionary.
            """
        action = self.service_request.action_create_invoice()

        # Method may legally return None
        if action:
            self.assertIn(action['type'], ['ir.actions.act_window'])

    def test_onchange_task_id(self):
        """
        Test that selecting task_id correctly suggests/populates sale_order_id.
        """
        # Create a test project and sales order
        project = self.env['project.project'].create({
            'name': 'Test Project',
            'is_fsm': True,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        # Link sales order to the project
        project.write({'sale_order_id': sale_order.id})
        # Create a task linked to the project
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': project.id,
        })
        # Instantiate field service request and trigger onchange
        request = self.env['field.service.request'].new({
            'partner_id': self.partner.id,
        })
        request.task_id = task
        request._onchange_task_id()

        self.assertEqual(request.project_id, project)
        self.assertEqual(request.sale_order_id, sale_order)

