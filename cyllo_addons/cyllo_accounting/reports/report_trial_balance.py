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


class TBReport(models.AbstractModel):
    """"This class represents the Trial Balance Report."""
    _name = "report.cyllo_accounting.report_trial_balance"
    _description = "Report Cyllo Accounting Report TB"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Get the values required to generate the trial balance report.
        :param docids: List of document IDs.
        :param data: Additional data for report generation.
        :return: Dictionary containing data for report generation.
        """
        report_name = data.get('reportName', "")
        filter_data = data.get('filterData', {})
        filter_by = data.get('filterBy', "")
        periods = data.get('periods', {})
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        journals = [self.env['account.journal'].browse(rec).name for rec in data['filterData']['journal_ids']]
        account_analytic = [self.env['account.analytic.account'].browse(rec).name for rec in
                            data['filterData']['analytic_ids']]
        pdf_data = self.env["trial.balance.report"].get_report(comparison, comparison_type, **filter_data)
        return {
            'doc_ids': docids,
            'doc_model': 'report.cyllo_accounting.report_trial_balance',
            'periods': periods,
            'filter_by': filter_by,
            'options': data['filterData']['options'],
            'pdf_data': pdf_data,
            'report_name': report_name,
            'comparison': comparison,
            'comparison_type': comparison_type,
            'journals': journals,
            'account_analytic': account_analytic,
            'data': data,
            'total_common_data': pdf_data[-1],
            'total_data': pdf_data[-2],
        }

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
        Generate an Excel report based on the provided data.
        :param data: JSON data containing filter information.
        :param response: HTTP response object to write the Excel data.
        :param report_name: Name of the report.
        """
        data = json.loads(data)
        xlsx_data = self.env["trial.balance.report"].get_report(data['filterData']['comparison_value'],
                                                                data['filterData']['comparison_type_value'],
                                                                **data['filterData'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = data['filterData']['start_date'] if \
            data['filterData']['start_date'] else ''
        end_date = data['filterData']['end_date'] if \
            data['filterData']['end_date'] else ''
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True,
             'bg_color': '#999999'})
        sheet = workbook.add_worksheet()
        journals = [self.env['account.journal'].browse(rec).name for rec in
                    data['filterData']['journal_ids']]
        account_analytic = [
            self.env['account.analytic.account'].browse(rec).name for rec in
            data['filterData']['analytic_ids']]
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, len(data['periods']) * 2 + 4, 18)
        col = 0
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Comparison', filter_head)
        sheet.write('B5:b4', 'Journal', filter_head)
        sheet.write('B6:b4', 'Account', filter_head)
        sheet.write('B7:b4', 'Option', filter_head)
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
        if account_analytic:
            account_keys = [account for
                            account in account_analytic]
            account_keys_str = ', '.join(account_keys)
            sheet.merge_range('C6:G6', account_keys_str, filter_body)
        if data['filterData']['options']:
            option_keys = list(data['filterData']['options'])
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C7:G7', option_keys_str, filter_body)
        sheet.write(9, col, '', sub_heading)
        sheet.merge_range(9, col + 1, 9, col + 2, 'Initial Balance',
                          sub_heading)
        i = 3
        for date_view in data['periods']:
            sheet.merge_range(9, col + i, 9, col + i + 1, date_view,
                              sub_heading)
            i += 2
        sheet.merge_range(9, col + i, 9, col + i + 1, 'End Balance',
                          sub_heading)
        sheet.write(10, col, '', sub_heading)
        sheet.write(10, col + 1, 'Debit', sub_heading)
        sheet.write(10, col + 2, 'Credit', sub_heading)
        i = 3
        for date_views in data['periods']:
            sheet.write(10, col + i, 'Debit', sub_heading)
            i += 1
            sheet.write(10, col + i, 'Credit', sub_heading)
            i += 1
        sheet.write(10, col + i, 'Debit', sub_heading)
        sheet.write(10, col + (i + 1), 'Credit', sub_heading)
        currency_symbol = xlsx_data[1].get('currency_symbol', '')
        currency_position = xlsx_data[1].get('currency_position', 'before')
        if currency_position == 'after':
            num_format_str = f'#,##0.00 "{currency_symbol}"'
        else:
            num_format_str = f'"{currency_symbol}" #,##0.00'

        number_format = workbook.add_format({'num_format': num_format_str})
        total_format = workbook.add_format({'num_format': num_format_str,
                                            'bg_color': '#C0C0C0', 'bold': True})
        total_name = workbook.add_format({'align': 'center', 'bold': True,
                                          'border': 1, 'border_color': 'black', 'bg_color': '#C0C0C0'})
        if xlsx_data:
            if report_name == 'Trial Balance':
                row = 11
                for move_line in xlsx_data[0]:
                    sheet.write(row, col, move_line['account']['name'],
                                side_heading_sub)
                    sheet.write(row, col + 1, move_line['initial_data']['debit'],
                                number_format)
                    sheet.write(row, col + 2,
                                move_line['initial_data']['credit'], number_format)
                    j = 3
                    if data['filterData']['comparison_value']:
                        number_of_periods = data['filterData']['comparison_value']
                        for num in str(number_of_periods):
                            for val in move_line['values']:
                                sheet.write(row, col + j, val[
                                    'debit'],
                                            number_format)
                                sheet.write(row, col + j + 1, val[
                                    'credit'],
                                            number_format)
                                j += 2
                            break
                    sheet.write(row, col + j, move_line['end_data']['debit'],
                                number_format)
                    sheet.write(row, col + j + 1,
                                move_line['end_data']['credit'], number_format)
                    row += 1
                sheet.write(row, col, 'Total',
                            total_name)
                sheet.write(row, col + 1, xlsx_data[-1]['initial_debit_sum'], total_format)
                sheet.write(row, col + 2, xlsx_data[-1]['initial_credit_sum'], total_format)
                col = 3
                if xlsx_data[-2]:
                    for num in xlsx_data[-2]:
                        sheet.write(row, col,
                                    num['debit'], total_format)
                        sheet.write(row, col + 1,
                                    num['credit'], total_format)
                        col += 2
                sheet.write(row, col, xlsx_data[-1]['end_debit_sum'], total_format)
                sheet.write(row, col + 1,
                            xlsx_data[-1]['end_credit_sum'], total_format)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
