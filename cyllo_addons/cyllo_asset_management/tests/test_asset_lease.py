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
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAssetLease(TestCommon):
    """Test for asset lease"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        asset = cls.asset
        '5000-5-6'
        asset.modified_asset_ids = asset.ids
        asset.asset_item_id.purchase_date = '3000-1-12'
        asset.status = 'sell'
        cls.asset_lease = cls.env['asset.lease'].create({
            'asset_id': asset.id,
            'start_date': '2005-1-1',
            'end_date': '2000-1-1',
            'status': 'lease',
            'lease_amount': -2,
            'customer_id': cls.partner.id
        })

    def test_onchange_lease_amount(self):
        """Test for _onchange_lease_amount function"""
        self.asset_lease._onchange_lease_amount()
        self.assertEqual(self.asset_lease.lease_amount, abs(self.asset_lease.lease_amount))

    def test_onchange_lease_date(self):
        """Test for _onchange_lease_date function"""
        with self.assertRaises(UserError):
            self.asset_lease._onchange_lease_date()
        self.asset_lease.start_date = '2005-1-1'
        with self.assertRaises(UserError):
            self.asset_lease._onchange_lease_date()

    def test_action_create_lease(self):
        """Test for _onchange_lease_date function"""
        with self.assertRaises(UserError):
            self.asset_lease.action_create_lease()
        self.asset_lease.asset_id.is_lease_asset = True
        self.asset_lease.asset_id.is_lease = True
        with self.assertRaises(UserError):
            self.asset_lease.action_create_lease()
        self.asset_lease.asset_id.is_lease = False

    def test_action_view_invoice(self):
        """test for action_view_invoice function"""
        self.account_move.ref = self.asset_lease.asset_id.name
        self.account_move.lease_id = self.asset_lease.id
        self.assertEqual(self.asset_lease.action_view_invoice(), {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_id': self.env['account.move'].search(
                [('ref', '=', self.asset_lease.asset_id.name), ('lease_id', '=', self.asset_lease.id)]).id,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        })

    def test_action_return_asset(self):
        """test for action_return_asset function"""
        self.account_move.lease_id = self.asset_lease.id
        with self.assertRaises(UserError):
            self.asset_lease.action_return_asset()
        self.account_move.lease_id = False
        self.asset_lease.action_return_asset()
        self.assertEqual(self.asset_lease.is_return, True)
        self.assertEqual(self.asset_lease.status, 'cancel')
        self.assertEqual(self.asset_lease.asset_id.is_lease, False)
        self.asset_lease.reservation_id = self.reserved_asset.id
        self.asset_lease.action_return_asset()
        self.assertEqual(self.asset_lease.asset_id.is_reserve, False)
        self.assertEqual(self.asset_lease.reservation_id.status, 'cancel')

    def test_action_reset_to_draft(self):
        """test for action_reset_to_draft function"""
        with self.assertRaises(UserError):
            self.asset_lease.action_reset_to_draft()
        self.asset_lease.asset_id.status = 'draft'
        self.asset_lease.action_reset_to_draft()
        self.assertEqual(self.asset_lease.status, 'draft')

    def test_unlink(self):
        """test for unlink function"""
        with self.assertRaises(UserError):
            self.asset_lease.unlink()
        self.asset_lease.status = 'return'

    def test_send_lease_asset_return_reminder_mail(self):
        """test for _send_lease_asset_return_reminder_mail function"""
        self.asset_lease.customer_id.email = 'testcustomer@gmail.com'
        self.asset_lease.end_date = fields.Date.today() + relativedelta(days=3)
        self.asset_lease._send_lease_asset_return_reminder_mail()
        lease_mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertNotEqual(lease_mail.state, 'outgoing')
        self.assertEqual(lease_mail.email_to, self.asset_lease.customer_id.email, 'testcustomer@gmail.com')
