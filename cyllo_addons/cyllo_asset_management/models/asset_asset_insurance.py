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


class AssetAssetInsurance(models.Model):
    """Model for creating the assets insurance providers"""
    _name = 'asset.asset.insurance'
    _description = 'Asset Insurance'
    _rec_name = 'name'

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one('res.partner', string="Insurance Provider")
    type_id = fields.Many2one(string="Type", comodel_name='asset.insurance.type')
    account_move_count = fields.Integer(string='Invoice', copy=False, compute='_compute_transaction_count')
    asset_count = fields.Integer(string='Invoice', copy=False, compute='_compute_asset_count')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 help='Select the company')

    @api.depends('partner_id', 'type_id')
    def _compute_name(self):
        """function for assigning the name of insurance based on provider and type"""
        for record in self:
            if record.partner_id and record.type_id:
                record.name = f"{record.partner_id.name} ({record.type_id.type})"
            else:
                record.name = False

    def _compute_asset_count(self):
        """Function for computing the asset count"""
        self.asset_count = self.env['asset.asset'].search_count([('insurance_name_id', '=', self.id)])

    def _compute_transaction_count(self):
        """Function for computing the account move count"""
        asset_ids = self.env['asset.asset'].search([('insurance_name_id', '=', self.id)]).ids
        self.account_move_count = self.env['account.move'].search_count([('repair_id.asset_id', 'in', asset_ids)])

    def action_view_assets(self):
        """Function for viewing the insurance linked assets"""
        return {
            'name': _('Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'view_mode': 'tree,form',
            'domain': [('insurance_name_id', '=', self.id)],
        }

    def action_view_moves(self):
        """Function for viewing the invoice"""
        asset_ids = self.env['asset.asset'].search([('insurance_name_id', '=', self.id)]).ids
        return {
            'name': _('Claims'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('asset_id', 'in', asset_ids),
                ('repair_id.asset_id', 'in', asset_ids),
                ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ],
            'search_view_id': self.env.ref('cyllo_asset_management.view_account_move_search_claim_only').id,
            'context': {
                'search_default_insurance_claim': 1
            },
        }
