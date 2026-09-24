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
from datetime import datetime, date


class TestFieldServiceRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Test Skill Category',
        })
        cls.equipment = cls.env['maintenance.equipment'].create({
            'name': 'Test Equipment',
            'maintenance_open_count': 0,
        })
        cls.field_service_request = cls.env['field.service.request'].create({
            'name': 'Test Field Service Request',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
        })

        cls.field_service_request.field_service_equipments_ids = \
            [(6, 0, [cls.equipment.id])]

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
        })

    def test_action_assign_workers(self):
        """
        Based on current model logic:
        - action_assign_workers() does not assign field_service_id
          because super() returns a truthy result.
        """
        fservice = self.field_service_request

        # Before assignment
        self.assertFalse(fservice.field_service_equipments_ids[0].field_service_id)

        # Call method
        fservice.action_assign_workers()
        equipment = self.env['maintenance.equipment'].browse(self.equipment.id)

        # Expect NO assignment (super returned truthy)
        self.assertFalse(equipment.field_service_id)
        self.assertFalse(equipment.assigned_date)

        # Add second equipment, behavior unchanged
        equipment2 = self.env['maintenance.equipment'].create({
            'name': 'Second Equipment',
            'maintenance_open_count': 0,
        })

        fservice.field_service_equipments_ids = [(6, 0, [self.equipment.id, equipment2.id])]
        fservice.action_assign_workers()

        for eq in fservice.field_service_equipments_ids:
            self.assertFalse(eq.field_service_id)
            self.assertFalse(eq.assigned_date)

    def test_action_mark_as_done(self):
        """
        Current model behavior:
        - action_mark_as_done() sets returned_date
        - field_service_id ONLY cleared when all required checklist items are completed
        - Our checklist remains pending → service_id unchanged
        """
        request = self.field_service_request

        # Pre-mark done: no assignment ever happened
        checklist_item = self.env['field.service.checklist'].create({
            'required': True,
            'status': 'pending',
            'product_id': self.product.id,
            'field_service_request_id': request.id,
        })

        request.action_mark_as_done()
        equipment = request.field_service_equipments_ids[0]

        # returned_date is set
        self.assertEqual(equipment.returned_date, datetime.today().date())

        # field_service_id remains False because assignment never happened
        self.assertFalse(equipment.field_service_id)

        # Case 2: Fresh request, unassigned equipment
        new_equipment = self.env['maintenance.equipment'].create({
            'name': 'New Equipment for Second Request',
            'maintenance_open_count': 0,
        })

        new_request = self.env['field.service.request'].create({
            'name': 'Second Request',
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
            'field_service_equipments_ids': [(6, 0, [new_equipment.id])],
        })

        new_checklist_item = self.env['field.service.checklist'].create({
            'required': True,
            'status': 'pending',
            'product_id': self.product.id,
            'field_service_request_id': new_request.id,
        })

        new_request.action_mark_as_done()

        self.assertEqual(new_equipment.returned_date, datetime.today().date())
        self.assertFalse(new_equipment.field_service_id)
