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
from odoo import fields, models


class AssetLost(models.TransientModel):
    """Model for asset modify"""
    _name = 'asset.modify'
    _description = 'Modify the Asset'

    asset_asset_id = fields.Many2one(
        'asset.asset',
        help='Asset selected for modification or revaluation.'
    )
    depreciation_method = fields.Selection(
        [
            ('straight_line', 'Straight Line'),
            ('declining_balance', 'Declining Balance'),
            ('declining_straight_line', 'Declining and Straight Line')
        ],
        string='Method',
        required=True,
        help='Depreciation method to be applied for the modified asset.'
    )
    depreciation_date = fields.Date(
        required=True,
        help='Date from which depreciation will be recalculated.'
    )
    method_duration = fields.Integer(
        string="Duration",
        tracking=True,
        default=1,
        required=True,
        help='Number of periods over which the asset will be depreciated.'
    )
    duration_period = fields.Selection(
        [('month', 'Month'), ('year', 'Year')],
        tracking=True,
        required=True,
        help='Time unit used for the depreciation duration.'
    )
    salvage_value = fields.Float(
        required=True,
        string='Depreciatable value',
        help='Amount to be depreciated after asset modification.'
    )
    fixed_asset_account_id = fields.Many2one(
        'account.account',
        domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]",
        required=True,
        help='Asset account used for recording the modified asset value.'
    )
    asset_depreciation_account_id = fields.Many2one(
        'account.account',
        string='Depreciation Asset Account',
        domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]",
        required=True,
        help='Accumulated depreciation account used for depreciation entries.'
    )
    asset_expense_account_id = fields.Many2one(
        'account.account',
        domain="[('account_type', '=', 'expense')]",
        required=True,
        help='Expense account used to record depreciation expenses.'
    )
    asset_journal_id = fields.Many2one(
        'account.journal',
        required=True,
        help='Journal used for creating depreciation accounting entries.'
    )
    reference_note = fields.Char(
        required=True,
        string="Reference",
        help='Reference note describing the reason for asset modification or revaluation.'
    )
    def action_revaluate(self):
        """Button action for revaluate the assets"""
        vals = {
            'asset_journal_id': self.asset_journal_id.id,
            'fixed_asset_account_id': self.fixed_asset_account_id.id,
            'asset_depreciation_account_id': self.asset_depreciation_account_id.id,
            'asset_expense_account_id': self.asset_expense_account_id.id,
            'salvage_value': self.salvage_value,
            'depreciation_method': self.depreciation_method,
            'duration_period': self.duration_period,
            'method_duration': self.method_duration,
            'depreciation_date': self.depreciation_date,
            'reference_note': self.reference_note
        }
        self.asset_asset_id.sudo().write(vals)
        self.asset_asset_id.action_revaluate_asset()
