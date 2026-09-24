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
from datetime import datetime

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.addons.cyllo_field_service.tests.common import TestCylloFieldService


class TestServiceRequest(TestCylloFieldService):
    """Test for field.service.request"""

    def test_action_submit(self):
        """When submit button clicked name field got value, state change to submit, date changes to current date"""
        self.service_request.action_submit()
        self.assertTrue(self.service_request.name)
        self.assertEqual(self.service_request.state, 'submit')
        self.assertEqual(self.service_request.submit_date.date(),
                         datetime.now().date())

    def test_action_confirm(self):
        self.service_request.action_confirm()
        self.assertEqual(self.service_request.state, 'submit')

    def test_action_fetch_suitable_workers(self):
        """Test the action_fetch_suitable_workers method for creating employee suggestions."""
        # Ensure no employee suggestions exist initially for the service request
        initial_suggestion_count = self.env[
            'field.service.employee.suggestion'].search_count([
            ('field_service_request_id', '=', self.service_request_1.id)
        ])
        self.assertEqual(initial_suggestion_count, 0,
                         "No suggestions should exist initially.")
        self.service_request_1.action_fetch_suitable_workers()

        # Check if a suggestion is created for Employee 1 (who has the matching skill)
        suggestions = self.env['field.service.employee.suggestion'].search([
            ('field_service_request_id', '=', self.service_request_1.id)
        ])
        self.assertEqual(len(suggestions), 1,
                         "Exactly one suggestion should be created.")
        suggestion = suggestions[0]
        self.assertEqual(suggestion.employee_id, self.employee,
                         "The suggestion should be for Employee 1.")
        self.assertIn(self.hr_skill.id, suggestion.skill_ids.ids,
                      "The suggestion should include the required skill.")
        no_suggestions = self.env['field.service.employee.suggestion'].search([
            ('employee_id', '=', self.employee_2.id),
            ('field_service_request_id', '=', self.service_request_1.id)
        ])
        self.assertFalse(no_suggestions,
                         "No suggestions should be created for employees without required skills.")
        # Verify notification behavior when no suitable employees exist
        self.service_request_1.hr_skill_ids = [(6, 0, [self.hr_skill_3.id])]
        notification = self.service_request_1.action_fetch_suitable_workers()
        self.assertEqual(notification.get('type'), 'ir.actions.client',
                         "Notification action type should be 'client'.")
        self.assertEqual(notification.get('tag'), 'display_notification',
                         "Notification tag should be 'display_notification'.")
        self.assertEqual("There are no employees who possess this skill",
                         notification['params']['message'],
                         msg="Notification message should indicate no suitable employees.")

    def test_action_assign_workers(self):
        """When action_submit function is called the state changes to
         submitted, then suitable employees are fetched, after fetching the
         employees, for testing purpose chosen last created worker, then run
         the function to add the employee as a worker, then
         action_assign_workers function run, at the time state changes from
         submit to assigned state"""
        self.service_request.field_service_worker_ids = self.field_service_worker.ids
        self.service_request.action_assign_workers()
        self.assertEqual(self.service_request.state, 'assigned')
        self.service_request.skill_category_id = False
        notification = self.service_request.action_assign_workers()
        self.assertEqual("Missing Skill Category",
                         notification['params']['title'],
                         msg="Notification title should indicate missing skill category.")

    def test_action_draft(self):
        self.service_request2.action_draft()
        self.assertEqual(self.service_request2.state, 'draft')

    def test_action_service_start(self):
        with self.assertRaises(UserError,
                               msg="No Workers where assigned to perform this service"):
            self.service_request.action_service_start()
        self.service_request.action_submit()
        self.service_request.action_fetch_suitable_workers()
        # Calling a function from field.service.employee.suggestion
        self.env['field.service.employee.suggestion'].search([], limit=1,
                                                             order="id desc").action_add_workers()
        self.service_request.action_assign_workers()
        self.assertEqual(self.service_request.state, 'assigned')
        with self.assertRaises(UserError):
            self.service_request.action_service_start()

    def test_action_mark_as_done(self):
        notification = self.service_request2.action_mark_as_done()
        self.assertEqual(
            "There are still pending checklist items that require completion",
            notification['params']['message'],
            msg="Notification title should indicate missing checklist template.")
        self.assertEqual(self.service_request2.state, 'submit')
        self.service_request.action_mark_as_done()
        self.assertEqual(self.service_request.state, 'completed')

    def test_action_create_invoice(self):
        self.service_request3.action_create_invoice()
        self.assertEqual(len(self.service_request3.move_ids), 2)

    def test_compute_ready_to_invoice(self):
        self.service_request3.action_create_invoice()
        self.assertEqual(self.service_request3.num_invoices, 0)
        self.service_request3._compute_ready_to_invoice()
        self.assertFalse(self.service_request3.ready_to_invoice)

    def test_get_report_base_filename(self):
        result = self.service_request._get_report_base_filename()
        self.assertEqual(result, 'Field Service Request- FS00001')

    def test_compute_access_url(self):
        self.assertEqual(self.service_request3.access_url,
                         f'/field_service_request/{self.service_request3.id}')

    def test_unlink_except_posted(self):
        with self.assertRaises(UserError,
                               msg="You can delete requests in draft state only"):
            self.service_request3._unlink_except_posted()

    def test_onchange_skill_category_id(self):
        """service_checklist_ids' changes with skill_category_id"""
        skill_category = self.env['field.service.skill.category'].create({
            'name': 'Test category',
            'company_id': self.company.id,
            'service_checklist_ids': [(fields.Command.create({
                'product_id': self.product2.id
            }))]
        })
        service_request = self.env['field.service.request'].create({
            'name': 'FS00003',
            'partner_id': self.partner.id,
            'user_id': self.user.id,
            'state': 'submit',
            'submit_date': '2023-11-30',
            'hr_skill_ids': self.skill_category.ids,
            'move_ids': self.account_move.ids,
            'ready_to_invoice': False,
            'skill_category_id': skill_category.id
        })
        service_request._onchange_skill_category_id()
        self.assertEqual(service_request.service_checklist_ids.product_id,
                         skill_category.service_checklist_ids.product_id,
                         )

    def test_onchange_date_assigned(self):
        self.service_request.date_deadline = '2023-11-20'
        self.service_request.date_assigned = '2023-11-30'
        with self.assertRaises(ValidationError):
            self.service_request._onchange_date_assigned()
