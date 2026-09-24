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
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestFieldServiceEmployeeSuggestion(TransactionCase):
    """Test cases for methods in the FieldServiceEmployeeSuggestion model."""

    @classmethod
    def setUpClass(cls):
        """Setup records required for all tests."""
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.company = cls.env['res.company'].create({'name': 'Test Company'})
        cls.skill_type = cls.env['hr.skill.type'].create({'name': 'Electrical'})
        cls.skill = cls.env['hr.skill'].create({
            'name': 'Test skill',
            'skill_type_id': cls.skill_type.id,
        })
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Category',
            'company_id': cls.company.id,
            'hr_skill_ids': cls.skill.ids,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Doe',
            'availability_status': 'available',
        })
        cls.service_request = cls.env['field.service.request'].create({
            'name': 'FS001',
            'description': 'Test Service',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id
        })
        cls.suggestion = cls.env['field.service.employee.suggestion'].create({
            'employee_id': cls.employee.id,
            'skill_ids': [(6, 0, [cls.skill.id])],
            'field_service_request_id': cls.service_request.id,
            'availability_status': cls.employee.availability_status,
        })

    def test_compute_sequence(self):
        """Test sequence computation logic for employee suggestion."""
        suggestion = self.suggestion
        suggestion.added_to_workers = False
        suggestion.availability_status = 'available'
        suggestion._compute_sequence()
        self.assertEqual(suggestion.sequence, 0)
        suggestion.availability_status = 'reserved'
        suggestion._compute_sequence()
        self.assertEqual(suggestion.sequence, 1)
        suggestion.added_to_workers = True
        suggestion.availability_status = 'available'
        suggestion._compute_sequence()
        self.assertEqual(suggestion.sequence, 2)
        suggestion.added_to_workers = True
        suggestion.availability_status = 'reserved'
        suggestion._compute_sequence()
        self.assertEqual(suggestion.sequence, 3)

    def test_action_add_workers(self):
        """Test assigning one employee to the service request."""
        suggestion = self.suggestion.with_context(
            field_service_request_id=self.service_request
        )
        suggestion.action_add_workers()
        worker = self.env['field.service.worker'].search([
            ('employee_id', '=', self.employee.id),
            ('field_service_request_id', '=', self.service_request.id)
        ])
        self.assertTrue(worker)
        self.assertTrue(suggestion.added_to_workers)

    def test_action_add_workers_bulk(self):
        """Test bulk assigning employees."""
        emp2 = self.env['hr.employee'].create({
            'name': 'Jane Doe',
            'availability_status': 'available',
        })
        sugg2 = self.env['field.service.employee.suggestion'].create({
            'employee_id': emp2.id,
            'availability_status': emp2.availability_status,
            'field_service_request_id': self.service_request.id,
        })
        suggestions = self.suggestion | sugg2
        suggestions = suggestions.with_context(field_service_request_id=self.service_request)
        suggestions.action_add_workers_bulk()
        workers = self.service_request.field_service_worker_ids.mapped('employee_id')
        self.assertIn(self.employee, workers)
        self.assertIn(emp2, workers)
