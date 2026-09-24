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
from dateutil.relativedelta import relativedelta

from odoo import api, models
from odoo.tools.date_utils import get_month


class TaxReport(models.AbstractModel):
    """
        This model for generating the Tax Report.
    """
    _name = 'tax.report'
    _inherit = ['report.comparison.mixin']
    _description = 'Tax Report'

    def _format_currency(self, amount, currency):
        if currency.position == 'before':
            return f"{currency.symbol} {amount:,.2f}"
        return f"{amount:,.2f} {currency.symbol}"

    def _round_report_amount(self, amount, currency, mixed_company_currencies):
        """Use the report currency precision only for a consolidation.

        The single-company reports historically round to two decimals and are
        deliberately left on that path.
        """
        return (currency.round(amount) if mixed_company_currencies
                else round(amount, 2))

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
            Generates the tax report based on the provided filter parameters.

            Args:
                comparison (str): The type of comparison for the report.
                comparison_type (str): The comparison type for the report.
                **filter_kwargs: Additional keyword arguments for filtering.

            Returns:
                dict: A dictionary containing the tax report data.

            Raises:
                ValueError: If the date format is incorrect.
        """
        company = filter_kwargs.get('company', [])
        options = filter_kwargs.get('options', [])
        date_from = filter_kwargs.get('startDate', False)
        date_to = filter_kwargs.get('endDate', False)
        report_type = filter_kwargs.get('report_type', False)

        start_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
        company_query = ""
        if company:
            if len(company) > 1:
                company_query += f""" AND lines.company_id IN {tuple(company)}"""
            else:
                company_query += f""" AND lines.company_id = {company[0]}"""

        company_ids = tuple(company or self.env.companies.ids)
        mixed_company_currencies = len(
            self.env['res.company'].browse(company_ids).mapped(
                'currency_id')) > 1

        report_data = []
        for key in ['sale', 'purchase']:
            if report_type == 'generic':
                report_data.append(
                    self._get_report_data_for_generic(key=key, comparison=comparison, comparison_type=comparison_type,
                                                      start_date=start_date, end_date=end_date, options=options,
                                                      company=company_query,
                                                      mixed_company_currencies=mixed_company_currencies))
            elif report_type == 'account':
                report_data.append(
                    self._get_report_data_for_account(key=key, comparison=comparison, comparison_type=comparison_type,
                                                      start_date=start_date, end_date=end_date, options=options,
                                                      company=company_query))
            elif report_type == 'tax':
                report_data.append(
                    self._get_report_data_for_tax(key=key, comparison=comparison, comparison_type=comparison_type,
                                                  start_date=start_date, end_date=end_date, options=options,
                                                  company=company_query))
        return {'report_type': report_type, 'report_data': report_data}

    def _get_report_data_for_generic(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "generic" report type.
            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "generic" report type.
        """
        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        mixed_company_currencies = kwargs.get('mixed_company_currencies', False)

        all_taxes = self.env['account.tax'].sudo().search([('type_tax_use', '=', key)])
        parent_map = {}
        for t in all_taxes:
            for child in t.children_tax_ids:
                parent_map[child.id] = t.id

        periods_data = []
        all_tax_ids_found = set()
        active_company = self.env.company
        active_curr = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}

        for count in range(0, int(comparison)):
            date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)

            query_base = f"""
                select lines.id as line_id, line_tax.account_tax_id as tax_id, lines.company_id, lines.date,
                       lines.debit, lines.credit
                from account_move_line as lines
                inner join account_move_line_account_tax_rel as line_tax on lines.id = line_tax.account_move_line_id
                inner join account_move as move on lines.move_id = move.id
                where move.state in %s and lines.date >= %s and lines.date <= %s {company}
            """
            self.env.cr.execute(query_base, (tuple(options), date_from, date_to))
            base_rows = self.env.cr.dictfetchall()

            query_tax = f"""
                select lines.tax_line_id as tax_id, lines.company_id, lines.date,
                       sum(lines.debit) as debit, sum(lines.credit) as credit
                from account_move_line as lines
                inner join account_move as move on lines.move_id = move.id
                where lines.tax_line_id IS NOT NULL and move.state in %s and lines.date >= %s and lines.date <= %s {company}
                group by lines.tax_line_id, lines.company_id, lines.date
            """
            self.env.cr.execute(query_tax, (tuple(options), date_from, date_to))
            tax_rows = self.env.cr.dictfetchall()

            period_taxes = {}
            line_processed_for_tax = set()

            for row in base_rows:
                t_id = row['tax_id']
                t_id = parent_map.get(t_id, t_id)
                all_tax_ids_found.add(t_id)

                line_id = row['line_id']
                if (line_id, t_id) in line_processed_for_tax:
                    continue
                line_processed_for_tax.add((line_id, t_id))

                comp = companies.get(row['company_id'])
                if not comp: continue
                comp_curr = comp.currency_id
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                if comp_curr != active_curr:
                    conversion_date = date_to if mixed_company_currencies else row['date']
                    debit = comp_curr._convert(debit, active_curr, active_company, conversion_date)
                    credit = comp_curr._convert(credit, active_curr, active_company, conversion_date)

                net = (credit - debit) if key == 'sale' else (debit - credit)
                if t_id not in period_taxes:
                    period_taxes[t_id] = {'net': 0.0, 'tax': 0.0}
                period_taxes[t_id]['net'] += net

            for row in tax_rows:
                t_id = row['tax_id']
                if t_id not in [t.id for t in all_taxes] and t_id not in parent_map:
                    continue
                t_id = parent_map.get(t_id, t_id)
                all_tax_ids_found.add(t_id)

                comp = companies.get(row['company_id'])
                if not comp: continue
                comp_curr = comp.currency_id
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                if comp_curr != active_curr:
                    conversion_date = date_to if mixed_company_currencies else row['date']
                    debit = comp_curr._convert(debit, active_curr, active_company, conversion_date)
                    credit = comp_curr._convert(credit, active_curr, active_company, conversion_date)

                tax_amt = (credit - debit) if key == 'sale' else (debit - credit)
                if t_id not in period_taxes:
                    period_taxes[t_id] = {'net': 0.0, 'tax': 0.0}
                period_taxes[t_id]['tax'] += tax_amt

            periods_data.append(period_taxes)

        data = {'key': key, 'values': []}
        total_data = {count: {'net': 0.0, 'tax': 0.0} for count in range(int(comparison))}

        for t_id in all_tax_ids_found:
            tax_record = self.env['account.tax'].browse(t_id)
            if tax_record.type_tax_use != key:
                continue

            children_amounts = [child.amount for child in tax_record.children_tax_ids]
            total_percent = sum(children_amounts) if children_amounts else tax_record.amount
            display_name = f"{tax_record.name} ({round(total_percent, 1)}%)"

            tax_data = {
                'tax_id': t_id,
                'display_name': display_name,
                'annotations': tax_record.annotations,
                'children_tax_ids': tax_record.children_tax_ids.ids,
                'values': []
            }

            for count in range(int(comparison)):
                p_data = periods_data[count].get(t_id, {'net': 0.0, 'tax': 0.0})
                net_amount = self._round_report_amount(
                    p_data['net'], active_curr, mixed_company_currencies)
                tax_amount = self._round_report_amount(
                    p_data['tax'], active_curr, mixed_company_currencies)

                tax_data['values'].append({
                    'net': net_amount, 'tax': tax_amount,
                    'format_net': self._format_currency(net_amount, active_curr),
                    'format_tax': self._format_currency(tax_amount, active_curr)
                })
                total_data[count]['net'] += net_amount
                total_data[count]['tax'] += tax_amount

            data['values'].append(tax_data)
            
        for count in total_data:
            total_data[count]['format_net'] = self._format_currency(total_data[count]['net'], active_curr)
            total_data[count]['format_tax'] = self._format_currency(total_data[count]['tax'], active_curr)
            
        data['totals'] = list(total_data.values())
        return data

    def _get_report_data_for_account(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "account" report type.

            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "account" report type.
        """

        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        mixed_company_currencies = kwargs.get('mixed_company_currencies', False)

        all_taxes = self.env['account.tax'].sudo().search([('type_tax_use', '=', key)])
        parent_map = {}
        for t in all_taxes:
            for child in t.children_tax_ids:
                parent_map[child.id] = t.id

        periods_data = []
        all_acc_tax_pairs = set()

        active_company = self.env.company
        active_curr = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        accounts_cache = {acc.id: acc for acc in self.env['account.account'].sudo().search([])}

        for count in range(0, int(comparison)):
            date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)

            query_base = f"""
                select lines.id as line_id, line_tax.account_tax_id as tax_id, lines.account_id, lines.company_id, lines.date,
                       lines.debit, lines.credit
                from account_move_line as lines
                inner join account_move_line_account_tax_rel as line_tax on lines.id = line_tax.account_move_line_id
                inner join account_move as move on lines.move_id = move.id
                where move.state in %s and lines.date >= %s and lines.date <= %s {company}
            """
            self.env.cr.execute(query_base, (tuple(options), date_from, date_to))
            base_rows = self.env.cr.dictfetchall()

            period_taxes = {}
            line_processed = set()

            for row in base_rows:
                t_id = row['tax_id']
                t_id = parent_map.get(t_id, t_id)
                acc_id = row['account_id']

                all_acc_tax_pairs.add((acc_id, t_id))

                line_id = row['line_id']
                if (line_id, t_id) in line_processed:
                    continue
                line_processed.add((line_id, t_id))

                comp = companies.get(row['company_id'])
                if not comp: continue
                comp_curr = comp.currency_id
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                if comp_curr != active_curr:
                    conversion_date = date_to if mixed_company_currencies else row['date']
                    debit = comp_curr._convert(debit, active_curr, active_company, conversion_date)
                    credit = comp_curr._convert(credit, active_curr, active_company, conversion_date)

                net = (credit - debit) if key == 'sale' else (debit - credit)
                pair_key = (acc_id, t_id)
                if pair_key not in period_taxes:
                    period_taxes[pair_key] = {'net': 0.0, 'tax': 0.0}
                period_taxes[pair_key]['net'] += net

            periods_data.append(period_taxes)

        # For the account grouped report, we calculate the tax mathematically from the net amount,
        # to correctly distribute it across the base accounts as requested.
        data = []
        total_data = {count: {'net': 0.0, 'tax': 0.0} for count in range(int(comparison))}

        acc_groups = {}
        for acc_id, t_id in all_acc_tax_pairs:
            if acc_id not in acc_groups:
                acc_groups[acc_id] = []
            acc_groups[acc_id].append(t_id)

        for acc_id, t_ids in acc_groups.items():
            acc_record = accounts_cache.get(acc_id)
            if not acc_record: continue

            acc_data = {
                'account': {'id': acc_id, 'name': f"{acc_record.code} {acc_record.name}"},
                'values': [],
            }

            for t_id in t_ids:
                tax_record = self.env['account.tax'].browse(t_id)
                if tax_record.type_tax_use != key:
                    continue

                children_amounts = [child.amount for child in tax_record.children_tax_ids]
                total_percent = sum(children_amounts) if children_amounts else tax_record.amount
                display_name = f"{tax_record.name} ({round(total_percent, 1)}%)"

                tax_data = {
                    'tax_id': t_id,
                    'display_name': display_name,
                    'annotations': tax_record.annotations,
                    'children_tax_ids': tax_record.children_tax_ids.ids,
                    'values': []
                }

                for count in range(int(comparison)):
                    p_data = periods_data[count].get((acc_id, t_id), {'net': 0.0})
                    net_amount = self._round_report_amount(
                        p_data['net'], active_curr, mixed_company_currencies)
                    tax_amount = self._round_report_amount(
                        net_amount * (total_percent / 100), active_curr,
                        mixed_company_currencies)

                    tax_data['values'].append({
                        'net': net_amount, 'tax': tax_amount,
                        'format_net': self._format_currency(net_amount, active_curr),
                        'format_tax': self._format_currency(tax_amount, active_curr)
                    })
                    total_data[count]['net'] += net_amount
                    total_data[count]['tax'] += tax_amount

                acc_data['values'].append(tax_data)
            data.append(acc_data)
            
        for count in total_data:
            total_data[count]['format_net'] = self._format_currency(total_data[count]['net'], active_curr)
            total_data[count]['format_tax'] = self._format_currency(total_data[count]['tax'], active_curr)

        return {'key': key, 'data': data, 'totals': list(total_data.values())}

    def _get_report_data_for_tax(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "tax" report type.
            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "tax" report type.
            """
        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        mixed_company_currencies = kwargs.get('mixed_company_currencies', False)

        all_taxes = self.env['account.tax'].sudo().search([('type_tax_use', '=', key)])
        parent_map = {}
        for t in all_taxes:
            for child in t.children_tax_ids:
                parent_map[child.id] = t.id

        periods_data = {}
        all_tax_acc_pairs = set()

        active_company = self.env.company
        active_curr = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        accounts_cache = {acc.id: acc for acc in self.env['account.account'].sudo().search([])}

        for count in range(0, int(comparison)):
            date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)
            periods_data[count] = {}

            query_base = f"""
                select lines.id as line_id, line_tax.account_tax_id as tax_id, lines.account_id, lines.company_id,
                 lines.date, lines.debit, lines.credit
                from account_move_line as lines
                inner join account_move_line_account_tax_rel as line_tax on lines.id = line_tax.account_move_line_id
                inner join account_move as move on lines.move_id = move.id
                where move.state in %s and lines.date >= %s and lines.date <= %s {company}
            """
            self.env.cr.execute(query_base, (tuple(options), date_from, date_to))
            base_rows = self.env.cr.dictfetchall()

            line_processed = set()

            for row in base_rows:
                t_id = row['tax_id']
                t_id = parent_map.get(t_id, t_id)
                acc_id = row['account_id']

                all_tax_acc_pairs.add((t_id, acc_id))

                line_id = row['line_id']
                if (line_id, t_id) in line_processed:
                    continue
                line_processed.add((line_id, t_id))

                comp = companies.get(row['company_id'])
                if not comp: continue
                comp_curr = comp.currency_id
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                if comp_curr != active_curr:
                    conversion_date = date_to if mixed_company_currencies else row['date']
                    debit = comp_curr._convert(debit, active_curr, active_company, conversion_date)
                    credit = comp_curr._convert(credit, active_curr, active_company, conversion_date)

                net = (credit - debit) if key == 'sale' else (debit - credit)
                pair_key = (t_id, acc_id)
                if pair_key not in periods_data[count]:
                    periods_data[count][pair_key] = {'net': 0.0, 'tax': 0.0}
                periods_data[count][pair_key]['net'] += net

        data = []
        total_data = {count: {'net': 0.0, 'tax': 0.0} for count in range(int(comparison))}

        tax_groups = {}
        for t_id, acc_id in all_tax_acc_pairs:
            if t_id not in tax_groups:
                tax_groups[t_id] = []
            tax_groups[t_id].append(acc_id)

        for t_id, acc_ids in tax_groups.items():
            tax_record = self.env['account.tax'].browse(t_id)
            if tax_record.type_tax_use != key:
                continue

            children_amounts = [child.amount for child in tax_record.children_tax_ids]
            total_percent = sum(children_amounts) if children_amounts else tax_record.amount
            display_name = f"{tax_record.name} ({round(total_percent, 1)}%)"

            tax_data = {
                'tax_id': t_id,
                'display_name': display_name,
                'annotations': tax_record.annotations,
                'children_tax_ids': tax_record.children_tax_ids.ids,
                'values': []
            }

            for acc_id in acc_ids:
                acc_record = accounts_cache.get(acc_id)
                if not acc_record: continue

                acc_data = {
                    'account': {'account_id': acc_id, 'name': f"{acc_record.code} {acc_record.name}"},
                    'values': []
                }

                for count in range(int(comparison)):
                    p_data = periods_data[count].get((t_id, acc_id), {'net': 0.0})
                    net_amount = self._round_report_amount(
                        p_data['net'], active_curr, mixed_company_currencies)
                    tax_amount = self._round_report_amount(
                        net_amount * (total_percent / 100), active_curr,
                        mixed_company_currencies)

                    acc_data['values'].append({
                        'net': net_amount, 'tax': tax_amount,
                        'format_net': self._format_currency(net_amount, active_curr),
                        'format_tax': self._format_currency(tax_amount, active_curr)
                    })
                    total_data[count]['net'] += net_amount
                    total_data[count]['tax'] += tax_amount

                tax_data['values'].append(acc_data)
            data.append(tax_data)
            
        for count in total_data:
            total_data[count]['format_net'] = self._format_currency(total_data[count]['net'], active_curr)
            total_data[count]['format_tax'] = self._format_currency(total_data[count]['tax'], active_curr)

        return {'key': key, 'data': data, 'totals': list(total_data.values())}

    @staticmethod
    def _get_comparison_dates(start_date, end_date, comparison_type, count):
        """
            Calculates the start and end dates for the comparison periods based on the specified comparison type.

            Args:
                start_date (datetime.date): The start date of the period.
                end_date (datetime.date): The end date of the period.
                comparison_type (str): The type of comparison ('year', 'month', or 'quarter').
                count (int): The number of comparison periods.

            Returns:
                tuple: A tuple containing the start and end dates for the comparison period.
        """
        if comparison_type == 'year':
            date_from = start_date - relativedelta(years=count)
            date_to = end_date - relativedelta(years=count)
        elif comparison_type == 'month':
            start_date_r = start_date - relativedelta(months=count)
            end_date_r = end_date - relativedelta(months=count)
            date_from, dummy = get_month(start_date_r)
            dummy, date_to = get_month(end_date_r)
        else:  # Should handle the quarter case
            start_date_r = start_date - relativedelta(
                months=count * 3)
            end_date_r = end_date - relativedelta(months=count * 3)
            date_from, dummy = get_month(start_date_r)
            dummy, date_to = get_month(end_date_r)
        return date_from, date_to
