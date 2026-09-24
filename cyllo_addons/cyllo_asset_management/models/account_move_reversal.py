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
from odoo import models


class AccountMoveReversal(models.TransientModel):
    """Inherit the model for updating the salvage based on the reversed entries"""
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        """Override to update the salvage value of assets when moves are reversed."""
        res = super().reverse_moves(is_modify)
        for rec in self.move_ids:
            if rec.asset_asset_id:
                rec.asset_asset_id.salvage_value += rec.amount_total_signed
        return res
