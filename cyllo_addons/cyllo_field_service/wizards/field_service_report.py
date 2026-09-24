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

from odoo import _, fields, models
from odoo.tools import date_utils


class FieldServiceReport(models.Model):
    """Class for wizard for reports"""
    _name = 'field.service.report'
    _description = 'Field Service Report'

    filter = fields.Selection(selection=[('customer_wise', 'Customer wise'),
                                         ('state_wise', 'State wise'),
                                         ('sale_order_wise',
                                          'Sale Order Wise')],
                              default="customer_wise",
                              help="Field to choose filter of report")
    group_by = fields.Selection(
        selection=[('state', 'State wise'), ('priority', 'Priority'),
                   ('company_id', 'Company wise'),
                   ('skill_category_id', 'Skill Category wise'),
                   ('sale_order_id', 'Sale Order Wise'), ('none', 'None')],
        default="state", help="Field to choose filter of report", )
    partner_ids = fields.Many2many('res.partner', string="Choose customer",
                                   help="Field to choose customer for report")
    sale_order_ids = fields.Many2many('sale.order', string="Choose Sale Orders",
                                      help="Field to choose sale orders for report")
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submit', 'Submitted'),
                   ('assigned', 'Assigned'),
                   ('in_progress', 'In Progress'), ('completed', 'Completed')],
        default="draft",
        help="field to specify state of report")
    from_date = fields.Date(help="Field to choose start date of report")
    to_date = fields.Date(help="Field to end date filter of report")

    def action_print(self):
        """Function to print pdf report"""
        if self.from_date and self.to_date and self.from_date > self.to_date:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Provide valid dates"),
                    'type': 'warning',
                },
            }
        details = self.env[
            'report.cyllo_field_service.report_field_service_request_xlsx']._get_report_values(
            [], {
                'context': {'active_id': self.id}})
        data = {
            'form': self.read()[0],
            'fs_requests': details['datas'],
            'group_option': details['group_option']
        }
        report = self.env.ref(
            'cyllo_field_service.report_field_service_request_pdf')
        if self.from_date and self.to_date:
            report.name = _('Field Service Report - %s To %s') % (
                self.from_date, self.to_date)
        return self.env.ref(
            'cyllo_field_service.report_field_service_request_pdf').report_action(
            None, data=data)

    def action_xlsx_print(self):
        """ Function to print xlsx report"""
        if self.from_date and self.to_date and self.from_date > self.to_date:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Provide valid dates"),
                    'type': 'warning',
                },
            }
        data = self.env[
            'report.cyllo_field_service.report_field_service_request_xlsx']._get_report_values(
            [], {
                'context': {'active_id': self.id}})
        report_name = _('Field Service Request Report')
        date_range = ''
        if self.from_date and self.to_date:
            date_range = ' - %s To %s' % (self.from_date, self.to_date)
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'field.service.report',
                'options': json.dumps(data, default=date_utils.json_default),
                'output_format': 'xlsx',
                'report_name': report_name + date_range,
            },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        """ Function to print xlsx report on certain design"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        bold = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_color': 'black'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px',
             'font_color': 'black'})
        txt = workbook.add_format(
            {'font_size': '10px', 'align': 'center', 'font_color': 'black'})
        sheet.merge_range('G2:P2', "Field Service Request Report", head)
        json_object = json.loads(data)
        if json_object['filter'] == "state_wise":
            sheet.merge_range('C3:D3', "State :", txt)
            sheet.merge_range('E3:F3', json_object['state'], txt)
        if json_object['start_date']:
            sheet.merge_range('C4:D4', "Start Date :", txt)
            sheet.merge_range('E4:F4', json_object['start_date'], txt)
        if json_object['end_date']:
            sheet.merge_range('C5:D5', "End Date :", txt)
            sheet.merge_range('E5:F5', json_object['end_date'], txt)
        index = 1
        col = 0
        row = 8
        sheet.write('C6', 'SL NO', bold)
        sheet.merge_range('D6:E6', 'Name', bold)
        sheet.merge_range('F6:I6', 'Partner', bold)
        sheet.merge_range('J6:M6', 'Skill Category', bold)
        sheet.merge_range('N6:P6', 'Deadline Date', bold)
        sheet.merge_range('Q6:R6', 'Sale Order', bold)
        sheet.write('S6', 'State', bold)
        if json_object['group_by'] == 'none':
            for request in json_object['datas']:
                sheet.write(row, col + 2, index, txt)
                sheet.merge_range(row, col + 3, row, col + 4,request['name'], txt)
                sheet.merge_range(row, col + 5, row, col + 8,request['partner_name'], txt)
                sheet.merge_range(row, col + 9, row, col + 12,request['category_name'], txt)
                sheet.merge_range(row, col + 13, row, col + 15, request['date_deadline'] or '', txt)
                sheet.merge_range(row, col + 16, row, col + 17,request['sale_order_name'] or '', txt)
                sheet.write(row, col + 18,request['state'], txt)
                index += 1
                row += 1
        else:
            for group in json_object['group_option']:
                if json_object['datas']:
                    sheet.merge_range(row, col, row, col + 1, group[1], bold)
                    row+=1
                for request in json_object['datas']:
                    if json_object['group_by'] == 'sale_order_id':
                        if request['sale_order_name'] == group[1]:
                            sheet.write(row, col + 2, index, txt)
                            sheet.merge_range(row, col + 3, row, col + 4,
                                              request['name'], txt)
                            sheet.merge_range(row, col + 5, row, col + 8,
                                              request['partner_name'], txt)
                            sheet.merge_range(row, col + 9, row, col + 12,
                                              request['category_name'], txt)
                            sheet.merge_range(row, col + 13, row, col + 15,
                                              request['date_deadline'], txt)
                            sheet.merge_range(row, col + 16, row, col + 17,
                                              request['sale_order_name'], txt)
                            sheet.write(row, col + 18, request['state'], txt)
                            index = index + 1
                            row = row + 1
                    elif request[json_object['group_by']] == group[0]:
                        sheet.write(row, col + 2, index, txt)
                        sheet.merge_range(row, col + 3, row, col + 4,
                                          request['name'], txt)
                        sheet.merge_range(row, col + 5, row, col + 8,
                                          request['partner_name'], txt)
                        sheet.merge_range(row, col + 9, row, col + 12,
                                          request['category_name'], txt)
                        sheet.merge_range(row, col + 13, row, col + 15,
                                          request['date_deadline'], txt)
                        sheet.merge_range(row, col + 16, row, col + 17,
                                          request['sale_order_name'], txt)
                        sheet.write(row, col + 18, request['state'], txt)
                        index = index + 1
                        row = row + 1
        sheet.merge_range(row, col, row, col + 1, "", bold)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
