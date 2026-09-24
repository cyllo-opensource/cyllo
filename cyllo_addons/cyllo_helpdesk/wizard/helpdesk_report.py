# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
import io
import json
from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
from odoo.tools import html2plaintext


class HelpDeskReport(models.TransientModel):
    _name = "helpdesk.report"
    _description = "HelpDesk Report"

    start_date = fields.Date(string="Start Date",
                             default=lambda self: fields.Date.today().replace(day=1),
                             required=True)
    end_date = fields.Date(string="End Date",
                           default=fields.Date.today,
                           required=True)
    category_ids = fields.Many2many('helpdesk.category', string="Category",
                                    help="Choose a category")
    customer_ids = fields.Many2many('res.partner', string="Customer",
                                    help="Choose a customer")
    team_ids = fields.Many2many('helpdesk.team', string="Team",
                                help="Choose a team")
    current_date = fields.Date(default=fields.Date.today)

    @staticmethod
    def _add_in_filter(query, params, column, records):
        """Append 'AND column IN (%s, %s, ...)' for a non-empty recordset."""
        if not records:
            return query
        query += " AND %s IN (%s)" % (
            column, ", ".join(["%s"] * len(records)))
        params.extend(records.ids)
        return query

    def get_helpdesk_ticket(self):
        query = """select helpdesk_ticket.id, helpdesk_ticket.name, helpdesk_category.name as 
                    category, res_partner.name as customer,
                    helpdesk_stage.name as stage, helpdesk_team.name as team, 
                    helpdesk_ticket.date, helpdesk_ticket.description from 
                    helpdesk_ticket left join helpdesk_category on 
                    helpdesk_ticket.category_id = helpdesk_category.id 
                    left join res_partner on 
                    helpdesk_ticket.customer_id = res_partner.id 
                    left join helpdesk_stage on 
                    helpdesk_ticket.stage_id = helpdesk_stage.id 
                    left join helpdesk_team on 
                    helpdesk_ticket.team_id = helpdesk_team.id WHERE 1=1
         """
        return query

    def action_generate_pdf(self):
        """Prints PDF report on clicking the button"""
        query = self.get_helpdesk_ticket()
        params = []
        query += " AND helpdesk_ticket.company_id = %s"
        params.append(self.env.company.id)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.category_id", self.category_ids)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.customer_id", self.customer_ids)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.team_id", self.team_ids)
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        if self.start_date:
            query += """ AND helpdesk_ticket.date >= %s"""
            params.append(self.start_date)
        if self.end_date:
            query += """ AND helpdesk_ticket.date < %s"""
            params.append(self.end_date + datetime.timedelta(days=1))
        cr_ = self._cr
        cr_.execute(query, params)
        helpdesk_ticket_data = self._cr.dictfetchall()
        data = {
            'customer': ', '.join([customer.name for customer in self.customer_ids]),
            'category': ', '.join([category.name for category in self.category_ids]),
            'team': ', '.join([team.name for team in self.team_ids]),
            'date_start': self.start_date,
            'date_end': self.end_date,
            'current_date': self.current_date,
            'helpdesk_ticket_data': helpdesk_ticket_data
        }
        return self.env.ref(
            'cyllo_helpdesk.action_report_helpdesk_ticket'). \
            report_action(None, data=data)

    def action_generate_xlsx(self):
        query = self.get_helpdesk_ticket()
        params = []
        query += " AND helpdesk_ticket.company_id = %s"
        params.append(self.env.company.id)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.category_id", self.category_ids)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.customer_id", self.customer_ids)
        query = self._add_in_filter(
            query, params, "helpdesk_ticket.team_id", self.team_ids)
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        if self.start_date:
            query += """ AND helpdesk_ticket.date >= %s"""
            params.append(self.start_date)
        if self.end_date:
            query += """ AND helpdesk_ticket.date < %s"""
            params.append(self.end_date + datetime.timedelta(days=1))
        cr_ = self._cr
        cr_.execute(query, params)
        helpdesk_ticket_data = self._cr.dictfetchall()
        data = {
            'customer': ', '.join([customer.name for customer in self.customer_ids]),
            'category': ', '.join([category.name for category in self.category_ids]),
            'team': ', '.join([team.name for team in self.team_ids]),
            'start_date': self.start_date,
            'end_date': self.end_date,
            'current_date': self.current_date,
            'helpdesk_ticket_data': helpdesk_ticket_data,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'helpdesk.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Helpdesk Report',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        data = json.loads(data)
        from_date = data['start_date']
        to_date = data['end_date']
        current_date = data['current_date']
        helpdesk_ticket_data = data['helpdesk_ticket_data']
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({'bold': True, 'align': 'center'})
        header_style = workbook.add_format({'bold': True})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})
        row = 4
        if from_date:
            sheet.write(row, 0, 'From Date :  ' + from_date, header_style)
            row += 1
            if to_date:
                sheet.write(row, 0, 'To date :  ' + to_date, header_style)
                row += 1
        else:
            sheet.write(row, 0, 'Date :  ' + current_date, header_style)
            row += 1
        row += 1
        column = 0
        sheet.merge_range('A2:I3', 'HELPDESK TICKET REPORT', head)
        sheet.write(row, column, 'Sl.no', header)
        column += 1
        sheet.write(row, column, 'Helpdesk Ticket Name', header)
        column += 1
        sheet.write(row, column, 'Customer', header)
        column += 1
        sheet.write(row, column, 'Category', header)
        column += 1
        sheet.write(row, column, 'Stage', header)
        column += 1
        sheet.write(row, column, 'Team', header)
        column += 1
        sheet.write(row, column, 'Date', header)
        column += 1
        sheet.write(row, column, 'Description', header)
        column += 1
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 20)
        sheet.set_column(2, 2, 20)
        sheet.set_column(3, 3, 20)
        sheet.set_column(4, 4, 20)
        sheet.set_column(6, 6, 20)
        sheet.set_column(7, 7, 20)
        sheet.set_column(8, 8, 20)
        row += 1
        number = 1
        for data in helpdesk_ticket_data:
            sheet.write(row, 0, number)
            sheet.write(row, 1, data['name'])
            sheet.write(row, 2, data['customer'])
            sheet.write(row, 3, data['category'])
            sheet.write(row, 4, data['stage'])
            sheet.write(row, 5, data['team'])
            sheet.write(row, 6, str(data['date']))
            sheet.write(row, 7, html2plaintext(data['description'] or ""))
            number += 1
            row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
