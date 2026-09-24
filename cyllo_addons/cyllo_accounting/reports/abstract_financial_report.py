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

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_fiscal_year

ACCOUNTING_TYPES = ['income', 'income_other', 'expense', 'expense_depreciation',
                    'expense_direct_cost', 'asset_receivable', 'asset_cash',
                    'asset_current', 'asset_non_current', 'asset_prepayments',
                    'asset_fixed', 'liability_payable', 'liability_credit_card',
                    'liability_current', 'liability_non_current', 'equity',
                    'equity_unaffected']


class AbstractFinancialReport(models.AbstractModel):
    """
    Abstract model for handling financial reports such as balance sheets and profit and loss statements.
    This abstract model provides common functionality required for generating and managing financial reports.
    """

    _name = 'abstract.financial.report'
    _inherit = ['report.comparison.mixin']
    _description = 'Financial Report'

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
        Generate a report based on specified parameters.

        Args:
            comparison (int): Number of comparison periods.
            comparison_type (str): Type of comparison ('year', 'month', or 'quarter').
            **filter_kwargs: Additional keyword arguments for filtering data, including:
                - start_date (str): Start date of the reporting period in 'YYYY-MM-DD' format.
                - end_date (str): End date of the reporting period in 'YYYY-MM-DD' format.
                - get_filters (bool): Whether to retrieve report filters.

        Returns:
            tuple: A tuple containing:
                - accounting_report_data (list): A list of dictionaries containing report data for each
                comparison period.
                - filters (dict or None): A dictionary containing filters for the report,
                if requested; otherwise, None.
        """
        self._check_report_access()
        start_date = filter_kwargs.get('start_date', "")
        end_date = filter_kwargs.get('end_date', "")
        get_filters = filter_kwargs.get('get_filters', False)
        if not start_date or not end_date:
            raise UserError(_(
                "Please select both a start date and an end date to "
                "generate the report."))
        accounting_report_data = []
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise UserError(_("Dates must be provided in the YYYY-MM-DD format."))

        for count in range(0, int(comparison)):
            date_from, date_to = self._get_comparison_dates(
                start_date, end_date, comparison_type, count)
            period_filters = dict(filter_kwargs, start_date=date_from,
                                  end_date=date_to)

            company_ids = tuple(
                period_filters.get('company_ids') or self.env.companies.ids)
            companies = self.env['res.company'].browse(company_ids)
            if len(companies.mapped('currency_id')) > 1:
                period_filters['conversion_date'] = date_to

            account_entries = self._get_account_entries(**period_filters)
            accounting_report_data.append(self._get_report_data(account_entries))

        filters = self._get_report_filters if get_filters else {}
        return accounting_report_data, filters

    def _check_report_access(self):
        """Ensure the caller may read accounting data before running any query.

        ``get_report`` is exposed over RPC, so it is gated on the same group
        that guards the accounting report menus rather than relying on the UI
        alone.
        """
        if not (self.env.user.has_group('account.group_account_user') or
                self.env.user.has_group('account.group_account_readonly') or
                self.env.user.has_group('account.group_account_invoice')):
            raise UserError(_(
                "You do not have the access rights required to view "
                "accounting reports."))

    @property
    def _get_report_filters(self):
        """
          Get filters for generating a report.

          Returns:
              dict: A dictionary containing filters for the report, including:
                  - 'journals': A list of dictionaries representing account journals, each containing 'name'.
                  - 'accounts': A list of dictionaries representing accounts, each containing 'name'.
                  - 'analytics': A list of dictionaries representing analytic accounts, each containing 'name'.

              ``company_id`` is read along with every filter so the client can
              group the dropdown entries company wise.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name', 'company_id']),
            'accounts': self.env['account.account'].search_read([], ['name', 'display_name', 'company_id']),
            'analytics': self.env['account.analytic.account'].search_read([], ['name', 'display_name', 'company_id'])
        }

    def _get_report_data(self, account_entries):
        """
        Calculate and aggregate data for generating a financial report.

        Args:
            account_entries (dict): A dictionary containing entries for various account types.

        Returns:
            dict: A dictionary containing aggregated data for the report, including:
                - 'total': Total balance.
                - 'total_value': Total balance as a float.
                - 'total_expense': Total expenses.
                - 'total_income': Total income.
                - 'total_current_asset': Total current assets.
                - 'total_assets': Total assets.
                - 'total_current_liability': Total current liabilities.
                - 'total_liability': Total liabilities.
                - 'total_earnings': Total earnings.
                - 'total_unallocated_earning': Total unallocated earnings.
                - 'total_equity': Total equity.
                - 'total_balance': Total balance (sum of liabilities and equity).
                - 'currency_symbol': Symbol of the currency used.
                - 'gross_profit': Gross profit.
                - Additional keys for individual account entries.
        """
        total_income = 0
        total_expense = 0
        total_current_asset = 0
        total_assets = 0
        total_current_liability = 0
        total_liability = 0
        total_unallocated_earning = 0
        total_equity = 0
        total_cost_of_revenue = 0

        for account_type, entries in account_entries.items():
            for entry in entries[0]:
                amount = float(entry['amount'])
                if account_type in ['income', 'income_other']:
                    total_income += amount
                elif account_type == 'expense_direct_cost':
                    total_cost_of_revenue += amount
                elif account_type in ['expense', 'expense_depreciation']:
                    total_expense += amount
                elif account_type in ['asset_receivable', 'asset_current', 'asset_cash', 'asset_prepayments']:
                    total_current_asset += amount
                elif account_type in ['asset_fixed', 'asset_non_current']:
                    total_assets += amount
                elif account_type in ['liability_current', 'liability_payable']:
                    total_current_liability += amount
                elif account_type == 'liability_non_current':
                    total_liability += amount
                elif account_type == 'equity_unaffected':
                    total_unallocated_earning += amount
                elif account_type == 'equity':
                    total_equity += amount

        net_profit = total_income - total_cost_of_revenue - total_expense
        total_unallocated_earning += net_profit
        total_assets += total_current_asset
        total_liability += total_current_liability
        total_equity += total_unallocated_earning
        total = total_liability + total_equity
        expense_direct_cost = account_entries.get("expense_direct_cost")
        income = account_entries.get("income")
        gross_profit = income[2] - expense_direct_cost[2]
        super_total = round(net_profit, 2)
        return {
            'total': f"{super_total:,.2f}",
            'total_value': super_total,
            'total_expense': f"{total_expense:,.2f}",
            'total_income': f"{total_income:,.2f}",
            'total_current_asset': f"{total_current_asset:,.2f}",
            'total_assets': f"{total_assets:,.2f}",
            'total_current_liability': f"{total_current_liability:,.2f}",
            'total_liability': f"{total_liability:,.2f}",
            'total_earnings': f"{net_profit:,.2f}",
            'total_unallocated_earning': f"{total_unallocated_earning:,.2f}",
            'total_equity': f"{total_equity:,.2f}",
            'total_balance': f"{total:,.2f}",
            'currency_symbol': self.env.company.currency_id.symbol,
            'gross_profit': f"{gross_profit:,.2f}",
            **account_entries
        }

    _NEGATED_ACCOUNT_TYPES = (
        'income', 'income_other', 'liability_payable', 'liability_current',
        'liability_credit_card', 'liability_non_current', 'equity',
        'equity_unaffected',
    )

    def _fetch_grouped_balances(self, **filter_kwargs):
        """Aggregate move-line balances per account in a single query.

        Replaces the previous one-query-per-account loop: a single, fully
        parameterised statement returns ``{account_id: balance}`` for every
        account that has matching move lines. All user-supplied values are
        passed as query parameters (never string-interpolated), which closes
        the earlier SQL-injection exposure, and results are scoped to the
        active companies.

        When ``start_date`` is falsy the lower date bound is omitted, so the
        balance is accumulated from inception up to ``end_date`` (used by the
        Balance Sheet, which is a point-in-time statement); otherwise it covers
        the ``[start_date, end_date]`` range (used by the Profit and Loss).

        Args:
            **filter_kwargs: target_move, analytic_ids, journal_ids,
                account_ids, start_date and end_date.

        Returns:
            dict: ``{account_id: balance}`` where balance is debit - credit.
        """
        target_move = filter_kwargs.get('target_move', [])
        analytic_ids = filter_kwargs.get('analytic_ids', [])
        journal_ids = filter_kwargs.get('journal_ids', [])
        account_ids = filter_kwargs.get('account_ids', [])
        start_date = filter_kwargs.get('start_date', "")
        end_date = filter_kwargs.get('end_date', "")
        company_ids = tuple(filter_kwargs.get('company_ids') or self.env.companies.ids)
        conversion_date = filter_kwargs.get('conversion_date')

        use_report_currency_table = bool(conversion_date)
        if use_report_currency_table:
            currency_table = self.env['res.currency']._get_query_currency_table(
                company_ids, conversion_date)
            query = f"""
                SELECT line.account_id,
                       line.company_id,
                       COALESCE(SUM(ROUND(line.debit * currency_table.rate,
                                          currency_table.precision)), 0) AS total_debit,
                       COALESCE(SUM(ROUND(line.credit * currency_table.rate,
                                          currency_table.precision)), 0) AS total_credit
                FROM account_move_line AS line
                JOIN {currency_table} ON currency_table.company_id = line.company_id
                WHERE line.date <= %s
                  AND line.company_id IN %s
            """
        else:
            query = """
                SELECT account_id,
                       company_id,
                       date,
                       COALESCE(SUM(debit), 0) AS total_debit,
                       COALESCE(SUM(credit), 0) AS total_credit
                FROM account_move_line
                WHERE date <= %s
                  AND company_id IN %s
            """
        params = [end_date, company_ids]
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if target_move:
            query += " AND parent_state IN %s"
            params.append(tuple(target_move))
        if account_ids:
            query += " AND account_id IN %s"
            params.append(tuple(account_ids))
        if journal_ids:
            query += " AND journal_id IN %s"
            params.append(tuple(journal_ids))
        if analytic_ids:
            query += " AND jsonb_exists_any(analytic_distribution, %s)"
            params.append([str(rec) for rec in analytic_ids])
        if use_report_currency_table:
            query += " GROUP BY line.account_id, line.company_id"
        else:
            query += " GROUP BY account_id, company_id, date"

        self.env.cr.execute(query, params)

        balances = {}
        for row in self.env.cr.dictfetchall():
            acc = row['account_id']
            if acc not in balances:
                balances[acc] = 0.0

            debit = float(row['total_debit'] or 0.0)
            credit = float(row['total_credit'] or 0.0)
            balances[acc] += (debit - credit)

        return balances

    def _get_account_entries(self, **filter_kwargs):
        """Build the per-type account entries consumed by ``_get_report_data``.

        Runs one grouped balance query for the period, then buckets every
        company-scoped account by its type. Accounts with no movement keep a
        zero balance (as before) so the templates decide whether to show them.

        Args:
            **filter_kwargs: forwarded to :meth:`_fetch_grouped_balances`.

        Returns:
            dict: ``{account_type: (entries, formatted_total, total)}`` where
                each entry is a dict with name, format_amount, id, amount and
                annotations.
        """
        balances = self._fetch_grouped_balances(**filter_kwargs)
        return self._bucket_account_entries(balances)

    def _bucket_account_entries(self, balances, company_ids=None):
        """Group pre-computed per-account balances by account type.

        Shared by the Profit and Loss (period balances) and the Balance Sheet
        (cumulative balances); the caller decides how ``balances`` was fetched.

        Args:
            balances (dict): ``{account_id: balance}`` (debit - credit).

        Returns:
            dict: ``{account_type: (entries, formatted_total, total)}``.
        """
        accounts = self.env['account.account'].search([
            ('account_type', 'in', ACCOUNTING_TYPES),
            ('company_id', 'in', company_ids or self.env.companies.ids),
        ])
        grouped_accounts = {}
        for account in accounts:
            code = account.code
            acc_type = account.account_type
            key = (code, acc_type)
            amount = balances.get(account.id, 0.0)

            if key not in grouped_accounts:
                grouped_accounts[key] = {
                    'name': f"{code} - {account.name}",
                    'id': account.id,
                    'amount': 0.0,
                    'annotations': account.annotations,
                    'account_type': acc_type
                }

            if acc_type in self._NEGATED_ACCOUNT_TYPES:
                amount = -amount

            grouped_accounts[key]['amount'] += amount

        currency = self.env.company.currency_id
        entries = {account_type: [] for account_type in ACCOUNTING_TYPES}
        totals = {account_type: 0.0 for account_type in ACCOUNTING_TYPES}

        for key, acc_data in grouped_accounts.items():
            acc_type = acc_data['account_type']
            amount = currency.round(acc_data['amount'])

            acc_data['format_amount'] = "{:,.2f}".format(amount)
            acc_data['amount'] = amount

            entries[acc_type].append(acc_data)
            totals[acc_type] += amount
        return {
            account_type: (
                entries[account_type],
                "{:,.2f}".format(currency.round(totals[account_type])),
                currency.round(totals[account_type]),
            )
            for account_type in ACCOUNTING_TYPES
        }

    def _net_profit_from_entries(self, account_entries):
        """Net profit (income - expense) from a bucketed entries mapping.

        Mirrors the Profit and Loss aggregation: direct costs reduce income and
        the remaining expense types are subtracted.
        """
        total_income = (account_entries['income'][2]
                        + account_entries['income_other'][2]
                        - account_entries['expense_direct_cost'][2])
        total_expense = (account_entries['expense'][2]
                         + account_entries['expense_depreciation'][2])
        return total_income - total_expense

    def _get_balance_sheet_data(self, as_of_date, **filter_kwargs):
        """Build one Balance Sheet column as of ``as_of_date``.

        Unlike the Profit and Loss, balances are accumulated from inception up
        to ``as_of_date`` (a point-in-time snapshot). The current-year result is
        the net profit from the fiscal-year start to ``as_of_date``; earlier
        profits fall under previous-years' unallocated earnings. Computing every
        balance cumulatively keeps the sheet balanced
        (Assets = Liabilities + Equity).

        Args:
            as_of_date (date): The date the snapshot is taken at.
            **filter_kwargs: journal_ids, account_ids, analytic_ids, target_move.

        Returns:
            dict: Totals and per-type account entries for the column.
        """
        currency = self.env.company.currency_id
        company_ids = tuple(filter_kwargs.get('company_ids') or self.env.companies.ids)
        cumulative_balances = self._fetch_grouped_balances(
            **dict(filter_kwargs, start_date="", end_date=as_of_date,
                   conversion_date=as_of_date))
        account_entries = self._bucket_account_entries(cumulative_balances, company_ids)
        fiscal_year_start = self.env.company.compute_fiscalyear_dates(
            as_of_date)['date_from']
        current_year_balances = self._fetch_grouped_balances(
            **dict(filter_kwargs, start_date=fiscal_year_start, end_date=as_of_date,
                   conversion_date=as_of_date))
        current_year_entries = self._bucket_account_entries(current_year_balances, company_ids)

        current_year_earnings = self._net_profit_from_entries(current_year_entries)
        prior_years_earnings = (self._net_profit_from_entries(account_entries)
                                - current_year_earnings)
        total_current_asset = (account_entries['asset_receivable'][2]
                               + account_entries['asset_cash'][2]
                               + account_entries['asset_current'][2]
                               + account_entries['asset_prepayments'][2])
        total_assets = (total_current_asset
                        + account_entries['asset_fixed'][2]
                        + account_entries['asset_non_current'][2])
        total_current_liability = (account_entries['liability_current'][2]
                                   + account_entries['liability_payable'][2]
                                   + account_entries['liability_credit_card'][2])
        total_liability = (total_current_liability
                           + account_entries['liability_non_current'][2])
        total_unallocated_earning = (current_year_earnings + prior_years_earnings
                                     + account_entries['equity_unaffected'][2])
        total_equity = account_entries['equity'][2] + total_unallocated_earning
        total_balance = total_liability + total_equity
        return {
            'total_current_asset': f"{currency.round(total_current_asset):,.2f}",
            'total_assets': f"{currency.round(total_assets):,.2f}",
            'total_current_liability': f"{currency.round(total_current_liability):,.2f}",
            'total_liability': f"{currency.round(total_liability):,.2f}",
            'total_earnings': f"{currency.round(current_year_earnings):,.2f}",
            'total_prior_earning': f"{currency.round(prior_years_earnings):,.2f}",
            'total_unallocated_earning': f"{currency.round(total_unallocated_earning):,.2f}",
            'total_equity': f"{currency.round(total_equity):,.2f}",
            'total_balance': f"{currency.round(total_balance):,.2f}",
            'currency_symbol': currency.symbol,
            **account_entries,
        }

    @api.model
    def get_balance_sheet(self, comparison, comparison_type, **filter_kwargs):
        """Generate Balance Sheet data with one column per comparison period.

        Each column is a point-in-time snapshot taken at the end date of the
        (shifted) comparison period. Mirrors :meth:`get_report`'s signature and
        return shape so it plugs into the same templates and client code.

        Returns:
            tuple(list, dict): ``(per-column data, optional filters)``.
        """
        self._check_report_access()
        start_date = filter_kwargs.get('start_date', "")
        end_date = filter_kwargs.get('end_date', "")
        get_filters = filter_kwargs.get('get_filters', False)
        if not start_date or not end_date:
            raise UserError(_(
                "Please select both a start date and an end date to "
                "generate the report."))
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise UserError(_("Dates must be provided in the YYYY-MM-DD format."))
        report_data = []
        for count in range(0, int(comparison)):
            dummy, as_of_date = self._get_comparison_dates(
                start_date, end_date, comparison_type, count)
            report_data.append(
                self._get_balance_sheet_data(as_of_date, **filter_kwargs))
        filters = self._get_report_filters if get_filters else {}
        return report_data, filters

    @api.model
    def get_financial_year(self):
        """
        Retrieve the start and end dates of the current financial year.

        Returns:
            dict: A dictionary containing the start and end dates of the financial year, with keys:
                - 'start_date': Start date of the financial year in 'YYYY-MM-DD' format.
                - 'end_date': End date of the financial year in 'YYYY-MM-DD' format.
        """
        today = fields.date.today()
        acc_fiscal_year = self.env['account.fiscal.year'].search(
            [('company_id', '=', self.env.company.id), ('state', '=', 'open'), ('start_date', '<=', today), ('end_date', '>=', today)], limit=1)
        if acc_fiscal_year:
            start_date = acc_fiscal_year.start_date
            end_date = acc_fiscal_year.end_date
        else:
            start_date, end_date = get_fiscal_year(today)
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
    
    @api.model
    def get_search_view(self):
        return self.sudo().env.ref("cyllo_accounting.view_account_move_line_search").id
