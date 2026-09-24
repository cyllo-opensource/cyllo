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
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAssetRental(TestCommon):
    """Test class for asset rental"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.partner.email = 'test_email2@gmail.com'

    def test_onchange_lease_date(self):
        """Test for _onchange_lease_date function"""
        self.asset_rental.start_date = '6511-5-10'
        with self.assertRaises(UserError):
            self.asset_rental._onchange_lease_date()
        self.asset_rental.start_date = '4000-5-2'
        with self.assertRaises(UserError):
            self.asset_rental._onchange_lease_date()

    def test_compute_invoice_count(self):
        """Test for _compute_invoice_count function"""
        self.asset_rental._compute_invoice_count()
        self.assertEqual(self.asset_rental.invoice_count, self.env['account.move'].search_count(
            [('rent_id', '=', self.asset_rental.id), ('ref', '=', self.asset_rental.asset_id.name)]))

    def test_action_create_rental(self):
        """Test for action_create_rental function"""
        with self.assertRaises(UserError):
            self.asset_rental.action_create_rental()
        self.asset_rental.asset_id.is_rental_asset = True

    def test_action_view_invoice(self):
        """Test for action_view_invoice function"""
        self.assertEqual(self.asset_rental.action_view_invoice(), {
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.asset_rental.asset_id.name), ('rent_id', '=', self.asset_rental.id)]
        })
        
    def test_action_return_asset(self):
        """Test for action_return_asset function"""
        move = self.env['account.move'].create({'rent_id': self.asset_rental.id, 'payment_state': 'paid'})
        with self.assertRaises(UserError):
            self.asset_rental.action_return_asset()
        move.unlink()
        self.asset_rental.reservation_id = self.reserved_asset.id
        self.asset_rental.action_return_asset()
        self.assertEqual(self.asset_rental.is_return, True)
        self.assertEqual(self.asset_rental.status, 'return')
        self.assertEqual(self.asset_rental.asset_id.is_rental, False)
        self.assertEqual(self.asset_rental.asset_id.is_reserve, False)
        self.assertEqual(self.asset_rental.reservation_id.status, 'cancel')

    def test_unlink(self):
        """Test for unlink function"""
        with self.assertRaises(UserError):
            self.asset_rental.unlink()
        self.asset_rental.status = 'return'
        self.asset_rental.unlink()

    def test_action_cancel(self):
        """Test for action_cancel function"""
        self.asset_rental.action_cancel()
        self.assertEqual(self.asset_rental.status, 'cancel')
        self.assertEqual(self.asset_rental.asset_id.is_rental, False)

    def test_action_reset_to_draft(self):
        """Test for action_reset_to_draft function"""
        asset_rental = self.asset_rental
        asset_rental.asset_id.status = 'sell'
        with self.assertRaises(UserError):
            asset_rental.action_reset_to_draft()
        asset_rental.asset_id.status = 'draft'
        asset_rental.action_reset_to_draft()
        self.assertEqual(asset_rental.status, 'draft')
        self.assertEqual(asset_rental.is_return, False)
        self.assertEqual(asset_rental.is_invoice, False)
        self.account_move.rent_id = asset_rental.id
        self.account_move.fiscal_year_id.state = 'open'
        self.account_move.state = 'cancel'
        self.account_move.button_draft()
        self.env['account.move'].search([('rent_id', '=', asset_rental.id)]).action_post()
        with self.assertRaises(UserError):
            asset_rental.action_reset_to_draft()

    def test_send_asset_rental_invoice_reminder_mail(self):
        """test for _send_asset_rental_invoice_reminder_mail function"""
        move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'rent_id': self.asset_rental.id,
            'state': 'draft',
            'invoice_date_due': fields.Date.today() + relativedelta(days=3),
        })
        with patch("odoo.addons.mail.models.mail_template.MailTemplate.send_mail") as mock_send_mail:
            self.asset_rental._send_asset_rental_invoice_reminder_mail()
            mock_send_mail.assert_called_once()
            args, kwargs = mock_send_mail.call_args
            self.assertEqual(kwargs.get('res_id'), move.id)
            self.assertEqual(kwargs.get('email_values', {}).get('email_to'),'test_email2@gmail.com')
            self.assertTrue(kwargs.get("force_send"))

