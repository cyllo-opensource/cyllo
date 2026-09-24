# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestManufacturingMpsConfigSettings(common.TransactionCase):
    """Tests for Manufacturing MPS settings and loaded actions."""

    def test_01_client_action_and_menu_are_loaded(self):
        action = self.env.ref('cyllo_manufacturing_mps.action_mps_schedule')
        menu = self.env.ref('cyllo_manufacturing_mps.menu_mps_schedule')
        group = self.env.ref('cyllo_manufacturing_mps.group_mps_enabled')

        self.assertEqual(action.tag, 'cyllo_manufacturing_mps.mps')
        self.assertEqual(action.name, 'MPS')
        self.assertEqual(menu.action, action)
        self.assertIn(group, menu.groups_id)

    def test_02_set_values_updates_cron_interval_and_active_state(self):
        cron = self.env.ref('cyllo_manufacturing_mps.ir_cron_mps_automate_orders')
        settings = self.env['res.config.settings'].create({
            'is_mps': True,
            'mps_default_timerange': 'week',
        })

        settings.set_values()

        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, 'weeks')
        self.assertEqual(cron.interval_number, 1)

    def test_03_set_values_syncs_mrp_managers_to_mps_group(self):
        manager_group = self.env.ref('mrp.group_mrp_manager')
        mps_group = self.env.ref('cyllo_manufacturing_mps.group_mps_enabled')
        manager_user = self.env['res.users'].create({
            'name': 'MPS Manager User',
            'login': 'mps_manager_user',
            'email': 'mps_manager_user@example.com',
            'groups_id': [(6, 0, [manager_group.id])],
        })

        self.env['res.config.settings'].create({
            'is_mps': True,
            'mps_default_timerange': 'month',
        }).set_values()

        self.assertIn(manager_user, mps_group.users)

        self.env['res.config.settings'].create({
            'is_mps': False,
            'mps_default_timerange': 'month',
        }).set_values()

        self.assertNotIn(manager_user, mps_group.users)

