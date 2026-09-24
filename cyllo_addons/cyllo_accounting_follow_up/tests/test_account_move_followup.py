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
from unittest.mock import patch
from datetime import date, timedelta


class TestAccountMoveFollowUp(TransactionCase):

    def setUp(self):
        super().setUp()

        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })

        self.followup_line = self.env['accounting.followup.line'].create({
            'title': 'Test Follow-Up',
            'due_date': 5,
        })

        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': date.today(),
            'invoice_date_due': date.today() - timedelta(days=5),
            'line_ids': [(0, 0, {
                'name': 'Test Line',
                'quantity': 1,
                'price_unit': 100,
                'account_id': self.env['account.account'].search(
                    [('account_type', '=', 'income')],
                    limit=1
                ).id,
            })],
        })

    def test_followup_fields_assignment(self):
        """Test next and last follow-up fields"""
        self.move.write({
            'next_follow_up_id': self.followup_line.id,
            'last_follow_up_id': self.followup_line.id,
        })

        self.assertEqual(self.move.next_follow_up_id, self.followup_line)
        self.assertEqual(self.move.last_follow_up_id, self.followup_line)

    def test_many2one_action_calls_partner_method(self):
        """Test many2one_action delegates to partner.change_followup_action"""
        with patch.object(
            type(self.partner),
            'change_followup_action'
        ) as mocked_method:
            self.move.many2one_action()
            mocked_method.assert_called_once_with(self.move)
