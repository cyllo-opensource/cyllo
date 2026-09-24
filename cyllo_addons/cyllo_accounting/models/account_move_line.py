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
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    """Extends the 'account.move.line' model by adding new functionalities and
    includes the 'annotation.mixin' for additional features."""
    _name = 'account.move.line'
    _description = 'Account Move Line'
    _inherit = ['account.move.line', 'annotation.mixin']

    multi_invoice_payment = fields.Boolean(default=False)
    # Enable boolean field to create deferred revenue or expense based on move lines
    asset = fields.Boolean('Deferred revenue/expense', default=False,
                           help="create deferred revenue/expense based on the move")
    # From the lines user can give corresponding deferred revenue or expense type, it is optional
    asset_type_id = fields.Many2one('account.asset.type', string='Deferred revenue/expense type',
                                    help='Select Asset Type')
    asset_ids = fields.Many2many('account.asset.asset', 'asset_invoice_line_rel', 'line_id',
                                 'asset_id', string='Assets', copy=False)
    move_asset_type = fields.Selection([('revenue', 'Deferred Revenue'), ('expense', 'Deferred Expense')],
                                       compute='_compute_move_asset_type', store=True, index=True, copy=True)

    @api.depends('move_type')
    def _compute_move_asset_type(self):
        """Find the value of the field move_asset_type"""
        for rec in self:
            rec.move_asset_type = False
            if rec.move_type == 'out_invoice':
                rec.move_asset_type = 'revenue'
            elif rec.move_type == 'in_invoice':
                rec.move_asset_type = 'expense'

    @api.model
    def get_js_list_view(self):
        view = self.env.ref("cyllo_accounting.view_account_move_line_tree")
        return view.id if view else False

    def reconcile(self):
        result = super().reconcile()
        self.move_id._compute_payment_state()
        return result

    @api.model
    def _prepare_reconciliation_amls(self, values_list, shadowed_aml_values=None):
        """Super this function to prepare partials in case of multi invoice
         payment"""
        if 'multi_inv_payment' in self.env.context and self.env.context.get(
                'multi_inv_payment'):
            org_list = []
            pay_val = self.env['account.move.line']
            debits = []
            credits_list = []
            amount_sign = 0
            payment_line = False
            for val in values_list:
                if val['aml'].multi_invoice_payment:
                    pay_val = val['aml']
                    if pay_val.amount_residual >= 0:
                        amount_sign = 1
                    else:
                        amount_sign = -1
            for val in values_list:
                if not val['aml'].multi_invoice_payment:
                    org_list.append({
                        'aml': val['aml'],
                        'amount_residual': val['amount_residual'],
                        'amount_residual_currency': val['amount_residual_currency'],
                    })
                    if self.payment_id:
                        payment_line = self.env['account.payment.line'].search([
                            ('move_id', '=', val['aml'].move_id.id), ('payment_id', '=', self.payment_id.id)], limit=1)
                    if amount_sign == -1:
                        total_residual = val['aml'].move_id.residual_amount \
                            if val['aml'].move_id.residual_amount <= val['amount_residual'] \
                            else val['amount_residual']
                        total_residual_currency = val['aml'].move_id.residual_amount \
                            if val['aml'].move_id.residual_amount <= val['amount_residual_currency'] \
                            else val['amount_residual_currency']
                        if payment_line:
                            payment_line.paid_amount = total_residual
                        org_list.append({'aml': pay_val, 'amount_residual': amount_sign * total_residual,
                                         'amount_residual_currency': amount_sign * total_residual_currency,
                                         } if pay_val else False)
                    else:
                        total_residual = val['aml'].move_id.residual_amount \
                            if val['aml'].move_id.residual_amount > val['amount_residual'] else val['amount_residual']
                        total_residual_currency = val['aml'].move_id.residual_amount \
                            if val['aml'].move_id.residual_amount > val['amount_residual_currency'] \
                            else val['amount_residual_currency']
                        if payment_line:
                            payment_line.paid_amount = total_residual
                        org_list.append({'aml': pay_val, 'amount_residual': amount_sign * total_residual,
                                         'amount_residual_currency': amount_sign * total_residual_currency
                                         } if pay_val else False)
            for x in org_list:
                if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) > 0.0 or x[
                    'aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) > 0.0:
                    debits.append(x)
                if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) < 0.0 or x[
                    'aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) < 0.0:
                    credits_list.append(x)
            fully_reconciled_aml_ids = set()
            all_results = []
            i = 0
            while i < len(debits):
                debit_values = debits[i]
                if not debit_values:
                    break
                # Move to the next available credit line.
                credit_values = credits_list[i]
                if not credit_values:
                    break
                # Compute the amounts to reconcile
                results = self._prepare_reconciliation_single_partial(debit_values, credit_values,
                                                                      shadowed_aml_values=shadowed_aml_values)
                if results.get('partial_values'):
                    all_results.append(results)
                if results['debit_values'] is None:
                    fully_reconciled_aml_ids.add(debit_values['aml'].id)
                if results['credit_values'] is None:
                    fully_reconciled_aml_ids.add(credit_values['aml'].id)
                i = i + 1
            return all_results, fully_reconciled_aml_ids
        else:
            res = super(AccountMoveLine, self)._prepare_reconciliation_amls(values_list, shadowed_aml_values=None)
            return res

