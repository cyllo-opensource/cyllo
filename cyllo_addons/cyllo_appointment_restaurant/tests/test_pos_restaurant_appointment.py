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


class TestPosRestaurantAppointment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.floor = cls.env['restaurant.floor'].create({
            'name': 'Main Floor',
        })

    def test_resource_created_on_table_creation(self):
        """Creating a table should create an appointment resource."""
        table = self.env['restaurant.table'].create({
            'name': 'T1',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        self.assertTrue(
            table.appointment_resource_id,
            "Appointment resource should be created automatically."
        )

        self.assertEqual(
            table.appointment_resource_id.capacity,
            4
        )

    def test_resource_name_generation(self):
        """Resource name should be generated correctly."""
        table = self.env['restaurant.table'].create({
            'name': 'T2',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        expected_name = "Main Floor Table T2 (🪑 4 seats)"

        self.assertEqual(
            table.appointment_resource_id.name,
            expected_name
        )

    def test_updating_seats_updates_resource_capacity(self):
        """Changing table seats should update resource capacity."""
        table = self.env['restaurant.table'].create({
            'name': 'T3',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        table.write({
            'seats': 6,
        })

        self.assertEqual(
            table.appointment_resource_id.capacity,
            6
        )

    def test_updating_name_updates_resource_name(self):
        """Changing table name should update resource name."""
        table = self.env['restaurant.table'].create({
            'name': 'T4',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        table.write({
            'name': 'VIP'
        })

        self.assertIn(
            'VIP',
            table.appointment_resource_id.name
        )

    def test_archiving_table_deactivates_resource(self):
        """Archiving a table should archive its resource."""
        table = self.env['restaurant.table'].create({
            'name': 'T5',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        table.write({
            'active': False,
        })

        self.assertFalse(
            table.appointment_resource_id.active
        )

    def test_unlink_table_deletes_resource(self):
        """Deleting a table should delete the linked resource."""
        table = self.env['restaurant.table'].create({
            'name': 'T6',
            'floor_id': self.floor.id,
            'seats': 4,
        })

        resource = table.appointment_resource_id

        table.unlink()

        self.assertFalse(
            resource.exists(),
            "Linked appointment resource should be deleted."
        )

    def test_action_view_pos_tables(self):
        """Verify action_view_pos_tables action."""
        resource = self.env['appointment.resource'].create({
            'name': 'Test Resource',
            'capacity': 4,
            'resource_type': 'room',
        })

        action = resource.action_view_pos_tables()

        self.assertEqual(
            action['type'],
            'ir.actions.act_window'
        )

        self.assertEqual(
            action['res_model'],
            'restaurant.table'
        )

        self.assertEqual(
            action['domain'],
            [('appointment_resource_id', '=', resource.id)]
        )