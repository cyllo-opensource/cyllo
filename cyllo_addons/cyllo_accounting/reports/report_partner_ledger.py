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


class ReportPartnerLedger(models.AbstractModel):
    """Partner ledger report"""
    _name = 'report.cyllo_accounting.partner_ledger'
    _description = 'Partner Ledger Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Function for pdf report"""

        filter_kwargs = {
            'partner_id': data['partner_id'],
            'startDate': data['startDate'],
            'endDate': data['endDate'],
            'parent_state': data['parent_state'],
            'is_report': True,
            'account_type': data['account_type']
        }
        partners = self.env['res.partner'].browse(data['partner_id']).mapped('name') if data['partner_id'] else []
        options = "Posted Entries, Draft Entries" if 'draft' in (data['parent_state'] or []) else "Posted Entries"
        move_lines, partner_idd = self.env['partner.ledger.report'].get_report(**filter_kwargs)

        return {
            'filter_partners': len(data['partner_id']),
            'start_date': data['startDate'],
            'end_date': data['endDate'],
            'report_name': data['report_name'],
            'company': self.env.user.company_id,
            'options': options,
            'account_type': ', '.join(data['account_type']),
            'partners': ', '.join(partners),
            **move_lines
        }

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """Function for the xlsx report"""
        data = json.loads(data)
        filter_kwargs = {
            'partner_id': data['partner_id'],
            'startDate': data['startDate'],
            'endDate': data['endDate'],
            'parent_state': data['parent_state'],
            'account_type': data['account_type'],
            'is_report': True
        }
        partners = self.env['res.partner'].browse(data['partner_id']).mapped('name') if data['partner_id'] else []
        move_lines, partner_idd = self.env['partner.ledger.report'].get_report(**filter_kwargs)
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
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.merge_range('A1:K1', report_name, head)
        sheet.set_row(0, 25)
        sheet.write('C3:C3', 'Date Range', filter_head)
        sheet.merge_range('D3:G3', data['startDate'] + ' - ' + data['endDate'], filter_body)
        sheet.write('C4:C4', 'Partners', filter_head)
        sheet.merge_range('D4:G4', ", ".join(partners), filter_body)
        sheet.write('C5:C5', 'Accounts', filter_head)
        sheet.merge_range('D5:G5', ", ".join(data['account_type']), filter_body)
        sheet.write('C6:C6', 'Options', filter_head)
        option = "Posted Entries, Draft Entries" if 'draft' in (data['parent_state'] or []) else "Posted Entries"
        sheet.merge_range('D6:G6', option, filter_body)

        sheet.write(7, col, ' ', sub_heading)
        sheet.write(7, col + 1, 'Invoice Date', sub_heading)
        sheet.write(7, col + 2, 'JRNL', sub_heading)
        sheet.write(7, col + 3, 'Account', sub_heading)
        sheet.write(7, col + 4, 'Accounting Date', sub_heading)
        sheet.write(7, col + 5, 'Due Date', sub_heading)
        sheet.set_column(5, 10, 16)
        sheet.set_column(4, 4, 20)
        sheet.write(7, col + 6, 'Matching Number', sub_heading)
        sheet.write(7, col + 7, 'Debit', sub_heading)
        sheet.write(7, col + 8, 'Credit', sub_heading)
        sheet.write(7, col + 9, 'Amount In Currency', sub_heading)
        sheet.write(7, col + 10, 'Balance', sub_heading)
        if move_lines and move_lines.get('partner_totals'):
         row = 7
         partner_totals = move_lines['partner_totals']
         for partner_ledger_total in partner_totals:
            row += 1
            sheet.write(row, col, partner_totals[partner_ledger_total]['partner_name'], side_heading_sub)
            sheet.write(row, col + 1, ' ', side_heading_sub)
            sheet.write(row, col + 2, ' ', side_heading_sub)
            sheet.write(row, col + 3, ' ', side_heading_sub)
            sheet.write(row, col + 7,
                        f"{move_lines['currency_id']} {partner_totals[partner_ledger_total]['total_debit']}",
                        side_heading_sub)
            sheet.write(row, col + 8,
                        f"{move_lines['currency_id']} {partner_totals[partner_ledger_total]['total_credit']}",
                        side_heading_sub)
            sheet.write(row, col + 10,
                        f"{move_lines['currency_id']} {round(partner_totals[partner_ledger_total]['total_debit'] - partner_totals[partner_ledger_total]['total_credit'], 2)}",
                        side_heading_sub)
            opening_debit = partner_totals[partner_ledger_total].get('opening_debit', 0.0)
            opening_credit = partner_totals[partner_ledger_total].get('opening_credit', 0.0)
            opening_balance = partner_totals[partner_ledger_total].get('opening_balance', 0.0)
            row += 1
            sheet.merge_range(row, col, row, col + 6, 'Initial Balance', side_heading_sub)
            sheet.write(row, col + 7, f"{move_lines['currency_id']} {opening_debit}", side_heading_sub)
            sheet.write(row, col + 8, f"{move_lines['currency_id']} {opening_credit}", side_heading_sub)
            sheet.write(row, col + 9, ' ', side_heading_sub)
            sheet.write(row, col + 10, f"{move_lines['currency_id']} {opening_balance}", side_heading_sub)
            running_balance = opening_balance
            for move_line in partner_totals[partner_ledger_total]['move_lines']:
                row += 1
                line_date = move_line['date']
                if hasattr(line_date, 'strftime'):
                    line_date = line_date.strftime("%Y-%m-%d")
                sheet.write(row, col, " ",
                            txt_name)
                sheet.write(row, col + 1, move_line['move_name'],
                            txt_name)
                sheet.write(row, col + 2, f"{move_line['jrnl']}",
                            txt_name)
                sheet.write(row, col + 3, move_line['code'],
                            txt_name)
                sheet.write(row, col + 4, f"{line_date}",
                            txt_name)
                sheet.write(row, col + 5,
                            move_line['date_maturity'].strftime("%Y-%m-%d") if move_line['date_maturity'] else '',
                            txt_name)
                sheet.write(row, col + 6, move_line['matching_number'] if move_line['matching_number'] else ' ',
                            txt_name)
                sheet.write(row, col + 7,
                            f"{move_lines['currency_id']} {move_line['debit']}",
                            txt_name)
                sheet.write(row, col + 8,
                            f"{move_lines['currency_id']} {move_line['credit']}",
                            txt_name)
                sheet.write(row, col + 9,
                            f"{move_lines['currency_id']} {move_line['amount_currency']}",
                            txt_name)
                running_balance += move_line['debit'] - move_line['credit']
                sheet.write(row, col + 10, f"{move_lines['currency_id']} {round(running_balance, 2)}", txt_name)
         sheet.merge_range(row + 1, col, row + 1, col + 6, 'Total',
                          filter_head)
         sheet.write(row + 1, col + 7,
                    f"{move_lines['currency_id']} {move_lines['totalDebitSum']}",
                    filter_head)
         sheet.write(row + 1, col + 8,
                    f"{move_lines['currency_id']} {move_lines['totalCreditSum']}",
                    filter_head)
         sheet.write(row + 1, col + 9, "", filter_head)
         sheet.write(row + 1, col + 10,
                    f"{round(move_lines['totalDebitSum'] - move_lines['totalCreditSum'], 2)}",
                    filter_head)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
