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
from odoo.exceptions import UserError
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAssetAssign(TestCommon):

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.assign = cls.env['asset.assign'].create({
            'asset_id': cls.asset.id,
            'employee_id': cls.employee.id,
            'assign_date': '2000-4-5',
            'department_id': cls.employee.department_id.id,
        })

    def test_onchange_assign_date(self):
        """Test for _onchange_assign_date"""
        with self.assertRaises(UserError):
            self.assign._onchange_assign_date()

    def test_action_assign(self):
        """Test for action_assign function"""
        self.assign.asset_id.is_assign = True
        with self.assertRaises(UserError):
            self.assign.action_assign()
        self.assign.asset_id.is_assign = False

    def test_action_unassign(self):
        """Test for action_unassign function"""
        self.reserved_asset.asset_id, self.reserved_asset.status = self.assign.asset_id.id, 'assign'
        reserved_asset = self.env['asset.reservation'].search(
            [('asset_id', '=', self.assign.asset_id.id), ('status', '=', 'assign')])
        self.assign.action_unassign()
        self.assertEqual(self.assign.asset_id.is_assign, False)
        self.assertEqual(self.assign.status, 'cancel')
        self.assertEqual(reserved_asset.status, 'cancel')

    def test_action_reset_to_draft(self):
        self.assign.asset_id.status = 'lost'
        with self.assertRaises(UserError):
            self.assign.action_reset_to_draft()
        self.assertEqual(self.assign.status, 'draft'  )

    def test_unlink(self):
        asset_id = self.assign.asset_id
        self.assign.unlink()
        self.assertEqual(asset_id.is_assign, False)
        new_assign = self.env['asset.assign'].create({
            'asset_id': self.asset.id,
            'status': 'assign',
            'employee_id': self.employee.id,
            'assign_date': '2000-4-5',
            'department_id': self.employee.department_id.id,
        })
        with self.assertRaises(UserError):
            new_assign.unlink()

