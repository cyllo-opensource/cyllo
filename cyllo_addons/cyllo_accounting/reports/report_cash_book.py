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


class CashBookReport(models.AbstractModel):
    """
    Abstract model for generating a Cash Book Report.

    This model defines the structure and behavior of the Cash Book Report.

    Attributes:
        _name (str): The technical name of the model ('report.cyllo_accounting.report_cash_book').
        _description (str): A brief description of the model ('Cyllo Cash Book Report').
    """
    _name = "report.cyllo_accounting.report_cash_book"
    _description = "Cyllo Cash Book Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Bank Book Report"""
        filter_kwargs = {
            'partners': data['partners'],
            'startDate': data['startDate'],
            'endDate': data['endDate'],
            'accounts': data['accounts'],
            'parent_state': data['parent_state'],
            'company_ids': data.get('company_ids', []),
            'is_report': True
        }
        move_lines = self.env['bank.cash.book.report'].get_report(data['account_type'],
                                                                  **filter_kwargs)
        return {
            'filter_partners': len(data['partners']),
            'startDate': data['startDate'],
            'endDate': data['endDate'],
            'partners': self.env['res.partner'].browse(data['partners']),
            'account_ids': self.env['account.account'].browse(data['accounts']),
            'parent_state': data['parent_state'],
            'move_lines': move_lines
        }

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        data = json.loads(data)
        filter_kwargs = {
            'partners': data['partners'],
            'startDate': data['startDate'],
            'endDate': data['endDate'],
            'account_type': data['account_type'],
            'accounts': data['accounts'],
            'parent_state': data['parent_state'],
            'company_ids': data.get('company_ids', []),
            'is_report': True
        }
        move_lines = self.env['bank.cash.book.report'].get_report(data['account_type'],
                                                                  **filter_kwargs)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        date_start = filter_kwargs['startDate'] if \
            filter_kwargs['startDate'] else ''
        date_end = filter_kwargs['endDate'] if \
            filter_kwargs['endDate'] else ''
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
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.merge_range('A1:O1', report_name, head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Partners', filter_head)
        sheet.write('B5:b4', 'Accounts', filter_head)
        sheet.write('B6:b4', 'Options', filter_head)
        if date_start or date_end:
            sheet.merge_range('C3:G3', f"{date_start} to {date_end}",
                              filter_body)
        if filter_kwargs['partners']:
            partner_names = self.env['res.partner'].browse(filter_kwargs['partners'])
            partner_display_names = [partner.name for partner in partner_names]
            display_names_str = ', '.join(partner_display_names)
            sheet.merge_range('C4:G4', display_names_str, filter_body)
        if filter_kwargs['accounts']:
            filter_accounts = self.env['account.account'].browse(filter_kwargs['accounts'])
            account_names = [account.name for account in filter_accounts]
            account_names_str = ', '.join(account_names)
            sheet.merge_range('C5:G5', account_names_str, filter_body)
        if filter_kwargs['parent_state']:
            option_keys = filter_kwargs['parent_state']
            formatted_states = ', '.join([f'{state.capitalize()}' for state in option_keys])
            option_keys_str = f"Includes {formatted_states} Entries"
            sheet.merge_range('C6:G6', option_keys_str, filter_body)
        if move_lines:
            sheet.write(8, col, ' ', sub_heading)
            sheet.merge_range('B9:C9', 'Journal', sub_heading)
            sheet.merge_range('D9:E9', 'Partner', sub_heading)
            sheet.merge_range('F9:G9', 'Ref', sub_heading)
            sheet.merge_range('H9:I9', 'Accounting Date', sub_heading)
            sheet.merge_range('J9:K9', 'Entry Label', sub_heading)
            sheet.merge_range('L9:M9', 'Debit', sub_heading)
            sheet.merge_range('N9:O9', 'Credit', sub_heading)
            sheet.merge_range('P9:Q9', 'Balance', sub_heading)
            row = 8
            for move_line in move_lines['account_entries']:
                row += 1
                sheet.write(row, col, move_line, txt_name)
                sheet.merge_range(row, col + 1, row, col + 2, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 3, row, col + 4, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 5, row, col + 6, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 7, row, col + 8, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 9, row, col + 10, ' ',
                                  txt_name)
                sheet.merge_range(row, col + 11, row, col + 12,
                                  f"{move_lines['currency_id']} {move_lines['account_entries'][move_line][1]}",
                                  txt_name)
                sheet.merge_range(row, col + 13, row, col + 14,
                                  f"{move_lines['currency_id']} {move_lines['account_entries'][move_line][2]}",
                                  txt_name)
                sheet.merge_range(row, col + 15, row, col + 16,
                                  f"{move_lines['currency_id']} {move_lines['account_entries'][move_line][3]}",
                                  txt_name)
                for rec in move_lines['account_entries'][move_line][0]:
                    row += 1
                    if rec['partner_id']:
                        partner = rec['partner_id'][1]
                    else:
                        partner = ' '
                    if rec['ref']:
                        ref = rec['ref']
                    else:
                        ref = ' '
                    sheet.write(row, col, rec['move_name'], txt_name)
                    sheet.merge_range(row, col + 1, row, col + 2,
                                      rec['journal_id'][1],
                                      txt_name)
                    sheet.merge_range(row, col + 3, row, col + 4, partner,
                                      txt_name)
                    sheet.merge_range(row, col + 5, row, col + 6,
                                      ref, txt_name)
                    sheet.merge_range(row, col + 7, row, col + 8,
                                      rec['date'].strftime('%Y-%m-%d'),
                                      txt_name)
                    sheet.merge_range(row, col + 9, row, col + 10,
                                      rec['name'],
                                      txt_name)
                    sheet.merge_range(row, col + 11, row, col + 12,
                                      f"{move_lines['currency_id']} {rec['debit']}", txt_name)
                    sheet.merge_range(row, col + 13, row, col + 14,
                                      f"{move_lines['currency_id']} {rec['credit']}", txt_name)
                    sheet.merge_range(row, col + 15, row, col + 16, ' ',
                                      txt_name)
            sheet.merge_range(row + 1, col, row + 1, col + 10, 'Total',
                              filter_head)
            sheet.merge_range(row + 1, col + 11, row + 1, col + 12,
                              f"{move_lines['currency_id']} {move_lines['total_debit']}",
                              filter_head)
            sheet.merge_range(row + 1, col + 13, row + 1, col + 14,
                              f"{move_lines['currency_id']} {move_lines['total_credit']}",
                              filter_head)
            sheet.merge_range(row + 1, col + 15, row + 1, col + 16,
                              f"{move_lines['currency_id']} {float(move_lines['total_debit']) - float(move_lines['total_credit'])}",
                              filter_head)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
