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
import calendar
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.date_utils import end_of

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class AccountAssetAsset(models.Model):
    """ For Creating deferred revenue or deferred expense.
    If the asset_type is revenue then this considered as deferred revenue.
    If the asset_type is expense then this considered as deferred expense"""
    _name = "account.asset.asset"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Account Asset"

    name = fields.Char(string='Asset name', required=True, tracking=True, help="Name of the asset")
    active = fields.Boolean(default=True, help="Whether this asset is active")
    # asset_type_id is deferred revenue type or deferred expense type, this can be created from the configuration.
    asset_type_id = fields.Many2one('account.asset.type', help='Select Asset Type')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    # asset_type decides it is deferred revenue or deferred expense
    asset_type = fields.Selection([('revenue', 'Deferred Revenue'), ('expense', 'Deferred Expense')],
                                  compute='_compute_asset_type', store=True, index=True, copy=True, string='Asset Category')
    journal_id = fields.Many2one('account.journal', required=True, help="Journal for this type",
                                 domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    # account_id is account for deferred revenue or expense. domain will be takes from the corresponding view
    account_id = fields.Many2one('account.account', required=True, domain="[('company_id', '=', company_id)]")
    # expense_account_id is account for recognizing the revenue or expense. Domain will be takes from the
    # corresponding view
    expense_account_id = fields.Many2one('account.account', string='Expense Account', required=True,
                                         domain="[('company_id', '=', company_id)]")
    number_of_entries = fields.Integer(string='Duration', default=6, required=True, help="The number of entries")
    period = fields.Selection([('1', 'Months'), ('12', 'Years')], default='1', required=True,
                              help="The time between the entries")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)
    date = fields.Date(default=fields.Date.context_today)
    first_recognition_date = fields.Date(required=True, default=fields.Date.context_today)
    # The value that enter from the form is the original value.
    original_value = fields.Float(compute='_compute_original_value', store=True)
    # It is the total value for depreciation and it calculated from the code.
    total_value = fields.Float(string='Total depreciable Value', copy=False)
    not_depreciable_value = fields.Float(copy=False)
    # It is the residual value for depreciation
    residual_value = fields.Float(compute='_compute_residual_value', store=True, copy=False, index=True)
    total_modify_value = fields.Float(compute='_compute_total_modify_value', store=True,
                                      help="Original Value-Not Depreciable Value+Gross Increase Value")
    # gross_value will be updated in case of modify revenue or expense
    gross_value = fields.Float(string='Gross Increase Value', default=0.0, copy=False)
    modify_residual = fields.Float(string='Modify Residual Value', default=0.0, copy=False)
    book_value = fields.Float(string='Deferred revenue/expense amount', compute='_compute_residual_value', store=True,
                              copy=False)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('running', 'Running'), ('done', 'Done'), ('close', 'Closed'),
                   ('cancel', 'Cancelled')], string='Status', copy=False, default='draft',
        help="When it is created, the status is 'Draft'.\n"
             "If the it is confirmed, the status in 'Running' and the lines can be posted.\n You can close it\n",
        index=True)
    # After calculating depreciations will get depreciable lines.
    depreciation_move_ids = fields.One2many('account.move', 'asset_id',
                                            string='Depreciation Lines')
    entries_count = fields.Integer(string='Number of entries', compute='_compute_entries_count')
    computation_method = fields.Selection([('no_prorata', 'No Prorata'), ('constant_period', 'Constant Period'),
                                           ('daily_compute', 'Daily Computation')], required=True, default='no_prorata')
    # For depreciation calculation
    cum_residual_amount = fields.Float(string='Cumulative Amount', compute='_compute_cum_residual_amount', store=True)
    prorata_date = fields.Date()
    invoice_line_ids = fields.Many2many('account.move.line', 'asset_invoice_line_rel',
                                        'asset_id', 'line_id', string='Journal Items',
                                        readonly=True, copy=False)
    purchase_value = fields.Float(string='Total purchase value', compute='_compute_purchase_value', store=True,
                                  copy=False)

    def copy_data(self, default=None):
        """ This method generates data for creating a copy of the record."""
        if default is None:
            default = {}
        default['name'] = self.name + _(' (copy)')
        return super().copy_data(default)

    # ----------- Compute Methods -----------------------------

    @api.depends('gross_value', 'original_value', 'total_value', 'not_depreciable_value')
    def _compute_total_modify_value(self):
        """Total amount after and before modification"""
        for rec in self:
            rec.total_modify_value = rec.total_value - rec.not_depreciable_value + rec.gross_value \
                if rec.total_value else 0.0

    @api.depends('depreciation_move_ids', 'depreciation_move_ids.asset_amount',
                 'depreciation_move_ids.asset_residual_amount')
    def _compute_cum_residual_amount(self):
        """Calculate Asset Amounts"""
        for rec in self:
            rec.cum_residual_amount = sum(rec.depreciation_move_ids.mapped('asset_amount'))

    @api.depends('invoice_line_ids', 'invoice_line_ids.account_id', 'asset_type')
    def _compute_original_value(self):
        """Compute the original value based on invoice lines or without invoice lines"""
        for rec in self:
            if not rec.invoice_line_ids:
                rec.original_value = rec.original_value or False
                continue
            if rec.invoice_line_ids.filtered(lambda x: x.move_id.state == 'draft'):
                raise UserError(_("All the lines must be posted."))
            rec.original_value = rec.purchase_value

    @api.depends('invoice_line_ids')
    def _compute_purchase_value(self):
        """Compute the total purchase value from the invoice lines"""
        for rec in self.filtered(lambda x: x.invoice_line_ids):
            if len(rec.invoice_line_ids.account_id) > 1:
                raise UserError(_("The lines are not from the same account."))
            purchase_value = sum(rec.invoice_line_ids.mapped('balance'))
            purchase_value *= -1 if rec.asset_type == 'revenue' else 1
            rec.purchase_value = purchase_value

    @api.depends('original_value', 'not_depreciable_value', 'depreciation_move_ids.state',
                 'depreciation_move_ids.asset_amount', 'invoice_line_ids', 'gross_value')
    def _compute_residual_value(self):
        """Find the residual value"""
        for rec in self:
            total_amount = sum(rec.depreciation_move_ids.filtered(lambda x: x.state == 'posted').mapped('asset_amount'))
            rec.residual_value = rec.total_value - total_amount - rec.not_depreciable_value
            rec.book_value = rec.modify_residual if rec.modify_residual > 0 else rec.residual_value

    def _compute_entries_count(self):
        """Compute the count of jornal entries"""
        for rec in self:
            rec.entries_count = len(rec.depreciation_move_ids)

    @api.depends('name')
    @api.depends_context('asset_type')
    def _compute_asset_type(self):
        """Value of the field asset_type"""
        for rec in self.filtered(lambda x: not x.asset_type and 'asset_type' in self.env.context):
            rec.asset_type = self.env.context['asset_type']

    # ----------- Onchange Methods -----------------------------
    @api.onchange('original_value', 'invoice_line_ids', 'not_depreciable_value', 'gross_value')
    def _onchange_original_value(self):
        """raise error when changing original value if there is already invoice lines"""
        self.total_value = self.original_value
        if self.invoice_line_ids and self.original_value != self.purchase_value:
            raise UserError(_("The amount you have entered does not match the Related Purchase's value "))

    @api.onchange('computation_method', 'first_recognition_date')
    def _onchange_computation_method(self):
        """Assign prorata date based on first_recognition_date"""
        if self.computation_method in ['constant_period', 'daily_compute'] and self.first_recognition_date:
            self.prorata_date = self.first_recognition_date
        else:
            self.prorata_date = False

    @api.onchange('asset_type_id')
    def _onchange_asset_type_id(self):
        """Value assign based on asset type"""
        if self.asset_type_id:
            self.journal_id = self.asset_type_id.journal_id
            self.account_id = self.asset_type_id.account_id
            self.expense_account_id = self.asset_type_id.expense_account_id
            self.number_of_entries = self.asset_type_id.number_of_entries
            self.period = self.asset_type_id.period
            self.computation_method = self.asset_type_id.computation_method

    def unlink(self):
        """When deleting a deferred revenue/expense"""
        for rec in self:
            if rec.state in ['running', 'done']:
                raise UserError(_('The document is in the state %s , So you cannot delete it.',
                                  dict(self._fields['state']._description_selection(self.env)).get(rec.state)))
            posted_moves = len(rec.depreciation_move_ids.filtered(lambda x: x.state == 'posted'))
            if posted_moves > 0:
                raise UserError(_('You cannot delete a record linked to posted entries.'
                                  '\nYou can cancel the linked journal entries.'))
        return super(AccountAssetAsset, self).unlink()

    def action_compute(self):
        """When clicks the compute button create revenue/expense board  and also creates draft entries"""
        start_date = self.prorata_date if self.prorata_date else self.first_recognition_date
        self.compute_depreciation(self.residual_value, self.number_of_entries, start_date)

    def action_confirm(self):
        """When confirming the asset revenue/expense, post the journal entries of each move"""
        if not self.depreciation_move_ids:
            start_date = self.prorata_date if self.prorata_date else self.first_recognition_date
            move_list = self.compute_depreciation(self.residual_value, self.number_of_entries, start_date)
            for move in move_list:
                move._post()
        else:
            for move in self.depreciation_move_ids:
                move._post()
        self.write({'state': 'running'})

    def action_running(self):
        """Button: Set to Running"""
        self.write({'state': 'running'})

    def action_close(self):
        """Button: Close"""
        self.ensure_one()
        self.write({'state': 'close'})

    def action_save_template(self):
        """Button: Save Template"""
        if self.asset_type == 'revenue':
            form_view = self.env.ref('cyllo_accounting.view_account_asset_type_deferred_revenue_form')
        else:
            form_view = self.env.ref('cyllo_accounting.view_account_asset_type_deferred_expense_form')
        return {
            'name': _('Save Template'),
            'views': [[form_view.id, "form"]],
            'res_model': 'account.asset.type',
            'type': 'ir.actions.act_window',
            'context': {
                'default_type': self.asset_type,
                'default_account_id': self.account_id.id,
                'default_expense_account_id': self.expense_account_id.id,
                'default_journal_id': self.journal_id.id,
                'default_number_of_entries': self.number_of_entries,
                'default_period': self.period,
                'default_computation_method': self.computation_method,
                'default_company_id': self.company_id.id,
                'default_currency_id': self.currency_id.id,
            }
        }

    def action_get_entries(self):
        """The smart button shows the corresponding journal entries"""
        self.ensure_one()
        return {
            'name': _("Journal Entries"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('asset_id', '=', self.id)],
        }

    def compute_depreciation_amount(self, depreciation, total_days, number_of_entries):
        """Calculate the amount based the days, total_days and depreciation_date
        that are already computed"""
        depreciation_date = depreciation.get('asset_date')
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
        total_residual = self.total_value - self.not_depreciable_value if self.total_value > 0 else (
                self.residual_value + sum(posted_depreciation_move_ids.mapped('asset_amount')))
        days = depreciation.get('days')
        period_days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[
            1] if self.period == '1' else (depreciation_date.year % 4) and 365 or 366
        days = period_days if days > period_days and self.computation_method == 'constant_period' else days
        if self.computation_method == 'constant_period':
            period_residual_amount = total_residual / number_of_entries
            amount_residual = period_residual_amount / period_days * days
        elif self.computation_method == 'daily_compute':
            amount_residual = total_residual / total_days * days
        else:
            amount_residual = total_residual / number_of_entries
        return amount_residual

    def compute_days(self, prorata_date, depreciation_start_date):
        """Compute days for depreciation board"""
        if prorata_date:
            delta_days = (depreciation_start_date - prorata_date).days + 1
        else:
            delta_days = calendar.monthrange(depreciation_start_date.year, depreciation_start_date.month)[
                1] if self.period == '1' else (depreciation_start_date.year % 4) and 365 or 366
        return delta_days

    def _depreciation_board(self, residual_value, number_of_entries, start_date):
        """Depreciation Board"""
        self.ensure_one()
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
        if residual_value <= 0:
            raise UserError(_('Residual value should be greater than zero'))
        move_values = []
        # total days from start date to end date
        if self.computation_method == 'daily_compute':
            total_days = (start_date + relativedelta(months=int(self.period) * number_of_entries) - start_date).days
        else:
            total_days = int(self.period) * number_of_entries * DAYS_PER_MONTH
        depreciated_days = sum(posted_depreciation_move_ids.mapped('asset_days'))
        depreciations = []
        # Add depreciation dates and days to the list depreciations
        if not float_is_zero(residual_value, precision_rounding=self.currency_id.rounding):
            while depreciated_days < total_days:
                prorata_date = False
                if depreciations:
                    depreciation_start_date = end_of(depreciations[-1].get('asset_end_date'), 'month')
                    depreciation_end_date = end_of(depreciation_start_date + relativedelta(months=1),
                                                   'month') if self.period == '1' else end_of(
                        depreciation_start_date + relativedelta(years=1), 'month')
                else:
                    prorata_date = start_date if self.prorata_date else False
                    if self.period == '1':
                        start_date_days = calendar.monthrange(start_date.year, start_date.month)[1]
                        depreciation_start_date = start_date + relativedelta(day=start_date_days)
                        depreciation_end_date = depreciation_start_date + relativedelta(months=1)
                    else:
                        date_fiscal_year = self.company_id.compute_fiscalyear_dates(start_date).get('date_to')
                        depreciation_start_date = date_fiscal_year \
                            if start_date < date_fiscal_year else date_fiscal_year + relativedelta(years=1)
                        depreciation_end_date = depreciation_start_date + relativedelta(years=1)
                days = self.compute_days(prorata_date, depreciation_start_date)
                depreciations.append(
                    {'asset_end_date': depreciation_end_date, 'asset_date': depreciation_start_date, 'days': days})
                depreciated_days += days
        # If there have value in the list ‘depreciations’,
        # then will calculate the corresponding amount to each depreciation.
        cum_residual = 0
        for depreciation in depreciations:
            amount = self.compute_depreciation_amount(depreciation, total_days, number_of_entries)
            if depreciations[-1] == depreciation:
                already_depreciated = sum(self.depreciation_move_ids.mapped('asset_amount'))
                amount = self.total_value - already_depreciated
            cum_residual += amount
            if cum_residual > residual_value:
                amount -= cum_residual - residual_value
                depreciation.update({'amount': amount})
                if not float_is_zero(depreciation.get('amount'), precision_rounding=self.currency_id.rounding):
                    move_values.append(self.env['account.move'].create(self.env['account.move']._prepare_moves({
                        'amount': depreciation.get('amount') if self.asset_type == 'revenue' else -depreciation.get(
                            'amount'),
                        'asset_id': self,
                        'asset_date': depreciation.get('asset_date'),
                        'date': depreciation.get('asset_date'),
                        'asset_end_date': depreciation.get('asset_end_date'),
                        'asset_days': depreciation.get('days'),
                    })))
                    break
            depreciation.update({'amount': amount})
            if not float_is_zero(depreciation.get('amount'), precision_rounding=self.currency_id.rounding):
                move_values.append(self.env['account.move'].create(self.env['account.move']._prepare_moves({
                    'amount': depreciation.get('amount') if self.asset_type == 'revenue' else -depreciation.get(
                        'amount'),
                    'asset_id': self,
                    'asset_date': depreciation.get('asset_date'),
                    'date': depreciation.get('asset_date'),
                    'asset_end_date': depreciation.get('asset_end_date'),
                    'asset_days': depreciation.get('days'),
                })))

        return move_values

    def compute_depreciation(self, residual_value, number_of_entries, start_date):
        """Compute depreciation moves: Main function for calculating depreciations"""
        # unlink already created draft depreciation moves
        self.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').unlink()
        depreciation_moves = self._depreciation_board(residual_value, number_of_entries, start_date)
        return depreciation_moves
