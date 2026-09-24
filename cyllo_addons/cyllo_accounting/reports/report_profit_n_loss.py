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

from odoo import api, models


class PnlReport(models.AbstractModel):
    """
    Abstract model for generating a Profit and Loss Report.

    This model serves as a template for creating specific Profit and Loss reports.

    Attributes:
        _name (str): The technical name of the model ('report.pnl_report').
        _description (str): A brief description of the model ('Profit and Loss Report').
    """
    _name = "report.cyllo_accounting.report_profit_n_loss"
    _description = "Report Cyllo Accounting Report PNL"
    _financial_report_method = "get_report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
           Retrieves the necessary data for generating the Profit and Loss report.

           This method is called by the report engine to fetch the required data for rendering the report.

           Args:
               docids (list): A list of document IDs (not used in this case).
               data (dict): A dictionary containing the report parameters, such as the report name, filter data, filter by, periods, comparison, and comparison type.

           Returns:
               dict: A dictionary containing the report data, including the periods, filter by, PDF data, report name, comparison, comparison type, journal names, account names, analytic account names, and the currency symbol.
        """
        report_name = data.get('reportName', "")
        filter_data = data.get('filterData', {})
        filter_by = data.get('filterBy', "")
        periods = data.get('periods', {})
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        journals = [self.env['account.journal'].browse(rec).name for rec in data['filterData']['journal_ids']]
        accounts = [self.env['account.account'].browse(rec).name for rec in data['filterData']['account_ids']]
        account_analytic = [self.env['account.analytic.account'].browse(rec).name for rec in
                            data['filterData']['analytic_ids']]
        pdf_data = getattr(self.env["abstract.financial.report"], self._financial_report_method)(
            comparison, comparison_type, **filter_data)
        currency_symbol = [item['currency_symbol'] for item in pdf_data[0]]
        return {
            'doc_ids': docids,
            'doc_model': 'report.cyllo_accounting.report_profit_n_loss',
            'periods': periods,
            'filter_by': filter_by,
            'pdf_data': pdf_data,
            'report_name': report_name,
            'comparison': comparison,
            'comparison_type': comparison_type,
            'journals': journals,
            'accounts': accounts,
            'account_analytic': account_analytic,
            'data': data,
            'currency_symbol': currency_symbol,
            'self': self
        }

    def get_account_lines(self, filter_key, data):
        """
            Retrieves the account lines based on the specified filter key.

            Args:
                filter_key (str): The key to use for filtering the data.
                data (list): The data to be filtered.

            Returns:
                list: The filtered account lines, or an empty list if all amounts are zero.
        """
        values = [item[filter_key] for item in data[0]]
        should_have_data = any(item[filter_key][2] != 0 for item in data[0])
        return values if should_have_data else []

    def get_account_line(self, account_id, account_lines):
        """
            Retrieves the account line information for the specified account ID.

            Args:
                account_id (str or dict): The ID of the account to retrieve the line for.
                account_lines (list): The full account lines data.

            Returns:
                list: The account line information, or an empty list if the amount is zero.
        """
        account_info = [acc for sublist in account_lines for acc in sublist[0] if acc['id'] == account_id]
        return account_info if any(item['amount'] != 0 for item in account_info) else []

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
            Generate an Excel report based on the provided data.

            Args:
                data (str): JSON string containing filter data.
                response: Response object to write the Excel file to.
                report_name (str): Name of the report.

            Returns:
                None
        """
        symbol = ''
        data = json.loads(data)
        filter_data = data['filterData']
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        report_method = 'get_balance_sheet' if report_name == 'Balance Sheet' else 'get_report'
        pdf_data = getattr(self.env["abstract.financial.report"], report_method)(
            comparison, comparison_type, **filter_data)

        start_date = data['filterData']['start_date'] if \
            data['filterData']['start_date'] else ''
        end_date = data['filterData']['end_date'] if \
            data['filterData']['end_date'] else ''
        journals = [self.env['account.journal'].browse(rec).name for rec in
                    data['filterData']['journal_ids']]
        account_analytic = [
            self.env['account.analytic.account'].browse(rec).name for rec in
            data['filterData']['analytic_ids']]

        account_names = self.env['account.account'].browse(
            data['filterData']['account_ids']).mapped('name') if data['filterData']['account_ids'] else []

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1,
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
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, len(data['periods']) * 2 + 4, 18)
        sheet.write('B1:D1', data['reportName'], head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Comparison', filter_head)
        sheet.write('B5:b4', 'Journal', filter_head)
        sheet.write('B6:b4', 'Account', filter_head)
        sheet.write('B7:b4', 'Analytic Account', filter_head)
        sheet.write('B8:b4', 'Option', filter_head)
        if report_name:
            sheet.merge_range('B1:D1', report_name,
                              head)
        if start_date or end_date:
            sheet.merge_range('C3:G3', f"{start_date} to {end_date}",
                              filter_body)
        if data['filterData']['comparison_value']:
            sheet.merge_range('C4:G4',
                              f"{data['filterData']['comparison_type_value']} : {data['filterData']['comparison_value']}",
                              filter_body)
        if journals:
            display_names = [journal for
                             journal in journals]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C5:G5', display_names_str, filter_body)
        sheet.merge_range('C6:G6', ', '.join(account_names), filter_body)
        if account_analytic:
            account_keys = [account for
                            account in account_analytic]
            account_keys_str = ', '.join(account_keys)
            sheet.merge_range('C7:G7', account_keys_str, filter_body)
        if data['filterData']['target_move']:
            option_keys = list(data['filterData']['target_move'])
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C8:G8', option_keys_str, filter_body)

        period_records = pdf_data[0]
        symbol = period_records[0]['currency_symbol'] if period_records else ''

        def write_period_values(row, key, nested=False):
            """Write one period's value per column for a summary line."""
            for idx, rec in enumerate(period_records):
                value = rec[key][1] if nested else rec[key]
                sheet.write(row, idx + 1, f"{rec['currency_symbol']}{value}")

        def write_account_lines(row, field):
            """Write a section's per-account breakdown, one column per period,
            keeping every row aligned to the same columns."""
            account_lines = self.get_account_lines(field, pdf_data)
            if not account_lines:
                return row
            for account in account_lines[0][0]:
                amounts = self.get_account_line(account['id'], account_lines)
                if not amounts:
                    continue
                row += 1
                sheet.write(row, 0, f"{account['name']}", txt_name)
                for idx, amount in enumerate(amounts):
                    sheet.write(row, idx + 1, f"{symbol}{amount['format_amount']}")
            return row

        if report_name == 'Profit and Loss':
            header_row = 11
            for idx, period in enumerate(data['periods']):
                sheet.write(header_row, idx + 1, period, sub_heading)
                sheet.write(header_row + 1, idx + 1, "Balance", sub_heading)

            row = header_row + 2
            sheet.write(row, 0, 'Net Profit', sub_heading)
            for idx, rec in enumerate(period_records):
                sheet.write(row, idx + 1, f"{rec['currency_symbol']} {rec['total']}")

            row += 1
            sheet.write(row, 0, 'Income', side_heading_sub)
            write_period_values(row, 'total_income')

            row += 1
            sheet.write(row, 0, 'Gross Profit')
            write_period_values(row, 'gross_profit')

            row += 1
            sheet.write(row, 0, 'Operating Income')
            write_period_values(row, 'income', nested=True)
            row = write_account_lines(row, 'income')

            row += 1
            sheet.write(row, 0, 'Cost Of Revenue')
            write_period_values(row, 'expense_direct_cost', nested=True)
            row = write_account_lines(row, 'expense_direct_cost')

            row += 1
            sheet.write(row, 0, 'Other Income')
            write_period_values(row, 'income_other', nested=True)
            row = write_account_lines(row, 'income_other')

            row += 1
            sheet.write(row, 0, 'Total Income', side_heading_sub)
            write_period_values(row, 'total_income')

            row += 1
            sheet.write(row, 0, 'Expenses', side_heading_sub)
            write_period_values(row, 'total_expense')

            row += 1
            sheet.write(row, 0, 'Expenses')
            write_period_values(row, 'expense', nested=True)
            row = write_account_lines(row, 'expense')

            row += 1
            sheet.write(row, 0, 'Depreciation')
            write_period_values(row, 'expense_depreciation', nested=True)
            row = write_account_lines(row, 'expense_depreciation')

            row += 1
            sheet.write(row, 0, 'Total Expenses', side_heading_sub)
            write_period_values(row, 'total_expense')
        elif report_name == "Balance Sheet":
            header_row = 10
            for idx, period in enumerate(data['periods']):
                sheet.write(header_row, idx + 1, period, sub_heading)
                sheet.write(header_row + 1, idx + 1, "Balance", sub_heading)

            row = 12
            sheet.write(row, 0, 'ASSETS', sub_heading)
            row += 1
            sheet.write(row, 0, 'Current Assets', side_heading_sub)

            row += 1
            sheet.write(row, 0, 'Bank and Cash Accounts')
            write_period_values(row, 'asset_cash', nested=True)
            row = write_account_lines(row, 'asset_cash')

            row += 1
            sheet.write(row, 0, 'Receivables')
            write_period_values(row, 'asset_receivable', nested=True)
            row = write_account_lines(row, 'asset_receivable')

            row += 1
            sheet.write(row, 0, 'Current Assets')
            write_period_values(row, 'asset_current', nested=True)
            row = write_account_lines(row, 'asset_current')

            row += 1
            sheet.write(row, 0, 'Prepayments')
            write_period_values(row, 'asset_prepayments', nested=True)
            row = write_account_lines(row, 'asset_prepayments')

            row += 1
            sheet.write(row, 0, 'Total Current Assets', side_heading_sub)
            write_period_values(row, 'total_current_asset')

            row += 1
            sheet.write(row, 0, 'Plus Fixed Assets')
            write_period_values(row, 'asset_fixed', nested=True)
            row = write_account_lines(row, 'asset_fixed')

            row += 1
            sheet.write(row, 0, 'Plus Non-current Assets')
            write_period_values(row, 'asset_non_current', nested=True)
            row = write_account_lines(row, 'asset_non_current')

            row += 1
            sheet.write(row, 0, 'Total Assets', side_heading_sub)
            write_period_values(row, 'total_assets')

            row += 1
            sheet.write(row, 0, 'LIABILITIES', sub_heading)
            row += 1
            sheet.write(row, 0, 'Current Liabilities', side_heading_sub)

            row += 1
            sheet.write(row, 0, 'Current Liabilities')
            write_period_values(row, 'liability_current', nested=True)
            row = write_account_lines(row, 'liability_current')

            row += 1
            sheet.write(row, 0, 'Payable')
            write_period_values(row, 'liability_payable', nested=True)
            row = write_account_lines(row, 'liability_payable')

            row += 1
            sheet.write(row, 0, 'Credit Card')
            write_period_values(row, 'liability_credit_card', nested=True)
            row = write_account_lines(row, 'liability_credit_card')

            row += 1
            sheet.write(row, 0, 'Total Current Liabilities', side_heading_sub)
            write_period_values(row, 'total_current_liability')

            row += 1
            sheet.write(row, 0, 'Plus Non-current Liabilities')
            write_period_values(row, 'liability_non_current', nested=True)
            row = write_account_lines(row, 'liability_non_current')

            row += 1
            sheet.write(row, 0, 'Total LIABILITIES', side_heading_sub)
            write_period_values(row, 'total_liability')

            row += 1
            sheet.write(row, 0, 'EQUITY', sub_heading)
            row += 1
            sheet.write(row, 0, 'Unallocated Earnings', side_heading_sub)

            row += 1
            sheet.write(row, 0, 'Current Earnings', side_heading_sub)
            write_period_values(row, 'total_earnings')

            row += 1
            sheet.write(row, 0, 'Previous Years Earnings')
            write_period_values(row, 'total_prior_earning')

            row += 1
            sheet.write(row, 0, 'Current Allocated Earnings')
            write_period_values(row, 'equity_unaffected', nested=True)
            row = write_account_lines(row, 'equity_unaffected')

            row += 1
            sheet.write(row, 0, 'Total Unallocated Earnings', side_heading_sub)
            write_period_values(row, 'total_unallocated_earning')

            row += 1
            sheet.write(row, 0, 'Retained Earnings')
            write_period_values(row, 'equity', nested=True)
            row = write_account_lines(row, 'equity')

            row += 1
            sheet.write(row, 0, 'Total EQUITY', side_heading_sub)
            write_period_values(row, 'total_equity')

            row += 1
            sheet.write(row, 0, 'LIABILITIES + EQUITY', side_heading_sub)
            write_period_values(row, 'total_balance')

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
