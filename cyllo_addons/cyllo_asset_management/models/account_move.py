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


class AccountMove(models.Model):
    """Inheriting account.move for adding new functionalities for creating the assets"""
    _inherit = 'account.move'

    asset_asset_id = fields.Many2one(
        'asset.asset',
        string='Asset'
    )
    sell_dispose_id = fields.Many2one(
        'asset.sell.dispose',
        string='Asset Sell'
    )
    asset_asset_ids = fields.Many2many(
        'asset.asset',
        string='Assets',
        copy=False
    )
    asset_asset_count = fields.Integer(
        string='Assets',
        compute='_compute_asset_asset_count',
        copy=False
    )
    lease_id = fields.Many2one(
        'asset.lease',
        copy=False
    )
    rent_id = fields.Many2one(
        'asset.rental',
        copy=False,
    )
    repair_id = fields.Many2one(
        'maintenance.request',
        index=True,
        ondelete='cascade',
        copy=False,
        domain="[('company_id', '=', company_id)]"
    )
    depreciation_line_id = fields.Many2one(
        'asset.depreciation.line'
    )

    @api.depends('asset_asset_ids')
    def _compute_asset_asset_count(self):
        """Compute assets linked to the account moves"""
        for rec in self:
            rec.asset_asset_count = len(rec.asset_asset_ids)

    def _post(self, soft=True):
        """When confirming the invoice create the asset entries"""
        post_move = super()._post(soft)
        post_move.create_account_asset_moves()
        for move in self:
            if not move.sudo().depreciation_line_id.is_depreciated:
                move.asset_asset_id.salvage_value -= move.amount_total_signed
                move.asset_asset_id.parent_id.salvage_value -= move.amount_total_signed
            depreciation_line = move.asset_asset_id.sudo().depreciation_line_ids.filtered(
                lambda d: d.id == move.depreciation_line_id.id)
            depreciation_line.write({
                'journal_reference': move.name
            })
        return post_move

    def button_draft(self):
        """Override: button_draft"""
        res = super(AccountMove, self).button_draft()
        for move in self:
            for asset in move.asset_asset_ids:
                if asset.is_depreciate:
                    raise UserError(_('You cannot reset to draft, The related asset is already posted'))
                else:
                    asset.unlink()
        return res

    def action_view_asset_moves(self):
        """action_view_asset_moves"""
        return {
            'name': 'Asset',
            'view_mode': 'tree,form',
            'res_model': 'asset.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.asset_asset_ids.ids), ('invoice_id', '=', self.id)]
        }

    def action_view_maintenace_request(self):
        """Function for viewing the maintenance request model from account move"""
        maintenace_request_id = self.env['maintenance.request'].search(
            [('id', '=', self.repair_id.id)])
        return {
            'name': _('Maintenance Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'res_id': maintenace_request_id.id,
            'view_mode': 'form',
            'domain': [('id', '=', self.repair_id.id)],
        }

    def _prepare_asset_moves(self, line, rec, depreciate_value):
        """Create Moves based on the asset values"""
        vals = {
            'name': line.name,
            'invoice_id': self.id,
            'vendor_id': self.partner_id.id if self.partner_id else False,
            'asset_item_id': line.account_id.asset_model_id.id,
            'asset_journal_id': line.account_id.asset_model_id.asset_journal_id.id,
            'fixed_asset_account_id': line.account_id.asset_model_id.fixed_asset_account_id.id,
            'asset_depreciation_account_id': line.account_id.asset_model_id.asset_depreciation_account_id.id,
            'asset_expense_account_id': line.account_id.asset_model_id.asset_expense_account_id.id,
            'asset_loss_account_id': line.account_id.asset_model_id.asset_loss_account_id.id,
            'company_id': line.company_id.id,
            'date': rec.invoice_date,
            'status': 'draft',
            'invoice_line_id': line.id,
            'brand_id': line.account_id.asset_model_id.brand_id.id,
            'original_value': depreciate_value,
            'salvage_value': depreciate_value,
            'depreciation_method': line.account_id.asset_model_id.depreciation_method,
            'method_duration': line.account_id.asset_model_id.method_duration,
            'duration_period': line.account_id.asset_model_id.duration_period,
            'computation_method': line.account_id.asset_model_id.computation_method,
            'depreciation_date': rec.invoice_date,
            'prorata_date': line.account_id.asset_model_id.prorata_date,
        }
        asset = self.env['asset.asset'].sudo().create(vals)
        rec.asset_asset_ids = [fields.Command.link(asset.id)]
        if line.account_id.asset_creation == 'validate':
            asset.action_confirm_deprecation()
        return asset

    def create_account_asset_moves(self):
        """Creates assets from the invoice lines"""
        for rec in self:
            if rec.is_invoice():
                for line in rec.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_fixed'):
                    if line.account_id.asset_creation != 'no':
                        if line.account_id.multiple_asset:
                            for qty in range(int(line.quantity)):
                                depreciate_value = line.price_unit
                                self._prepare_asset_moves(line, rec, depreciate_value)
                        else:
                            depreciate_value = line.price_subtotal
                            self._prepare_asset_moves(line, rec, depreciate_value)
