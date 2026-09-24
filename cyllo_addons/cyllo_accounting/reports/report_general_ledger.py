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
import io
import json
import xlsxwriter

from odoo import _, api, models
from odoo.exceptions import UserError

LIMIT = 100


class GeneralLedgerReport(models.AbstractModel):
    """
    Abstract model for generating the General Ledger Report.

    This model serves as a base for generating the General Ledger Report in the accounting system.

    """
    _name = 'report.cyllo_accounting.general_ledger'
    _description = 'General Ledger Report'

    @api.model
    def get_report(self, **kwargs):
        """
        Generate a general ledger report.

        The interactive (collapsed) view passes ``summary_only=True`` and gets
        only the per-account totals in a single grouped query; the detail lines
        for an account are then lazy-loaded on expand via
        :meth:`get_account_data`. The PDF/XLSX paths omit ``summary_only`` and
        receive the detail lines as well.

        Args:
            **kwargs: Filter parameters, including get_filters, account_id,
                summary_only, limit and offset.

        Returns:
            tuple: (account_data, account_sum_data, account_data_page, filters,
                currency_symbol).
        """
        get_filters = kwargs.get('get_filters', False)
        account_id = kwargs.pop('account_id', False)
        summary_only = kwargs.get('summary_only', False)
        limit = kwargs.get('limit', LIMIT)
        offset = kwargs.get('offset', 0)

        sums = self._get_grouped_sums(account_id, **kwargs)
        openings = self._get_opening_balances(
            [account_id] if account_id else None, **kwargs)
        account_ids = list(set(sums) | set(openings))
        accounts = self.env['account.account'].browse(account_ids).sorted(
            key=lambda account: account.code or '')
        account_labels = self._get_account_labels(accounts)

        account_data = {}
        account_sum_data = {}
        account_data_page = {}
        for account in accounts:
            # An opening-only account has no strict-range sum row, but is a
            # valid ledger account and must therefore be displayed.
            row = sums.get(account.id, {
                'account_id': account.id,
                'total_credit': 0.0,
                'total_debit': 0.0,
                'line_count': 0,
            })
            name = account_labels[account.id]
            opening = openings.get(account.id) or {}
            opening_debit = opening.get('opening_debit') or 0.0
            opening_credit = opening.get('opening_credit') or 0.0
            period_debit = row['total_debit'] or 0.0
            period_credit = row['total_credit'] or 0.0
            account_data_page[name] = {
                "limit": limit,
                "offset": offset,
                "total": row['line_count'],
                "account_id": account.id,
                "opening_debit": round(opening_debit, 2),
                "opening_credit": round(opening_credit, 2),
                "opening_balance": round(opening_debit - opening_credit, 2),
            }
            account_sum_data[name] = [{
                'account_id': account.id,
                'total_credit': round(opening_credit + period_credit, 2),
                'total_debit': round(opening_debit + period_debit, 2),
                'opening_debit': round(opening_debit, 2),
                'opening_credit': round(opening_credit, 2),
                'opening_balance': round(opening_debit - opening_credit, 2),
            }]
            account_data[name] = ([] if summary_only
                                  else self._get_data(account.id, **kwargs))
        filters = self._get_report_filters if get_filters else {}
        currency_symbol = self.env.company.currency_id.symbol
        return [account_data], [account_sum_data], account_data_page, filters, currency_symbol

    def _get_account_labels(self, accounts):
        """Return stable report keys without losing same-code accounts from
        different companies in a multi-company report.

        The existing layout uses the dictionary key as the visible account
        label.  Keep that label unchanged unless it is ambiguous; in that
        case, append the company name so neither account overwrites the other.
        """
        duplicate_names = {}
        for account in accounts:
            duplicate_names.setdefault(account.display_name, []).append(account)
        return {
            account.id: (
                account.display_name
                if len(duplicate_names[account.display_name]) == 1
                else "%s (%s)" % (account.display_name, account.company_id.name)
            )
            for account in accounts
        }

    @property
    def _get_report_filters(self):
        """
        Retrieve filters for generating a financial report.

        Returns:
            dict: A dictionary containing filters for the report, including:
                - 'journals': A list of dictionaries representing account journals, each containing 'name'.
                - 'analytics': A list of dictionaries representing analytic accounts, each containing 'name'.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name', 'company_id']),
            'analytics': self.env['account.analytic.account'].search_read([],
                                                                          ['name', 'display_name', 'company_id'])
        }

    def _report_filter(self, **kwargs):
        """Build the shared, fully parameterised WHERE fragment for the move-line
        queries.

        Every user-supplied value (target move, dates, companies, journals,
        analytics) is passed as a query parameter rather than interpolated into
        the SQL, which avoids SQL injection.

        Returns:
            tuple(str, list): The SQL fragment (to append after an existing
                condition) and the ordered parameter list.
        """
        target_move = kwargs.get('target_move', []) or ['posted']
        analytic_ids = kwargs.get('analytic_ids', [])
        journal_ids = kwargs.get('journal_ids', [])
        company_ids = kwargs.get('company_ids', []) or self.env.companies.ids
        start_date = kwargs.get('start_date', "")
        end_date = kwargs.get('end_date', "")
        if not start_date or not end_date:
            raise UserError(_(
                "Please select both a start date and an end date to "
                "generate the report."))
        clause = (" AND move_line.account_id IS NOT NULL"
                  " AND move_line.parent_state IN %s"
                  " AND move_line.date >= %s AND move_line.date <= %s"
                  " AND move_line.company_id IN %s")
        params = [tuple(target_move), start_date, end_date, tuple(company_ids)]
        if journal_ids:
            clause += " AND move_line.journal_id IN %s"
            params.append(tuple(journal_ids))
        if analytic_ids:
            clause += " AND jsonb_exists_any(move_line.analytic_distribution, %s)"
            params.append([str(rec) for rec in analytic_ids])
        return clause, params

    def _get_currency_table(self, **kwargs):
        """Return Odoo's standard company-to-report-currency table.

        General Ledger consolidates selected companies in the current user's
        company currency.  Odoo's accounting reports use the report end date
        for this conversion table, rather than converting every historical
        journal item at its own posting date.
        """
        company_ids = tuple(kwargs.get('company_ids') or self.env.companies.ids)
        end_date = kwargs.get('end_date')
        if not end_date:
            raise UserError(_("Please select both a start date and an end date to generate the report."))
        return self.env['res.currency']._get_query_currency_table(
            company_ids, end_date)

    def _get_grouped_sums(self, account_id, **kwargs):
        """Return per-account totals and line count in a single grouped query.

        Args:
            account_id (int|bool): Restrict to one account, or all accounts.
            **kwargs: Forwarded to :meth:`_report_filter`.

        Returns:
            dict: ``{account_id: {total_credit, total_debit, line_count}}``.
        """
        clause, params = self._report_filter(**kwargs)
        currency_table = self._get_currency_table(**kwargs)
        query = f"""
            SELECT move_line.account_id AS account_id,
                   move_line.company_id AS company_id,
                   SUM(ROUND(move_line.credit * currency_table.rate,
                             currency_table.precision)) AS total_credit,
                   SUM(ROUND(move_line.debit * currency_table.rate,
                             currency_table.precision)) AS total_debit,
                   COUNT(*) AS line_count
            FROM account_move_line move_line
            JOIN {currency_table} ON currency_table.company_id = move_line.company_id
            WHERE 1 = 1 {clause}"""
        query_params = list(params)
        if account_id:
            query += " AND move_line.account_id = %s"
            query_params.append(int(account_id))
        query += " GROUP BY move_line.account_id, move_line.company_id"

        self.env.cr.execute(query, query_params)

        sums = {}
        for row in self.env.cr.dictfetchall():
            acc = row['account_id']
            if acc not in sums:
                sums[acc] = {'account_id': acc, 'total_credit': 0.0, 'total_debit': 0.0,
                             'line_count': 0}

            credit = float(row['total_credit'] or 0.0)
            debit = float(row['total_debit'] or 0.0)
            sums[acc]['total_debit'] += debit
            sums[acc]['total_credit'] += credit
            sums[acc]['line_count'] += row['line_count']

        return sums

    def _get_data(self, account_id, **kwargs):
        """
        Retrieve detailed move line data for a specific account, paginated at the
        SQL level (``LIMIT``/``OFFSET``) so a page never loads the whole account.

        Args:
            account_id (int): The account to retrieve detail lines for.
            **kwargs: Forwarded to :meth:`_report_filter`, plus limit and offset.

        Returns:
            list: A list of move-line dicts (see report template for keys). Lines
                with no partner are kept (LEFT JOIN) with partner_name/id None.
        """
        clause, params = self._report_filter(**kwargs)
        currency_table = self._get_currency_table(**kwargs)
        query = f"""SELECT move_line.id, move_line.annotations, move_line.account_id,
                   move_line.company_id,
                   ROUND(move_line.credit * currency_table.rate,
                         currency_table.precision) AS credit,
                   move_line.date,
                   ROUND(move_line.debit * currency_table.rate,
                         currency_table.precision) AS debit,
                   move_line.journal_id, move_line.move_id, move_line.move_name,
                   move_line.name, partner.name partner_name, partner.id partner_id
                   FROM account_move_line move_line
                   JOIN {currency_table} ON currency_table.company_id = move_line.company_id
                   LEFT JOIN res_partner partner ON move_line.partner_id = partner.id
                   WHERE move_line.account_id = %s {clause}
                   ORDER BY move_line.date ASC, move_line.id ASC"""
        query_params = [int(account_id)] + params
        limit = kwargs.get('limit', LIMIT)
        offset = kwargs.get('offset', 0)
        if limit:
            query += " LIMIT %s OFFSET %s"
            query_params += [limit, offset]

        self.env.cr.execute(query, query_params)
        return self.env.cr.dictfetchall()

    def _get_opening_balances(self, account_ids, **kwargs):
        """Gross debit/credit brought forward before the period start (cumulative
        from inception), per account — matching the production general ledger,
        which does not reset P&L accounts at the fiscal year.

        Args:
            account_ids (list|None): Accounts to compute the opening for, or
                ``None`` to aggregate every account with qualifying opening
                activity.
            **kwargs: target_move, start_date, company_ids, journal_ids,
                analytic_ids.

        Returns:
            dict: ``{account_id: {opening_debit, opening_credit}}``.
        """
        if account_ids == []:
            return {}
        start_date = kwargs.get('start_date', "")
        if not start_date:
            return {}
        target_move = kwargs.get('target_move', []) or ['posted']
        company_ids = kwargs.get('company_ids', []) or self.env.companies.ids
        journal_ids = kwargs.get('journal_ids', [])
        analytic_ids = kwargs.get('analytic_ids', [])
        clause = (" AND move_line.account_id IS NOT NULL"
                  " AND move_line.parent_state IN %s"
                  " AND move_line.date < %s"
                  " AND move_line.company_id IN %s")
        params = [tuple(target_move), start_date, tuple(company_ids)]
        if account_ids:
            clause += " AND move_line.account_id IN %s"
            params.append(tuple(account_ids))
        if journal_ids:
            clause += " AND move_line.journal_id IN %s"
            params.append(tuple(journal_ids))
        if analytic_ids:
            clause += " AND jsonb_exists_any(move_line.analytic_distribution, %s)"
            params.append([str(rec) for rec in analytic_ids])
        currency_table = self._get_currency_table(**kwargs)
        query = f"""
            SELECT move_line.account_id AS account_id,
                   move_line.company_id AS company_id,
                   SUM(ROUND(move_line.debit * currency_table.rate,
                             currency_table.precision)) AS opening_debit,
                   SUM(ROUND(move_line.credit * currency_table.rate,
                             currency_table.precision)) AS opening_credit
            FROM account_move_line move_line
            JOIN {currency_table} ON currency_table.company_id = move_line.company_id
            WHERE 1 = 1 {clause}
            GROUP BY move_line.account_id, move_line.company_id"""

        self.env.cr.execute(query, params)

        openings = {}
        for row in self.env.cr.dictfetchall():
            acc = row['account_id']
            if acc not in openings:
                openings[acc] = {'account_id': acc, 'opening_debit': 0.0, 'opening_credit': 0.0}

            debit = float(row['opening_debit'] or 0.0)
            credit = float(row['opening_credit'] or 0.0)
            openings[acc]['opening_debit'] += debit
            openings[acc]['opening_credit'] += credit

        return openings

    def _running_start(self, account_id, **kwargs):
        """Sum of (debit - credit) for the account's period lines *before* the
        current page offset, so the running balance continues correctly across
        pages. Returns 0 for the first page.
        """
        offset = kwargs.get('offset', 0)
        if not offset:
            return 0.0
        clause, params = self._report_filter(**kwargs)
        currency_table = self._get_currency_table(**kwargs)
        query = f"""
            SELECT ROUND(move_line.debit * currency_table.rate,
                         currency_table.precision) AS debit,
                   ROUND(move_line.credit * currency_table.rate,
                         currency_table.precision) AS credit
            FROM account_move_line move_line
            JOIN {currency_table} ON currency_table.company_id = move_line.company_id
            WHERE move_line.account_id = %s {clause}
            ORDER BY move_line.date ASC, move_line.id ASC
            LIMIT %s"""

        self.env.cr.execute(query, [int(account_id)] + params + [offset])

        running = 0.0
        for row in self.env.cr.dictfetchall():
            debit = float(row['debit'] or 0.0)
            credit = float(row['credit'] or 0.0)
            running += debit - credit

        return running

    @api.model
    def get_account_data(self, **kwargs):
        """
        Retrieve one account's detail lines for a given page (used to lazy-load
        an account on expand and to page through it).

        Args:
            **kwargs: limit, offset, account_id and the report filters.

        Returns:
            tuple(dict, dict): (account_data, account_data_page) keyed by the
                account display name.
        """
        account_data = {}
        account_data_page = {}
        limit = kwargs.get("limit", LIMIT)
        offset = kwargs.get("offset", 0)
        account_id = kwargs.pop("account_id", None)
        # The client supplies the visible key so a same-code account from a
        # second selected company updates its own row rather than creating a
        # new one under the unqualified display name.
        account_label = kwargs.pop("account", None)
        if account_id:
            account = self.env['account.account'].browse(account_id)
            # The full line count (for the pager) comes from the grouped query,
            # not from the paginated detail page.
            sums = self._get_grouped_sums(account_id, **kwargs)
            total = (sums.get(account.id) or {}).get('line_count', 0)
            opening = self._get_opening_balances([account_id], **kwargs).get(account_id) or {}
            opening_debit = opening.get('opening_debit') or 0.0
            opening_credit = opening.get('opening_credit') or 0.0
            opening_net = opening_debit - opening_credit
            lines = self._get_data(account_id, **kwargs)
            running = opening_net + self._running_start(account_id, **kwargs)
            for line in lines:
                running += (line['debit'] or 0.0) - (line['credit'] or 0.0)
                line['balance'] = round(running, 2)
            account_label = account_label or account.display_name
            account_data_page[account_label] = {
                "limit": limit,
                "offset": offset,
                "total": total,
                "account_id": account.id,
                "opening_debit": round(opening_debit, 2),
                "opening_credit": round(opening_credit, 2),
                "opening_balance": round(opening_net, 2),
            }
            account_data[account_label] = lines
        return account_data, account_data_page

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
        Generate an XLSX report based on the provided data.

        Args:
            data (str): JSON data containing information required for generating the report.
            response: The HTTP response object used to send the generated XLSX file.
            report_name (str): Name of the report.

        Returns:
            None
        """
        data = json.loads(data)
        filters_kwargs = data.get("filterData", {})
        filters_kwargs['limit'] = 0
        filters_kwargs['get_filters'] = True

        account_data, account_sum_data, dummy, filters, currency_symbol = self.get_report(
            **filters_kwargs)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = filters_kwargs.get('start_date', "")
        end_date = filters_kwargs.get('end_date', "")
        sheet = workbook.add_worksheet()
        option = "With Draft Entries" if len(filters_kwargs.get('target_move', [])) == 2 else ""
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        header_text_name = workbook.add_format({'font_size': '10px', 'border': 1, 'bold': True})
        header_text_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.write('A1:b1', report_name, head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Journals', filter_head)
        sheet.write('B5:b4', 'Analytic Accounts', filter_head)
        sheet.write('B6:b4', 'Options', filter_head)
        sheet.merge_range('C3:G3', f"{start_date} to {end_date}", filter_body)
        journal_ids = filters_kwargs.get('journal_ids', False)
        if journal_ids:
            journals = filters.get('journals', [])
            display_names = list(
                map(lambda record: record['name'],
                    filter(lambda rec: rec['id'] in journal_ids, journals)))
            pos = len(display_names) + 3
            display_names = ', '.join(display_names)
            sheet.merge_range(3, 2, 3, pos, display_names, filter_body)
        analytic_ids = filters_kwargs.get('analytic_ids', False)
        if analytic_ids:
            analytics = filters.get('analytics', [])
            display_names = list(
                map(lambda record: record['name'],
                    filter(lambda rec: rec['id'] in analytic_ids, analytics)))
            pos = len(display_names) + 3
            display_names = ', '.join(display_names)
            sheet.merge_range(4, 2, 4, pos, display_names, filter_body)
        sheet.merge_range(5, 2, 5, 3, option, filter_body)
        analytic_ids = filters_kwargs.get('analytic_ids', False)
        col = 0
        sheet.write(8, col, ' ', sub_heading)
        sheet.write(8, col + 1, 'Date', sub_heading)
        sheet.merge_range('C9:E9', 'Communication', sub_heading)
        sheet.merge_range('F9:G9', 'Partner', sub_heading)
        sheet.merge_range('H9:I9', 'Debit', sub_heading)
        sheet.merge_range('J9:K9', 'Credit', sub_heading)
        sheet.merge_range('L9:M9', 'Balance', sub_heading)
        row = 8
        total_debit = total_credit = 0
        for rec in account_data[0]:
            account_obj = account_sum_data[0][rec][0]
            row += 1
            sheet.write(row, col, rec, header_text_name)
            sheet.write(row, col + 1, ' ', txt_name)
            sheet.merge_range(row, col + 2, row, col + 4, ' ', txt_name)
            sheet.merge_range(row, col + 4, row, col + 6, ' ', txt_name)
            sheet.merge_range(row, col + 7, row, col + 8,
                              f"{currency_symbol} {account_obj['total_debit']}",
                              header_text_name)
            sheet.merge_range(row, col + 9, row, col + 10,
                              f"{currency_symbol} {account_obj['total_credit']}",
                              header_text_name)
            sheet.merge_range(row, col + 11, row, col + 12,
                              f"{currency_symbol} {account_obj['total_debit'] - account_obj['total_credit']}",
                              header_text_name)
            row += 1
            sheet.write(row, col, 'Initial Balance', header_text_name)
            sheet.write(row, col + 1, ' ', txt_name)
            sheet.merge_range(row, col + 2, row, col + 4, ' ', txt_name)
            sheet.merge_range(row, col + 5, row, col + 6, ' ', txt_name)
            sheet.merge_range(row, col + 7, row, col + 8,
                              f"{currency_symbol} {account_obj.get('opening_debit', 0.0)}",
                              header_text_name)
            sheet.merge_range(row, col + 9, row, col + 10,
                              f"{currency_symbol} {account_obj.get('opening_credit', 0.0)}",
                              header_text_name)
            sheet.merge_range(row, col + 11, row, col + 12,
                              f"{currency_symbol} {account_obj.get('opening_balance', 0.0)}",
                              header_text_name)
            running_balance = account_obj.get('opening_balance', 0.0)
            for inner_rec in account_data[0][rec]:
                row += 1
                name = inner_rec['name'] if inner_rec.get('name', "") else ""
                partner_name = inner_rec.get('partner_name') or ''
                sheet.set_row(row, 20 if len(name) < 40 else 25)
                sheet.write(row, col, inner_rec['move_name'], txt_name)
                sheet.write(row, col + 1, inner_rec['date'].strftime("%Y-%m-%d"), txt_name)
                sheet.set_column(col + 2, col + 4, 15 if len(name) < 40 else 20)
                sheet.merge_range(row, col + 2, row, col + 4, name, txt_name)
                sheet.merge_range(row, col + 5, row, col + 6, partner_name, txt_name)
                sheet.merge_range(row, col + 7, row, col + 8,
                                  f"{currency_symbol} {inner_rec['debit']}", txt_name)
                sheet.merge_range(row, col + 9, row, col + 10,
                                  f"{currency_symbol} {inner_rec['credit']}", txt_name)
                running_balance += inner_rec['debit'] - inner_rec['credit']
                sheet.merge_range(row, col + 11, row, col + 12,
                                  f"{currency_symbol} {running_balance}", txt_name)

            total_credit += account_obj['total_credit']
            total_debit += account_obj['total_debit']
        sheet.merge_range(row, col, row, col + 6, 'Total', filter_head)
        sheet.merge_range(row, col + 7, row, col + 8, f"{currency_symbol} {total_debit}",
                          filter_head)
        sheet.merge_range(row, col + 9, row, col + 10, f"{currency_symbol} {total_credit}",
                          filter_head)
        sheet.merge_range(row, col + 11, row, col + 12,
                          f"{currency_symbol} {total_debit - total_credit}", filter_head)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


class GeneralLedgerReportPDF(models.AbstractModel):
    """
    Abstract model for generating the General Ledger PDF Report.
    """
    _name = 'report.cyllo_accounting.report_general_ledger'
    _description = 'General Ledger PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Get the values required to generate the general ledger pdf report.
        """
        report_name = data.get('reportName', "")
        filter_data = data.get('filterData', {})
        filter_by = data.get('filterBy', "")
        periods = data.get('periods', {})
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        journals = [self.env['account.journal'].browse(rec).name for rec in
                    data['filterData'].get('journal_ids', [])]
        account_analytic = [self.env['account.analytic.account'].browse(rec).name for rec in
                            data['filterData'].get('analytic_ids', [])]

        pdf_data = self.env['report.cyllo_accounting.general_ledger'].get_report(**filter_data)

        return {
            'doc_ids': docids,
            'doc_model': 'report.cyllo_accounting.report_general_ledger',
            'periods': periods,
            'filter_by': filter_by,
            'options': data['filterData'].get('options', []),
            'pdf_data': pdf_data,
            'report_name': report_name,
            'comparison': comparison,
            'comparison_type': comparison_type,
            'journals': journals,
            'account_analytic': account_analytic,
            'data': data,
            'currency_symbol': pdf_data[4],
        }
