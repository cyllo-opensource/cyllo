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
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    """Inheriting account.move for adding new functionalities"""
    _inherit = 'account.move'

    # -------------------- Assets --------------------------------
    residual_amount = fields.Monetary(string='Residual', help='For changing the amount residual')
    asset_id = fields.Many2one('account.asset.asset', index=True, ondelete='cascade',
                               copy=False, domain="[('company_id', '=', company_id)]",
                               help="Asset of the journal")
    asset_date = fields.Date(string="Asset Date", help="Asset date of the journal")
    asset_end_date = fields.Date('End Date', help="End Date of Asset")
    total_residual = fields.Float(compute='_compute_total_residual', store=True)
    asset_amount = fields.Float(help="Asset amount of the move")
    asset_residual_amount = fields.Float(string='Asset Residual Amount',
                                         compute='_compute_total_residual', store=True)
    asset_count = fields.Integer(string='Asset Moves', compute='_compute_asset_count')
    set_asset_move = fields.Boolean()
    check_increment = fields.Boolean('Check Increment move', default=False)
    asset_ids = fields.One2many('account.asset.asset', string='Assets',
                                compute="_compute_asset_count")
    asset_type = fields.Char(compute="_compute_asset_count")
    asset_days = fields.Integer(copy=False)
    # -------------------- Multi Payments --------------------------------
    create_from_payment = fields.Boolean('Create Move From Payment', default=False)
    fiscal_year_id = fields.Many2one('account.fiscal.year', tracking=True,
                                     compute='_compute_fiscal_year_id',
                                     help='The invoice date within the fiscal year')

    @api.depends('asset_id', 'asset_id.residual_value', 'asset_id.cum_residual_amount')
    def _compute_total_residual(self):
        """Calculate Asset Amounts"""
        for rec in self:
            rec.total_residual = 0
            rec.asset_residual_amount = 0
            depreciated = 0
            remaining = rec.asset_id.total_value - rec.asset_id.not_depreciable_value + rec.asset_id.gross_value
            for move in rec.asset_id.depreciation_move_ids.sorted(
                    lambda x: (x.asset_date, x._origin.id)):
                remaining -= move.asset_amount
                depreciated += move.asset_amount
                move.asset_residual_amount = depreciated
                move.total_residual = remaining

    @api.depends('line_ids.asset_ids')
    def _compute_asset_count(self):
        """Compute assets linked to the move"""
        for record in self:
            record.asset_ids = record.line_ids.asset_ids
            record.asset_count = len(record.asset_ids)
            record.asset_type = record.asset_ids[:1].asset_type

    def _compute_fiscal_year_id(self):
        """Compute fiscal year based on invoice date"""
        for rec in self:
            if rec.date:
                rec.fiscal_year_id = False
                fiscal_year_id = self.env['account.fiscal.year'].sudo().with_context(
                    company_id=rec.company_id.id).search(
                    [('start_date', '<=', rec.date),
                     ('end_date', '>=', rec.date),
                     ('company_id', '=', rec.company_id.id)], limit=1)
                if fiscal_year_id:
                    rec.fiscal_year_id = fiscal_year_id

    @api.onchange('amount_residual', 'payment_state')
    def _onchange_amount_residual(self):
        """Assign amount_residual to residual_amount for multi invoice payments"""
        for rec in self.filtered(lambda x: x.amount_residual):
            rec.residual_amount = rec.amount_residual

    def action_get_asset_moves(self):
        """Smart button for the asset revenues/expenses"""
        if self.move_type == 'out_invoice':
            return {
                'name': _("Deferred Revenues"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.asset.asset',
                'view_mode': 'tree,form',
                'target': 'current',
                'views': [(self.env.ref(
                    'cyllo_accounting.view_account_asset_asset_deferred_revenue_tree').id, 'tree'),
                          (self.env.ref(
                              'cyllo_accounting.view_account_asset_asset_deferred_revenue_form').id,
                           'form')],
                'domain': [('id', 'in', self.asset_ids.ids), ('asset_type', '=', 'revenue')],
                'context': {'default_asset_type': 'revenue', 'create': False},
            }
        elif self.move_type == 'in_invoice':
            return {
                'name': _("Deferred Expenses"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.asset.asset',
                'view_mode': 'tree,form',
                'target': 'current',
                'views': [(self.env.ref(
                    'cyllo_accounting.view_account_asset_asset_deferred_expense_tree').id, 'tree'),
                          (self.env.ref(
                              'cyllo_accounting.view_account_asset_asset_deferred_expense_form').id,
                           'form')],
                'domain': [('id', 'in', self.asset_ids.ids), ('asset_type', '=', 'expense')],
                'context': {'default_asset_type': 'expense', 'create': False}
            }
        return None

    def action_open_business_doc(self):
        """Override to handle reconciled transactions differently.
        For reconciled bank statement lines, open the reconcile view with proper domain.
        For other transactions, use the default form view behavior.
        """
        self.ensure_one()

        statement_lines = self.env['account.bank.statement.line'].search([
            ('move_id', '=', self.id)
        ])

        reconciled_st_lines = statement_lines.filtered(lambda x: x.is_reconciled)

        if reconciled_st_lines:
            action = {
                'name': _('Reconciliation'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.statement.line',
                'view_mode': 'reconcile',
                'views': [(False, 'reconcile')],
                'target': 'current',
                'context': {'create': False},
                'domain': [('id', 'in', reconciled_st_lines.ids)],
            }
            return action

        return super(AccountMove, self).action_open_business_doc()

    def create_asset_moves(self):
        """Creates deferred revenue or expense from invoice lines"""
        for line in self.filtered(lambda x: x.is_invoice()).line_ids:
            if line.asset and line.account_id and line.price_total > 0 and not line.asset_ids:
                if not line.name:
                    raise UserError(
                        _('There is no label in the journal items of {account}').format(
                            account=line.account_id.display_name))

                journal_id = self.env['account.journal'].search(
                    [('type', '=', 'general'), ('company_id', '=', line.company_id.id)], limit=1)
                if line.move_id.move_type == 'out_invoice':
                    account_id = self.env['account.account'].search(
                        [('account_type', '=', 'liability_current'),
                         ('company_id', '=', line.company_id.id)], limit=1)
                else:
                    account_id = self.env['account.account'].search(
                        [('account_type', 'in', ('asset_current', 'asset_prepayments')),
                         ('company_id', '=', line.company_id.id)], limit=1)
                self.env['account.asset.asset'].create({
                    'name': line.name,
                    'asset_type_id': line.asset_type_id.id if line.asset_type_id else False,
                    'journal_id': line.asset_type_id.journal_id.id if line.asset_type_id else journal_id.id,
                    'account_id': line.asset_type_id.account_id.id if line.asset_type_id else account_id.id,
                    'expense_account_id': line.asset_type_id.expense_account_id.id
                    if line.asset_type_id else line.account_id.id,
                    'company_id': line.company_id.id,
                    'date': line.move_id.invoice_date,
                    'first_recognition_date': line.move_id.invoice_date,
                    'state': 'draft',
                    'invoice_line_ids': [fields.Command.set(line.ids)],
                    'asset_type': 'revenue' if line.move_id.move_type == 'out_invoice' else 'expense',
                    'original_value': line.price_subtotal,
                    'total_value': line.price_subtotal,
                    'number_of_entries': line.asset_type_id.number_of_entries if line.asset_type_id else 6,
                    'period': line.asset_type_id.period if line.asset_type_id else '1',
                    'computation_method': line.asset_type_id.computation_method if line.asset_type_id else 'no_prorata',
                    'prorata_date': line.move_id.invoice_date
                    if line.asset_type_id and line.asset_type_id.computation_method != 'no_prorata' else False,
                })

    def button_cancel(self):
        """Override: For cancel the assets """
        res = super(AccountMove, self).button_cancel()
        self.env['account.asset.asset'].sudo().search(
            [('invoice_line_ids.move_id', 'in', self.ids)]).write(
            {'active': False})
        return res

    def button_draft(self):
        """Override: button_draft"""
        res = super(AccountMove, self).button_draft()
        for move in self:
            for asset in move.asset_ids:
                if asset.state != 'draft':
                    raise UserError(
                        _('You cannot reset to draft, The related asset is already posted'))
                else:
                    asset.unlink()
        return res

    def _post(self, soft=True):
        """When confirming the invoice create asset"""
        posted_moves = super()._post(soft)
        posted_moves.create_asset_moves()
        return posted_moves

    @api.model
    def _get_invoice_in_payment_state(self):
        ''' Overriding function so that when Cyllo accounting module in_payment
        state in enabled. '''
        return 'in_payment'

    def _check_fiscalyear_lock_date(self):
        """Check the date is within an open fiscal year and not in a lock date"""
        res = super(AccountMove, self)._check_fiscalyear_lock_date()
        if res:
            for rec in self:
                fiscal_year_id = rec.fiscal_year_id
                company_id = self.env.company
                if not fiscal_year_id:
                    if self.env.user.has_group('account.group_account_manager'):
                        action = self.env.ref(
                            'cyllo_accounting.action_view_fiscal_years')
                        raise RedirectWarning(
                            message=(_(
                                'The Date %s Must Be Within a Fiscal Year'
                            ) % rec.date),
                            action=action.id,
                            button_text=_("Create Fiscal Year"),
                        )
                    else:
                        raise ValidationError(_(
                            'The Date %s Must Be Within a Fiscal Year,'
                            ' Contact Billing Administrator for Creating Fiscal Years') % rec.date)
                elif fiscal_year_id.state == 'open':
                    if company_id.all_lock_date and rec.date <= company_id.all_lock_date:
                        raise ValidationError(_(
                            'You cannot add/modify entries prior '
                            'to and inclusive of: Lock Date %s.') % company_id.all_lock_date)
                    else:
                        if company_id.sale_lock_date and rec.move_type == 'out_invoice' and rec.date <= company_id.sale_lock_date:
                            raise ValidationError(_(
                                'You cannot add/modify entries prior to and '
                                'inclusive of: Sale Lock Date %s.') % company_id.sale_lock_date)
                        elif company_id.purchase_lock_date and rec.move_type == 'in_invoice' and rec.date <= company_id.purchase_lock_date:
                            raise ValidationError(_(
                                'You cannot add/modify entries prior to and '
                                'inclusive of: Purchase Lock Date %s.') % company_id.purchase_lock_date)
                        else:
                            return res
                elif fiscal_year_id.state == 'close':
                    raise ValidationError(
                        _('Fiscal Year is Closed'))
                else:
                    raise ValidationError(
                        _('First Open the Fiscal Year'))
        else:
            return res

    def _prepare_moves(self, vals):
        """Create Moves based on the asset values"""
        asset_id = vals['asset_id']
        current_currency = asset_id.currency_id
        date = vals.get('date', fields.Date.context_today(self))
        amount_currency = vals['amount']
        company_currency_id = asset_id.company_id.currency_id
        dec_place = company_currency_id.decimal_places
        amount = current_currency._convert(amount_currency, company_currency_id,
                                           asset_id.company_id, date)
        return {
            'date': vals['asset_date'],
            'journal_id': asset_id.journal_id.id,
            'line_ids': [fields.Command.create({
                'name': asset_id.name,
                'account_id': asset_id.account_id.id,
                'credit': 0.0 if float_compare(amount, 0.0,
                                               precision_digits=dec_place) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0,
                                                 precision_digits=dec_place) > 0 else 0.0,
                'currency_id': current_currency.id,
                'amount_currency': amount_currency,
            }), fields.Command.create({
                'name': asset_id.name,
                'account_id': asset_id.expense_account_id.id,
                'debit': 0.0 if float_compare(amount, 0.0,
                                              precision_digits=dec_place) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0,
                                                  precision_digits=dec_place) > 0 else 0.0,
                'currency_id': current_currency.id,
                'amount_currency': -amount_currency,
            })],
            'asset_id': vals['asset_id'].id,
            'ref': _("%s: Depreciation", asset_id.name),
            'asset_date': vals['asset_date'],
            'asset_end_date': vals['asset_end_date'],
            'asset_days': vals['asset_days'],
            'asset_amount': abs(vals['amount']),
            'name': '/',
            'move_type': 'entry',
            'invoice_date_due': vals['asset_date'],
            'currency_id': current_currency.id,
            'check_increment': True if 'check_increment' in vals and vals[
                'check_increment'] else False,
        }

    def get_reconciled_statement_line_ids(self):
        """Get the IDs of bank statement lines reconciled with this move.
        This method is called from JavaScript to get the correct domain for
        opening the reconcile view.

        :return: List of statement line IDs
        """
        self.ensure_one()

        # Get all statement lines from reconciled move lines
        reconciled_st_lines = self.line_ids.mapped('matched_debit_ids.debit_move_id.statement_line_id') | \
                              self.line_ids.mapped('matched_credit_ids.credit_move_id.statement_line_id')

        return reconciled_st_lines.ids
