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
import datetime

from odoo import _, api, models
from odoo.exceptions import UserError


class TrialBalanceReport(models.AbstractModel):
    """
    This abstract model represents a Trial Balance Report.
    It provides methods to generate trial balance reports based on specified filters.
     """
    _name = 'trial.balance.report'
    _inherit = ['report.comparison.mixin']
    _description = 'Trial Balance Report'

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
        Generate a trial balance report based on the provided filters and parameters.

        Args:
            comparison (int): Number of periods to compare against.
            comparison_type (str): Type of comparison ('year', 'month', or 'quarter').
            **filter_kwargs (dict): Additional filter parameters including options, analytic_ids,
                                    journal_ids, get_filters, start_date, and end_date.

        Returns:
            tuple: A tuple containing:
                - list: Trial balance data for each account.
                - dict: Filters for the report.
                - list: Total data for each comparison period.
                - dict: Common total data for all accounts.
        """
        target_move = filter_kwargs.get('options', []) or ['posted']
        analytic_ids = filter_kwargs.get('analytic_ids', [])
        company_ids = tuple(filter_kwargs.get('company_ids') or self.env.companies.ids)
        journal_ids = filter_kwargs.get('journal_ids', [])
        get_filters = filter_kwargs.get('get_filters', False)
        start_date = filter_kwargs.get('start_date', '')
        end_date = filter_kwargs.get('end_date', '')
        if not start_date or not end_date:
            raise UserError(_(
                "Please select both a start date and an end date to "
                "generate the report."))
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise UserError(_("Dates must be provided in the YYYY-MM-DD format."))

        filter_clause = (" AND lines.company_id IN %s"
                         " AND lines.parent_state IN %s")
        base_params = [tuple(company_ids), tuple(target_move)]
        if journal_ids:
            filter_clause += " AND lines.journal_id IN %s"
            base_params.append(tuple(journal_ids))
        if analytic_ids:
            filter_clause += " AND jsonb_exists_any(lines.analytic_distribution, %s)"
            base_params.append([str(rec) for rec in analytic_ids])

        active_company = self.env.company
        active_currency = active_company.currency_id

        def _aggregate(date_clause, date_params, conversion_date):
            """Return ``{account_id: {total_debit, total_credit}}`` for the given
            date window, using the shared parameterised filter clause."""
            currency_table = self.env['res.currency']._get_query_currency_table(
                company_ids, conversion_date)
            self.env.cr.execute(f"""
                SELECT lines.account_id AS account_id,
                       lines.company_id AS company_id,
                       SUM(ROUND(lines.debit * currency_table.rate, currency_table.precision)) AS total_debit,
                       SUM(ROUND(lines.credit * currency_table.rate, currency_table.precision)) AS total_credit
                FROM account_move_line AS lines
                JOIN {currency_table} ON currency_table.company_id = lines.company_id
                WHERE 1 = 1 {filter_clause} AND {date_clause}
                GROUP BY lines.account_id, lines.company_id
            """, base_params + date_params)

            sums = {}
            for row in self.env.cr.dictfetchall():
                acc = row['account_id']
                if acc not in sums:
                    sums[acc] = {'account_id': acc, 'total_credit': 0.0, 'total_debit': 0.0}

                debit = float(row['total_debit'] or 0.0)
                credit = float(row['total_credit'] or 0.0)

                sums[acc]['total_debit'] += debit
                sums[acc]['total_credit'] += credit

            return sums

        accounting_report_data = []
        total_data, total_common_data = {}, {}
        initial_credit_sum, initial_debit_sum, end_credit_sum, end_debit_sum = 0, 0, 0, 0

        period_ranges = []
        initial_date = start_date
        for count in range(0, int(comparison)):
            date_from, date_to = self._get_comparison_dates(
                start_date, end_date, comparison_type, count)
            initial_date = date_from
            period_ranges.append((date_from, date_to))

        period_totals = [_aggregate("lines.date >= %s AND lines.date <= %s",
                                    [date_from, date_to], date_to)
                         for date_from, date_to in period_ranges]
        initial_totals = _aggregate("lines.date < %s", [initial_date], initial_date)
        pnl_types = ('income', 'income_other', 'expense',
                     'expense_depreciation', 'expense_direct_cost')
        fiscal_year_start = self.env.company.compute_fiscalyear_dates(
            initial_date)['date_from']
        if fiscal_year_start == initial_date:
            prior_totals = initial_totals
        else:
            prior_totals = _aggregate("lines.date < %s", [fiscal_year_start], fiscal_year_start)

        account_id_set = set(initial_totals) | set(prior_totals)
        for period in period_totals:
            account_id_set |= set(period)
        account_id_set.discard(None)
        accounts = self.env['account.account'].browse(sorted(account_id_set))
        account_ids = [{
            'acc_id': account.id,
            'name': f"{account.code} {account.name}",
            'code': account.code,
            'annotations': account.annotations,
            'account_type': account.account_type,
        } for account in accounts]
        account_types = {acc['acc_id']: acc['account_type'] for acc in account_ids}
        prior_earnings = 0
        for acc in account_ids:
            if acc['account_type'] in pnl_types:
                prior_row = prior_totals.get(acc['acc_id'])
                if prior_row:
                    prior_earnings += ((prior_row['total_debit'] or 0)
                                       - (prior_row['total_credit'] or 0))
        unaffected_account = self.env['account.account'].search(
            [('account_type', '=', 'equity_unaffected'),
             ('company_id', 'in', company_ids)], limit=1)
        unaffected_id = unaffected_account.id if unaffected_account else False
        if unaffected_id and unaffected_id not in account_types:
            account_ids.append({
                'acc_id': unaffected_id,
                'name': f"{unaffected_account.code} {unaffected_account.name}",
                'code': unaffected_account.code,
                'annotations': unaffected_account.annotations,
                'account_type': 'equity_unaffected'})
            account_types[unaffected_id] = 'equity_unaffected'

        account_ids.sort(key=lambda acc: acc['code'] or '')
        for account in account_ids:
            acc_id = account['acc_id']
            acc_data = {'account': {'id': acc_id, 'name': account['name'],
                                    'annotations': account['annotations']},
                        'initial_data': {}, 'end_data': {}, 'values': []}
            credit, debit = 0, 0
            for count in range(len(period_ranges)):
                row = period_totals[count].get(acc_id)
                total_debit = row['total_debit'] if row and row['total_debit'] is not None else 0
                total_credit = row['total_credit'] if row and row['total_credit'] is not None else 0

                credit += total_credit
                debit += total_debit
                acc_data['values'].append({'debit': total_debit, 'credit': total_credit})

                if count in total_data:
                    total_data[count]['debit'] += total_debit
                    total_data[count]['credit'] += total_credit
                else:
                    total_data[count] = {'debit': total_debit, 'credit': total_credit}

            init_row = initial_totals.get(acc_id)
            initial_total_debit = init_row['total_debit'] if init_row and init_row[
                'total_debit'] is not None else 0
            initial_total_credit = init_row['total_credit'] if init_row and init_row[
                'total_credit'] is not None else 0

            if account_types.get(acc_id) in pnl_types:
                prior_row = prior_totals.get(acc_id)
                prior_debit = prior_row['total_debit'] if prior_row and prior_row[
                    'total_debit'] is not None else 0
                prior_credit = prior_row['total_credit'] if prior_row and prior_row[
                    'total_credit'] is not None else 0
                opening_balance = ((initial_total_debit - initial_total_credit)
                                   - (prior_debit - prior_credit))
            else:
                opening_balance = initial_total_debit - initial_total_credit

            if acc_id == unaffected_id:
                opening_balance += prior_earnings

            acc_data['initial_data'] = {
                'debit': round(opening_balance, 2) if opening_balance > 0 else 0,
                'credit': abs(round(opening_balance, 2)) if opening_balance < 0 else 0}
            end_balance = debit - credit + opening_balance
            acc_data['end_data'] = {'debit': round(end_balance, 2) if end_balance > 0 else 0,
                                    'credit': abs(round(end_balance, 2)) if end_balance < 0 else 0}
            accounting_report_data.append(acc_data)
            initial_credit_sum += acc_data['initial_data']['credit']
            initial_debit_sum += acc_data['initial_data']['debit']
            end_debit_sum += acc_data['end_data']['debit']
            end_credit_sum += acc_data['end_data']['credit']
            total_common_data = {'initial_credit_sum': round(initial_credit_sum, 2),
                                 'initial_debit_sum': round(initial_debit_sum, 2),
                                 'end_debit_sum': round(end_debit_sum, 2),
                                 'end_credit_sum': round(end_credit_sum, 2)}
        filters = self._get_report_filters if get_filters else {}
        filters['currency_symbol'] = active_currency.symbol
        filters['currency_position'] = active_currency.position
        total_vals = list(total_data.values())
        for val in total_vals:
            val.update({
                'debit': round(val.get('debit', 0), 2),
                'credit': round(val.get('credit', 0), 2)
            })
        return accounting_report_data, filters, total_vals, total_common_data

    @property
    def _get_report_filters(self):
        """
        Get the filters for the trial balance report.
        Returns:
            dict: A dictionary containing filters such as journals and analytics.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name', 'company_id']),
            'analytics': self.env['account.analytic.account'].search_read([],
                                                                          ['name', 'display_name', 'company_id'])
        }
