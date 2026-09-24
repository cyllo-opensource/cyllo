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
from odoo.exceptions import RedirectWarning, UserError


class AccountMoveLock(models.TransientModel):
    """Wizard for locking account dates"""
    _name = 'account.move.lock'
    _description = 'Account Move Lock'

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)
    # lock dates
    sale_lock_date = fields.Date(string='Lock Sales')
    purchase_lock_date = fields.Date(string='Lock Purchase')
    tax_lock_date = fields.Date(string='Lock Tax Return')
    all_lock_date = fields.Date(string='Lock All Journal Entries')
    has_draft_entries = fields.Boolean(compute='_compute_has_draft_entries')
    # for closing fiscal year
    fiscal_year_id = fields.Many2one('account.fiscal.year')
    is_entire_fiscal_year_close = fields.Boolean()

    @api.model
    def default_get(self, fields_list):
        """Load values from current company."""
        res = super().default_get(fields_list)
        company = self.env.company
        res.update({
            'company_id': company.id,
            'sale_lock_date': company.sale_lock_date,
            'purchase_lock_date': company.purchase_lock_date,
            'tax_lock_date': company.tax_lock_date,
            'all_lock_date': company.all_lock_date,
        })
        return res

    @api.depends('sale_lock_date', 'purchase_lock_date', 'tax_lock_date', 'all_lock_date')
    def _compute_has_draft_entries(self):
        """Compute if there are draft entries within the selected periods"""
        self.has_draft_entries = False
        dates = [self.sale_lock_date, self.purchase_lock_date, self.tax_lock_date, self.all_lock_date]
        valid_dates = [d for d in dates if d]
        if valid_dates:
            draft_entries = self.env['account.move'].search(
                [('state', '=', 'draft'), ('date', '<=', max(valid_dates))])
            self.has_draft_entries = True if draft_entries else False

    def action_open_draft_entries(self):
        """opens draft entries from wizard"""
        all_lock_date = self.all_lock_date or self.fiscal_year_id.end_date or False
        dates = [self.sale_lock_date, self.purchase_lock_date, self.tax_lock_date, all_lock_date]
        valid_dates = [d for d in dates if d]
        check_date = max(valid_dates) if valid_dates else fields.Date.today()
        return {
            'name': _('Draft Entries'),
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('state', '=', 'draft'), ('date', '<=', check_date)],
            'views': [(False, 'list'), (False, 'form')],
        }

    def action_close(self):
        """Close entire fiscal year"""
        if self.fiscal_year_id.end_date:
            self.write({
                'is_entire_fiscal_year_close': True,
                'all_lock_date': self.fiscal_year_id.end_date
            })
            self.action_save()

    def action_save(self):
        """Save values to company and check for validation cases."""
        all_lock_date = self.all_lock_date or self.fiscal_year_id.end_date or False
        if all_lock_date:
            unreconciled_bank_lines = self.env['account.bank.statement.line'].search(
                [('is_reconciled', '=', False), ('date', '<=', all_lock_date)])

            if unreconciled_bank_lines:
                action = {
                    'name': _('Reconcile page'),
                    'res_model': 'account.bank.statement.line',
                    'type': 'ir.actions.act_window',
                    'views': [
                        (self.env.ref(
                            'cyllo_accounting.view_account_bank_statement_line_reconcile').id,
                         'reconcile'),
                        (self.env.ref('cyllo_accounting.view_account_bank_statement_line_tree').id,
                         'list')
                    ],
                    'domain': [('id', 'in', unreconciled_bank_lines.ids)],
                    'context': {
                        'search_default_not_matched': 1,
                        'search_default_journal_id': unreconciled_bank_lines[0].journal_id.id,
                        'active_id': unreconciled_bank_lines[0].journal_id.id,
                    }
                }
                raise RedirectWarning(
                    message=(_(
                        'There are still unreconciled bank statement lines in the period '
                        'you want to lock.You should either reconcile or delete them.')),
                    action=action,
                    button_text=_("Reconciliation Page"),
                )
        if self.tax_lock_date and self.tax_lock_date > fields.Date.context_today(self):
            raise UserError(_('You cannot set a lock date in the future.'))

        self.company_id.sudo().write({
            'sale_lock_date': self.sale_lock_date,
            'purchase_lock_date': self.purchase_lock_date,
            'tax_lock_date': self.tax_lock_date,
            'all_lock_date': all_lock_date,
        })
        if self.fiscal_year_id and (
                self.is_entire_fiscal_year_close or (
                all_lock_date and self.fiscal_year_id.end_date == all_lock_date)) :
            self.is_entire_fiscal_year_close = False
            self.fiscal_year_id.write({
                'state': 'close'
            })
            self.company_id.sudo().write({
                'all_lock_date': False,
            })
        return {'type': 'ir.actions.act_window_close'}
