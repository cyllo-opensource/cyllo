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


class TestAssetReservation(TestCommon):
    """Test class for asset reservation"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()

    def test_onchange_reservation_date(self):
        """Test for _onchange_reservation_date function"""
        reservation = self.reserved_asset
        reservation.start_date, reservation.end_date = '7000-05-10', '7000-05-05'
        with self.assertRaises(UserError):
            reservation._onchange_reservation_date()
        reservation.start_date, reservation.end_date = '4000-05-02', '7000-05-09'
        with self.assertRaises(UserError):
            reservation._onchange_reservation_date()
        reservation.start_date, reservation.end_date = '7000-05-07', '7000-05-09'
        reservation._onchange_reservation_date()

    def test_action_assign_asset(self):
        """Test for action_assign_asset function"""
        reservation = self.reserved_asset
        action = reservation.action_assign_asset()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'asset.assign')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')
        context = action.get('context', {})
        self.assertEqual(context.get('default_asset_id'), reservation.asset_id.id)
        self.assertEqual(context.get('default_employee_id'), reservation.employee_id.id)
        self.assertEqual(context.get('default_reservation_id'), reservation.id)
        view = self.env.ref('cyllo_asset_management.view_asset_assign_form2')
        self.assertEqual(action['view_id'], view.id)

    def test_action_lease_asset(self):
        """Test for action_lease_asset function"""
        reservation = self.reserved_asset
        reservation.asset_id.is_lease_asset = False
        with self.assertRaises(UserError):
            reservation.action_lease_asset()
        reservation.asset_id.is_lease_asset = True
        action = reservation.action_lease_asset()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'asset.lease')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')
        context = action.get('context', {})
        self.assertEqual(context.get('default_asset_id'), reservation.asset_id.id)
        self.assertEqual(context.get('default_customer_id'), reservation.employee_id.work_contact_id.id)
        self.assertEqual(context.get('default_reservation_id'), reservation.id)
        view = self.env.ref('cyllo_asset_management.view_asset_lease_form2')
        self.assertEqual(action['view_id'], view.id)

    def test_action_rental_asset(self):
        """Test for action_rental_asset function"""
        reservation = self.reserved_asset
        reservation.asset_id.is_rental_asset = False
        with self.assertRaises(UserError):
            reservation.action_rental_asset()
        reservation.asset_id.is_rental_asset = True
        action = reservation.action_rental_asset()
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'asset.rental')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')
        context = action.get('context', {})
        self.assertEqual(context.get('default_asset_id'), reservation.asset_id.id)
        self.assertEqual(context.get('default_customer_id'), reservation.employee_id.work_contact_id.id)
        self.assertEqual(context.get('default_reservation_id'), reservation.id)
        view = self.env.ref('cyllo_asset_management.view_asset_rental_form')
        self.assertEqual(action['view_id'], view.id)

    def test_action_unreserve(self):
        """Test for action_unreserve function"""
        reservation = self.reserved_asset
        asset = reservation.asset_id
        asset.is_reserve = True
        reservation.status = 'reserve'
        reservation.action_unreserve()
        self.assertEqual(reservation.status, 'cancel')
        self.assertFalse(asset.is_reserve)

    def test_unlink(self):
        """Test for unlink function"""
        reservation = self.reserved_asset
        asset = reservation.asset_id
        reservation.status = 'reserve'
        with self.assertRaises(UserError):
            reservation.unlink()
        reservation.status = 'cancel'
        asset.is_reserve = True
        reservation.unlink()
        self.assertFalse(asset.is_reserve)
        self.assertFalse(self.env['asset.reservation'].search([('id', '=', reservation.id)]))

    def test_action_reset_to_draft(self):
        """Test for action_reset_to_draft function"""
        reservation = self.reserved_asset
        asset = reservation.asset_id
        restricted_states = ['sell', 'disposed', 'cancel', 'lost']
        for state in restricted_states:
            asset.status = state
            with self.assertRaises(UserError):
                reservation.action_reset_to_draft()
        asset.status = 'reserved'
        reservation.status = 'reserve'
        reservation.action_reset_to_draft()
        self.assertEqual(reservation.status, 'draft')
        self.assertNotIn(asset.status, ['sell', 'disposed', 'cancel', 'lost'])
