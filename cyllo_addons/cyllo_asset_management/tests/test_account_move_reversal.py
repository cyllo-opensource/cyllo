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
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAccountMoveReversal(TestCommon):
    
    def test_reverse_moves(self):
        """Test for reverse_moves"""
        self.asset_journal_id.type = 'sale'
        self.account_move.journal_id = self.asset_journal_id.id
        reversal_wizard = self.env['account.move.reversal'].create({
            'move_ids': self.account_move.ids,
            'journal_id': self.asset_journal_id.id,
        })
        first_sal_value = self.account_move.asset_asset_id.salvage_value
        self.account_move.amount_total_signed = 2
        reversal_wizard.reverse_moves()
        self.assertEqual(self.account_move.asset_asset_id.salvage_value, first_sal_value+2)

