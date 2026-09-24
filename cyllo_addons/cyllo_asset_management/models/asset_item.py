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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetItem(models.Model):
    """Model for asset items"""
    _name = 'asset.item'
    _description = 'Account Item'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Assets',
        required=True,
        help='Name of the asset.'
    )
    brand_id = fields.Many2one(
        'asset.brand',
        string='Brand',
        help='Brand associated with the asset.'
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        help='Purchase or acquisition date of the asset.'
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Purchase From',
        copy=False,
        help='Vendor from whom the asset was purchased.'
    )
    depreciation_method = fields.Selection(
        [
            ('straight_line', 'Straight Line'),
            ('declining_balance', 'Declining Balance'),
            ('declining_straight_line', 'Declining and Straight Line')
        ],
        string='Method',
        required=True,
        help='Method used to calculate asset depreciation.'
    )
    automatic_maintenance = fields.Selection(
        [
            ('no', 'No Maintenance Required'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', '3 Months'),
            ('semi_annually', '6 Months'),
            ('yearly', 'Yearly'),
        ],
        string="Automatic Maintenance",
        default='no',
        help="Select frequency for automatic maintenance request generation."
    )
    is_auto_calculate = fields.Boolean(
        string='Auto Calculate',
        default=True,
        help='Automatically calculate the depreciation factor.'
    )
    depreciating_factor = fields.Float(
        default=30,
        help='Factor used for declining depreciation methods.'
    )
    method_duration = fields.Integer(
        string='Duration',
        tracking=True,
        default=1,
        help='Number of periods over which the asset is depreciated.'
    )
    duration_period = fields.Selection(
        [
            ('month', 'Month'),
            ('year', 'Year')
        ],
        tracking=True,
        default='year',
        required=True,
        help='Period unit used for depreciation duration.'
    )
    computation_method = fields.Selection(
        [
            ('no_prorata', 'No Prorata'),
            ('constant_period', 'Constant Period'),
            ('daily_compute', 'Daily Computation')
        ],
        string='Computation',
        default='no_prorata',
        tracking=True,
        required=True,
        help='Method used to compute depreciation amounts.'
    )
    prorata_date = fields.Date(
        default=fields.Date.context_today,
        help='Starting date used for prorata depreciation calculations.'
    )
    fixed_asset_account_id = fields.Many2one(
        'account.account',
        required=True,
        domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]",
        help='Account used to record the asset value.'
    )
    asset_depreciation_account_id = fields.Many2one(
        'account.account',
        string='Depreciation Asset Account',
        required=True,
        domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]",
        help='Account used to record accumulated depreciation.'
    )
    asset_expense_account_id = fields.Many2one(
        'account.account',
        required=True,
        domain="[('account_type', '=', 'expense')]",
        help='Expense account used for depreciation entries.'
    )
    asset_journal_id = fields.Many2one(
        'account.journal',
        required=True,
        domain="[('type', '=', 'general')]",
        help='Journal used for depreciation and asset accounting entries.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help='Currency used by the company.'
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help='Company associated with this asset.'
    )
    asset_loss_account_id = fields.Many2one(
        'account.account',
        required=True,
        help='Account used to record asset loss or disposal entries.'
    )
    is_quality = fields.Boolean(
        string='Quality Check',
        help='Enable to activate quality check on assets related to this asset item.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            if rec.is_quality:
                module = self.env['ir.module.module'].sudo().search([('name', '=', 'cyllo_asset_quality')], limit=1)
                if module and module.state != 'installed':
                    module.button_immediate_install()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_quality'):
            module = self.env['ir.module.module'].sudo().search([('name', '=', 'cyllo_asset_quality')], limit=1)
            if module and module.state != 'installed':
                module.button_immediate_install()
        return res

    @api.constrains('method_duration')
    def _onchange_method_duration(self):
        """Function for checking method duration"""
        if self.method_duration <= 0:
            raise UserError(_('The Duration period should be greater than 0'))

    @api.onchange('fixed_asset_account_id')
    def _onchange_fixed_asset_account_id(self):
        """Function for setting the depreciation account based on fixed asset account"""
        self.asset_depreciation_account_id=self.fixed_asset_account_id

    @api.onchange('asset_expense_account_id')
    def _onchange_asset_expense_account_id(self):
        """Function for setting the loss account based on expense account"""
        self.asset_loss_account_id=self.asset_expense_account_id
