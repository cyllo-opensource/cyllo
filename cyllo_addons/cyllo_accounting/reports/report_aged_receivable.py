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


class ReportAgedReceivable(models.AbstractModel):
    """Model for generating the Aged Receivable Report."""
    _name = 'report.cyllo_accounting.aged_receivable'
    _description = 'Aged Receivable Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generates report values for the Aged Receivable Report.
           :param list docids: The IDs of the documents.
           :param dict data: The data for generating report data .
           :return: Dictionary containing report values.
           :rtype: dict
       """
        filter_kwargs = {
            'partners': data['partners'],
            'date': data['date'],
            'company_ids': data['company_ids'],
            'is_report': True
        }
        move_lines = self.env['aged.payable.receivable.report'].get_report(data['account_type'],
                                                                           **filter_kwargs)
        return {
            'filter_partners': len(data['partners']),
            'date': data['date'],
            'report_name': data['report_name'],
            **move_lines
        }

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """Generates an XLSX report for the Aged Receivable Report.
           :param str data: The report data in JSON format.
           :param response: The HTTP response object.
           :param str report_name: The name of the report.
       """
        data = json.loads(data)
        filter_kwargs = {
            'partners': data['partners'],
            'date': data['date'],
            'company_ids': data['company_ids'],
            'is_report': True
        }
        move_lines = self.env['aged.payable.receivable.report'].get_report(data['account_type'],
                                                                           **filter_kwargs)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px', 'border': 1,
             'border_color': 'black'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        sheet.set_row(0, 25)
        sheet.set_column(0, 0, 25)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 4, 15)
        col = 0
        sheet.merge_range('A1:O1', report_name, head)
        sheet.write('B3:B3', 'Date Range', filter_head)
        if data['partners']:
            sheet.write('B4:B4', 'Partners', filter_head)
        sheet.merge_range('C3:G3', f"{data['date']}", filter_body)
        if data['partners']:
            display_names = ', '.join(
                partner.get('name', 'undefined') for partner in move_lines['partners'])
            sheet.merge_range('C4:G4', display_names, filter_body)

        sheet.write(6, col, ' ', sub_heading)
        sheet.write(6, col + 1, 'Invoice Date', sub_heading)
        sheet.write(6, col + 2, 'Amount Currency', sub_heading)
        sheet.write(6, col + 3, 'Currency', sub_heading)
        sheet.merge_range(6, col + 4, 6, col + 5, 'Account',
                          sub_heading)
        sheet.merge_range(6, col + 6, 6, col + 7, 'Expected Date',
                          sub_heading)
        sheet.write(6, col + 8, 'At Date', sub_heading)
        sheet.write(6, col + 9, '1-30', sub_heading)
        sheet.write(6, col + 10, '31-60', sub_heading)
        sheet.write(6, col + 11, '61-90', sub_heading)
        sheet.write(6, col + 12, '91-120', sub_heading)
        sheet.write(6, col + 13, 'Older', sub_heading)
        sheet.write(6, col + 14, 'Total', sub_heading)
        sheet.set_column(col + 8, col + 14, 15)
        if move_lines and move_lines.get('partner_totals'):
            row = 6

            for ml_total in move_lines['partner_totals']:
                row += 1
                sheet.write(row, col, ml_total['partner'], side_heading_sub)
                sheet.write(row, col + 1, ' ', side_heading_sub)
                sheet.write(row, col + 2, ' ', side_heading_sub)
                sheet.write(row, col + 3, ' ', side_heading_sub)
                sheet.merge_range(row, col + 4, row, col + 5, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 6, row, col + 7, ' ',
                                  txt_name)
                sheet.write(row, col + 8,
                            f"{ml_total['currency_id']} {ml_total['diff0_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 9,
                            f"{ml_total['currency_id']} {ml_total['diff1_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 10,
                            f"{ml_total['currency_id']} {ml_total['diff2_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 11,
                            f"{ml_total['currency_id']} {ml_total['diff3_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 12,
                            f"{ml_total['currency_id']} {ml_total['diff4_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 13,
                            f"{ml_total['currency_id']} {ml_total['diff5_sum']}",
                            side_heading_sub)
                sheet.write(row, col + 14,
                            f"{ml_total['currency_id']} {ml_total['sub_total']}",
                            side_heading_sub)
                for move_line in ml_total['move_lines']:
                    row += 1
                    name_str = move_line['move_name']
                    if move_line['name'] and move_line['name'].strip() and move_line['name'] != move_line['move_name']:
                        name_str += ' ' + move_line['name']
                    sheet.write(row, col, name_str, txt_name)
                    sheet.write(row, col + 1, f"{move_line['date']}",
                                txt_name)
                    sheet.write(row, col + 2,
                                f"{move_line['amount_currency_symbol']} {move_line['amount_currency']}",
                                txt_name)
                    sheet.write(row, col + 3, move_line['amount_currency_name'],
                                txt_name)
                    sheet.merge_range(row, col + 4, row, col + 5,
                                      f"{move_line['account_code']} {move_line['account_name']['en_US']}",
                                      txt_name)
                    sheet.merge_range(row, col + 6, row, col + 7,
                                      f"{move_line['date_maturity'] if move_line['date_maturity'] else ''}",
                                      txt_name)
                    sheet.write(row, col + 8,
                                f"{ml_total['currency_id']} {move_line['diff0']}",
                                txt_name)
                    sheet.write(row, col + 9,
                                f"{ml_total['currency_id']} {move_line['diff1']}",
                                txt_name)
                    sheet.write(row, col + 10,
                                f"{ml_total['currency_id']} {move_line['diff2']}",
                                txt_name)
                    sheet.write(row, col + 11,
                                f"{ml_total['currency_id']} {move_line['diff3']}",
                                txt_name)
                    sheet.write(row, col + 12,
                                f"{ml_total['currency_id']} {move_line['diff4']}",
                                txt_name)
                    sheet.write(row, col + 13,
                                f"{ml_total['currency_id']} {move_line['diff5']}",
                                txt_name)
                    sheet.write(row, col + 14, ' ', txt_name)
            sheet.merge_range(row + 1, col, row + 1, col + 7, 'Total',
                              filter_head)
            sheet.write(row + 1, col + 8,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff0_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 9,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff1_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 10,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff2_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 11,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff3_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 12,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff4_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 13,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['diff5_sum']}",
                        filter_head)
            sheet.write(row + 1, col + 14,
                        f"{move_lines['grand_total']['currency']} {move_lines['grand_total']['total']}",
                        filter_head)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
