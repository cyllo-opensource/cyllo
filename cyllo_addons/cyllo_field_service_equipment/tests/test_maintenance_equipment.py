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


class TestMaintenanceEquipment(TransactionCase):
    """
    Test suite for validating the functionality of the
    Maintenance Equipment model with respect to
    equipment history and related service requests.
    """
    @classmethod
    def setUpClass(cls):
        """
        Test data setup for the equipment and service request tests.

        - Creates a partner and a skill category (dependencies for service requests).
        - Creates one equipment (`cls.equipment`) linked to a field service request
          (`cls.field_service_request`).
        - Creates two additional equipment records (`cls.equipment_1`, `cls.equipment_2`)
          for testing the equipment history count functionality.
        """
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Test Skill Category'
        })
        cls.equipment = cls.env['maintenance.equipment'].create({
            'name': 'Test Equipment',
            'maintenance_open_count': 0,
        })
        cls.field_service_request = cls.env['field.service.request'].create({
            'name': 'Test Field Request',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
            'field_service_equipments_ids': [(6, 0, [cls.equipment.id])],
        })
        cls.equipment_model = cls.env['maintenance.equipment']
        cls.service_request_model = cls.env['field.service.request']
        cls.equipment_1 = cls.equipment_model.create({
            'name': 'Test Equipment 1',
        })
        cls.equipment_2 = cls.equipment_model.create({
            'name': 'Test Equipment 2',
        })

    def test_action_view_equipment_history(self):
        """
        Test the `action_view_equipment_history` method.

        Validates that:
        - The returned action is of type `ir.actions.act_window`.
        - The action targets the `field.service.request` model.
        - The domain in the action correctly filters service requests
          related to the equipment.
        - The pre-created service request is included in the result.
        """
        equipment = self.equipment
        action = equipment.action_view_equipment_history()
        self.assertEqual(action['res_model'], 'field.service.request')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertIn('domain', action)
        domain = action['domain']
        self.assertIn(('field_service_equipments_ids', 'in', equipment.ids),
                      domain)
        requests = self.env['field.service.request'].search(domain)
        self.assertIn(self.field_service_request, requests)

    def test_compute_equipment_history_count(self):
        """
        Test the `_compute_equipment_history_count` method.

        Steps:
        - Verify that equipment with no service requests starts with count = 0.
        - Create 2 service requests for `equipment_1` and check that
          its history count updates to 2.
        - Create 1 service request for `equipment_2` and check that
          its history count updates to 1.

        Ensures the computed field `equipment_history_count` correctly reflects
        the number of related service requests.
        """
        self.equipment_1._compute_equipment_history_count()
        self.assertEqual(
            self.equipment_1.equipment_history_count,
            0)
        self.service_request_model.create({
            'name': 'Service Request 1',
            'field_service_equipments_ids': [(6, 0, [self.equipment_1.id])],
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
        })
        self.service_request_model.create({
            'name': 'Service Request 2',
            'field_service_equipments_ids': [(6, 0, [self.equipment_1.id])],
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
        })
        self.equipment_1._compute_equipment_history_count()
        self.assertEqual(
            self.equipment_1.equipment_history_count,
            2
        )
        self.service_request_model.create({
            'name': 'Service Request 3',
            'field_service_equipments_ids': [(6, 0, [self.equipment_2.id])],
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
        })
        self.equipment_2._compute_equipment_history_count()
        self.assertEqual(
            self.equipment_2.equipment_history_count,
            1)
