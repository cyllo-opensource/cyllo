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
from odoo.addons.cyllo_map.hooks import uninstall_hook


@tagged('-at_install', 'post_install')
class TestUninstallHook(TransactionCase):
    """
    Test suite for verifying uninstall hook behavior.

    This ensures that when the module uninstall hook executes,
    the system action `contacts.action_contacts` is restored to
    its original expected view mode.
    """

    def test_uninstall_hook(self):
        """
        Validate the uninstall hook behavior:

            ✔ Before hook: manually modify view_mode to simulate module change.
            ✔ Run uninstall hook.
            ✔ After hook: view_mode must be reset to standard Odoo value.
        """

        action = self.env.ref("contacts.action_contacts")
        action.write({'view_mode': 'map,tree,form'})
        self.assertEqual(
            action.view_mode,
            'map,tree,form',
        )
        uninstall_hook(self.env)
        action = self.env['ir.actions.act_window'].browse(action.id)
        self.assertEqual(
            action.view_mode,
            'kanban,tree,form,activity',
        )
