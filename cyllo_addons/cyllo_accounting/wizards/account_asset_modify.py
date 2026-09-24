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
from odoo.tools.date_utils import end_of, start_of

DAYS_PER_MONTH = 30


class AccountAssetModify(models.TransientModel):
    """Wizard for Asset Modification"""
    _name = 'account.asset.modify'
    _description = 'Account Asset Modify'

    name = fields.Text(string='Reason', required=True)
    asset_id = fields.Many2one(comodel_name='account.asset.asset', required=True, ondelete="cascade")
    residual_value = fields.Float()
    number_of_entries = fields.Integer(string='Duration', default=6, required=True, help="The number of entries")
    period = fields.Selection([('1', 'Months'), ('12', 'Years')], readonly=True,
                              help="The time between the entries")
    company_id = fields.Many2one('res.company', related='asset_id.company_id')
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id', store=True)

    @api.model
    def default_get(self, fields):
        """Adding default values for the wizard"""
        res = super(AccountAssetModify, self).default_get(fields)
        asset_id = self.env.context.get('active_id')
        asset = self.env['account.asset.asset'].browse(asset_id)
        if 'asset_id' in fields:
            res.update({'asset_id': asset.id})
        if 'residual_value' in fields:
            res.update({'residual_value': asset.residual_value})
        if 'period' in fields and asset.period:
            res.update({'period': asset.period})
        else:
            res.update({'period': '1'})
        if 'number_of_entries' in fields and asset.number_of_entries:
            res.update({'number_of_entries': asset.number_of_entries})
        return res

    def compute_depreciation_amount(self, depreciation, total_days, org_number_of_entries):
        """Calculate the amount based the days, total_days and depreciation_date that are already computed"""
        depreciation_date = depreciation.get('asset_date')
        posted_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
            lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
        all_total_days = (self.asset_id.prorata_date + relativedelta(
            months=int(self.period) * org_number_of_entries) - self.asset_id.prorata_date).days \
            if self.asset_id.prorata_date else (self.asset_id.first_recognition_date + relativedelta(
            months=int(self.period) * org_number_of_entries) - self.asset_id.first_recognition_date).days
        total_residual = self.asset_id.total_value - self.asset_id.not_depreciable_value \
            if self.asset_id.total_value > 0 else self.residual_value + sum(
            posted_depreciation_move_ids.mapped('asset_amount'))
        year = depreciation_date.year
        days = depreciation.get('days')
        period_days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[
            1] if self.period == '1' else (year % 4) and 365 or 366
        days = period_days if days > period_days and self.asset_id.computation_method == 'constant_period' else days
        if self.asset_id.computation_method == 'constant_period':
            period_residual_amount = total_residual / org_number_of_entries
            amount_residual = period_residual_amount / period_days * days
        elif self.asset_id.computation_method == 'daily_compute':
            amount_residual = total_residual / all_total_days * days
        else:
            amount_residual = total_residual / org_number_of_entries
        return amount_residual

    def compute_days(self, prorata_date, depreciation_start_date):
        """Compute days for depreciation"""
        year = depreciation_start_date.year
        if prorata_date:
            delta_days = (depreciation_start_date - prorata_date).days
        else:
            delta_days = calendar.monthrange(depreciation_start_date.year, depreciation_start_date.month)[
                1] if self.period == '1' else (year % 4) and 365 or 366
        return delta_days

    def compute_modify_depreciation(self, residual_value, number_of_entries, start_date, gross_value):
        """Compute modified depreciation"""
        move_values = []
        if residual_value > 0:
            if self.asset_id.computation_method == 'daily_compute':
                total_days = (start_date + relativedelta(
                    months=int(self.period) * number_of_entries) - start_date).days
            else:
                total_days = int(self.period) * number_of_entries * DAYS_PER_MONTH
            total_residual = residual_value
            depreciated_days = 0
            posted_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
                lambda x: x.state == 'posted' and not x.check_increment)
            depreciations = []
            if not float_is_zero(residual_value, precision_rounding=self.currency_id.rounding):
                while depreciated_days < total_days:
                    prorata_date = False
                    if depreciations:
                        depreciation_start_date = end_of(depreciations[-1].get('asset_end_date'), 'month')
                        depreciation_end_date = end_of(depreciation_start_date + relativedelta(months=1),
                                                       'month') if self.period == '1' else end_of(
                            depreciation_start_date + relativedelta(years=1), 'month')
                    else:
                        prorata_date = start_date if self.asset_id.prorata_date else False
                        date_fiscal_year = self.company_id.compute_fiscalyear_dates(start_date).get('date_to')
                        if self.period == '1':
                            depreciation_start_date = start_date + relativedelta(
                                day=calendar.monthrange(start_date.year, start_date.month)[1])
                            depreciation_end_date = depreciation_start_date + relativedelta(months=1)
                        else:
                            depreciation_start_date = date_fiscal_year if start_date < date_fiscal_year \
                                else date_fiscal_year + relativedelta(years=1)
                            depreciation_end_date = depreciation_start_date + relativedelta(years=1)
                    days = self.compute_days(prorata_date, depreciation_start_date)
                    depreciations.append(
                        {'asset_end_date': depreciation_end_date, 'asset_date': depreciation_start_date, 'days': days})
                    depreciated_days += days
            if depreciations:
                cum_residual = 0
                depreciation_gross_count = len(depreciations) - len(posted_depreciation_move_ids)
                add_gross_amount = gross_value / depreciation_gross_count if depreciation_gross_count > 0 else 0
                for depreciation in depreciations:
                    amount = self.compute_depreciation_amount(depreciation, total_days, self.asset_id.number_of_entries)
                    amount += add_gross_amount
                    cum_residual += amount
                    if cum_residual > total_residual:
                        amount -= cum_residual - total_residual
                        depreciation.update({'amount': amount})
                        if not float_is_zero(depreciation.get('amount'), precision_rounding=self.currency_id.rounding):
                            move_values.append(self.env['account.move'].create(self.env['account.move']._prepare_moves({
                                'amount': depreciation.get(
                                    'amount') if self.asset_id.asset_type == 'revenue' else -depreciation.get('amount'),
                                'asset_id': self.asset_id,
                                'asset_date': depreciation.get('asset_date'),
                                'date': depreciation.get('asset_date'),
                                'asset_end_date': depreciation.get('asset_end_date'),
                                'asset_days': depreciation.get('days'),
                            })))
                            break
                        break
                    depreciation.update({'amount': amount})
                    if not float_is_zero(depreciation.get('amount'), precision_rounding=self.currency_id.rounding):
                        move_values.append(self.env['account.move'].create(self.env['account.move']._prepare_moves({
                            'amount': depreciation.get(
                                'amount') if self.asset_id.asset_type == 'revenue' else -depreciation.get('amount'),
                            'asset_id': self.asset_id,
                            'asset_date': depreciation.get('asset_date'),
                            'date': depreciation.get('asset_date'),
                            'asset_end_date': depreciation.get('asset_end_date'),
                            'asset_days': depreciation.get('days'),
                        })))
        return move_values

    def action_modify(self):
        """Button: Modify"""
        self.ensure_one()
        if self.residual_value <= 0:
            raise UserError(_('Residual value should be greater than zero'))
        old_residual = self.asset_id.residual_value
        total_value = self.asset_id.total_value - self.asset_id.not_depreciable_value
        un_posted_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
            lambda x: x.state == 'draft')
        cancel_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
            lambda x: x.state == 'cancel')
        posted_depreciation_move_ids = self.asset_id.depreciation_move_ids.filtered(
            lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
        number_of_entries = self.number_of_entries - len(posted_depreciation_move_ids.filtered(
            lambda x: x.check_increment))
        start_date = today = fields.Date.context_today(self)
        # If there is no draft entries then modification is not possible
        if cancel_depreciation_move_ids:
            raise UserError(_('Set to draft the canceled journal entry for modify the depreciation.'))
        if not un_posted_depreciation_move_ids:
            raise UserError(_('All revenues are posted'))
        else:
            # First unlink all draft entries for creating new
            un_posted_depreciation_move_ids.unlink()
            if posted_depreciation_move_ids:
                total_residual = total_value if total_value > 0 else self.residual_value + sum(
                    posted_depreciation_move_ids.mapped('asset_amount'))
                start_asset_date = posted_depreciation_move_ids[-1].asset_date
                days_difference = (fields.Date.today() - start_asset_date).days
                year = today.year
                period_days = calendar.monthrange(today.year, today.month)[
                    1] if self.period == '1' else (year % 4) and 365 or 366
                days = period_days if days_difference > period_days else days_difference
                period_residual_amount = total_residual / self.asset_id.number_of_entries
                if days_difference < 0:
                    raise UserError(_('For Keeping the audit trail, '
                                      'you cannot delete the journal entries once they have been posted.'
                                      'Instead, you can set to draft the journal entry'))
                if not posted_depreciation_move_ids[-1].check_increment or posted_depreciation_move_ids[
                    -1].asset_date != today:
                    # If it is the first modification created today then calculate an increment value also checks the
                    # last entry date is not today
                    amount_residual = period_residual_amount / period_days * days
                    if amount_residual > 0:
                        move_values = self.env['account.move']._prepare_moves({
                            'amount': amount_residual if self.asset_id.asset_type == 'revenue' else -amount_residual,
                            'asset_id': self.asset_id,
                            'asset_date': today,
                            'asset_end_date': today,
                            'date': today,
                            'check_increment': True,
                            'asset_days': days_difference,
                        })
                        if move_values:
                            new_move = self.env['account.move'].create(move_values)
                            new_move._post()
                if self.residual_value < self.asset_id.book_value:
                    # If the residual value to modify is less than the book_value of asset then
                    # create a new entry to post all balance amount
                    current_posted_moves = self.asset_id.depreciation_move_ids.filtered(
                        lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
                    current_residual = total_value - current_posted_moves[-1].asset_residual_amount
                    current_end_date = start_of(today + relativedelta(months=1),
                                                'month') if self.period == '1' else start_of(
                        today + relativedelta(years=1), 'month')
                    if current_residual >= self.residual_value:
                        current_total_residual = current_residual - self.residual_value
                        if current_total_residual > 0:
                            move_values = self.env['account.move']._prepare_moves({
                                'amount': current_total_residual
                                if self.asset_id.asset_type == 'revenue' else -current_total_residual,
                                'asset_id': self.asset_id,
                                'asset_date': today,
                                'asset_end_date': current_end_date,
                                'date': today,
                                'asset_days': 0,
                            })
                            start_date = current_end_date
                            if move_values:
                                new_move = self.env['account.move'].create(move_values)
                                new_move._post()
                    else:
                        current_total_residual = current_residual - self.residual_value
                        if current_total_residual > 0:
                            move_values = self.env['account.move']._prepare_moves({
                                'amount': current_total_residual
                                if self.asset_id.asset_type == 'revenue' else -current_total_residual,
                                'asset_id': self.asset_id,
                                'asset_date': today,
                                'asset_end_date': current_end_date,
                                'date': today,
                                'rev_entry': True,
                                'asset_days': 0,
                            })
                            start_date = current_end_date
                            if move_values:
                                new_move = self.env['account.move'].create(move_values)
                                new_move._post()
                all_current_posted_moves = self.asset_id.depreciation_move_ids.filtered(
                    lambda x: x.state == 'posted').sorted(key=lambda l: (l.asset_date, l.id))
                if self.residual_value > old_residual:
                    self.asset_id.gross_value = self.residual_value - old_residual
                    residual_amount = (total_value + self.asset_id.gross_value) - all_current_posted_moves[
                        -1].asset_residual_amount
                else:
                    self.asset_id.gross_value = 0
                    residual_amount = total_value - all_current_posted_moves[
                        -1].asset_residual_amount
                self.asset_id.modify_residual = self.residual_value
                if number_of_entries > 0:
                    move_list = self.compute_modify_depreciation(residual_amount, number_of_entries, start_date,
                                                                 self.asset_id.gross_value)
                    for move in move_list:
                        move._post()
            else:
                self.asset_id.original_value = self.residual_value
                self.asset_id.total_value = self.residual_value
                self.asset_id.residual_value = self.residual_value
                residual_amount = self.residual_value - self.asset_id.not_depreciable_value
                self.asset_id.modify_residual = 0
                move_list = self.asset_id.compute_depreciation(residual_amount, self.number_of_entries, start_date)
                for move in move_list:
                    move._post()
