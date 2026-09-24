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


class TestResUsers(TransactionCase):
    """Test methods of the Res Users"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.User = cls.env['res.users'].create({
            'name': 'ABCD',
            'login': 'XYZ',
            'idle_timer': True,
            'idle_time': 72,
        })

    def test_get_change_pwd_view_id(self):
        self.assertEqual(self.User.get_change_pwd_view_id(), self.env.ref(
            'cyllo_dashboard.view_change_password_own_form').id)

    def test_get_groups(self):
        self.assertEqual(self.User.get_groups(), self.env.user.groups_id.ids)

    def test_toggle_auto_edit(self):
        self.User.toggle_auto_edit(True)
        self.assertEqual(self.env.user.auto_edit, True)

    def test_get_auto_edit_value(self):
        self.assertEqual(self.User.get_auto_edit_value(),
                         self.env.user.auto_edit)

    def test_action_change_password_dashboard(self):
        self.env.user._change_password('admin')
        chg_pwd_own = self.env['change.password.own'].create(
            {'old_password': 'admin', 'new_password': 'ABCD', 'confirm_password': 'ABCD', })
        self.assertEqual(chg_pwd_own.action_change_password_dashboard(),
                         {'type': 'ir.actions.client', 'tag': 'reload'})
