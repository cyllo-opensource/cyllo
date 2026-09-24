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
import json
from datetime import datetime
from io import BytesIO

import xlsxwriter
from odoo import api, fields, models


class CommissionReport(models.Model):
    """Detailed report of salesperson / sales-team who all receives Commissions"""
    _name = 'commission.report'
    _description = "Detailed report of salesperson / sales-team who all receives Commissions"

    plan_id = fields.Many2one('commission.plan', string='Commission Plan',
                              ondelete='cascade',
                              readonly=True)
    user_id = fields.Many2one('res.users', string='Sales Person', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team',
                              related='plan_id.team_id', store=True)
    type = fields.Selection('commission.plan', related='plan_id.type',
                            store=True)
    period_id = fields.Many2one('commission.plan.frequency',
                                string='Period',
                                readonly=True)
    period_name = fields.Char(related='period_id.name', string='Period',
                              store=True)
    target_amount = fields.Monetary(string='Target Amount', readonly=True)
    achieve_amount = fields.Monetary(string='Achieved Amount', readonly=True)
    achieve_rate = fields.Float(string='Achieved Rate(%)', readonly=True)
    commission_amount = fields.Monetary(string='Commission', readonly=True)
    frequency = fields.Selection('commission.plan',
                                 related='plan_id.frequency', store=True)
    date_from = fields.Date(related='period_id.date_from', string='From',
                            store=True)
    date_to = fields.Date(related='period_id.date_to', string='To',
                          store=True)
    date = fields.Date(string='Date', readonly=True)
    order_id = fields.Many2one('sale.order', string='Source', readonly=True)
    order_ids = fields.Many2many('sale.order',
                                 relation='commission_report_orders_rel',
                                 column1='report_id',
                                 column2='order_id', string='Orders',
                                 readonly=True)
    orderline_ids = fields.Many2many('sale.order.line',
                                     relation='commission_report_lines_rel',
                                     column1='report_id',
                                     column2='line_id', string='Order Lines',
                                     readonly=True, )
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda
                                     self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)

    @api.model
    def get_dashboard_data(self):
        """Pass data to the Dashboard"""
        self = self.sudo()
        company_id = self.env.company
        currency_id = company_id.currency_id

        user_id = self.env.user.id
        is_manager = self.env.user.has_group('sales_team.group_sale_manager')
        user_access = [{'id': user_id, '_is_manager': is_manager}]

        plans = self.env['commission.plan'].search([
            ('company_id', '=', company_id.id), ('state', '=', 'approved')
        ])
        commissions = self.env['commission.report'].search([
            ('company_id', '=', company_id.id),
            ('plan_id.state', '=', 'approved')
        ])
        source_orderlines = commissions.mapped('orderline_ids')
        orders = self.env['sale.order'].search([
            ('is_paid', '=', True)
        ])
        partners = self.env['res.partner'].search([])
        crm_leads = self.env['crm.lead']
        leads = crm_leads.search([])
        won_leads = crm_leads.search([
            ('stage_id.is_won', '=', True),
            ('order_ids.is_paid', '=', True)
        ])
        team_members = self.env['crm.team.member'].search(
            [('active', '=', True)])
        salespeople_data = [
            {'id': user.user_id.id, 'name': user.user_id.name} for user in
            team_members
        ]
        unique_salespeople = []
        seen_ids = set()
        for person in salespeople_data:
            if person['id'] not in seen_ids:
                seen_ids.add(person['id'])
                unique_salespeople.append(person)

        teams_data = [
            {'id': team.id, 'name': team.name} for team in
            team_members.mapped('crm_team_id')
        ]
        plan_data = [{
            'id': plan.id,
            'name': plan.name,
            'type': plan.type,
            'start_date': plan.date_from,
            'end_date': plan.date_to,
            'total_commission': plan.total_commission,
            'salespeople': plan.sales_people_user_ids.ids,
        } for plan in plans]
        commission_data = [
            {
                'id': c.id,
                'plan_id': c.plan_id.id,
                'plan_name': c.plan_id.name,
                'plan_type': c.plan_id.type,
                'period_name': c.period_name,
                'commission_amount': c.commission_amount,
                'salesperson_id': c.user_id.id,
                'salesperson': c.user_id.name,
                'sale_amount': c.achieve_amount,
                'team_id': c.team_id.id,
                'date_from': c.date_from,
                'date_to': c.date_to,
                'sale_order_id': c.order_id.id,
                'sale_order_ids': c.order_ids.ids,
                'sale_orderline_ids': c.orderline_ids.ids,
            }
            for c in commissions
        ]
        order_data = [
            {
                'id': order.id,
                'name': order.name,
                'customer_id': order.partner_id.id,
                'amount': order.amount_untaxed,
                'date': order.order_date,
                'user': order.user_id.name,
                'team': order.team_id.name,
                'user_id': order.user_id.id,
                'team_id': order.team_id.id,
            }
            for order in orders
        ]
        team_members_data = [
            {
                'id': member.id,
                'user_id': member.user_id.id,
                'name': member.user_id.name,
                'team_id': member.crm_team_id.id,
                'team_name': member.crm_team_id.name,
            }
            for member in team_members
        ]
        orderline_data = [{
            'id': line.id,
            'order_id': line.order_id.id,
            'date': line.order_id.order_date,
            'product_id': line.product_id.id,
            'product_name': line.product_id.name,
            'qty': line.qty_invoiced,
            'amount': line.price_subtotal_latest,
            'user_id': line.order_id.user_id.id,
            'team_id': line.order_id.team_id.id,
            'team_name': line.order_id.team_id.name,
        } for line in source_orderlines]

        customers = [{
            "id": partner.id,
            "name": partner.name,
            "create_date": partner.create_date,
            'user_id': partner.user_id.id,
            'team_id': partner.team_id.id,
        } for partner in partners]

        won_opportunities = [{'id': lead.id,
                              'stage_update_date': lead.date_last_stage_update,
                              'user_id': lead.user_id.id,
                              'team_id': lead.team_id.id,
                              } for lead in won_leads]
        opportunities = [{'id': lead.id,
                          'stage_update_date': lead.date_last_stage_update,
                          'user_id': lead.user_id.id,
                          'team_id': lead.team_id.id,
                          } for lead in leads]

        view_contribution_id = self.env.ref(
            "cyllo_commission.view_contribution_commission_report_tree").id
        view_target_id = self.env.ref(
            "cyllo_commission.view_target_commission_report_tree").id

        return {
            'access': user_access,
            'plans': plan_data,
            'commissions': commission_data,
            'currency': currency_id.name,
            'currency_symbol': currency_id.symbol,
            'symbol_position': currency_id.position,
            'salespeople': unique_salespeople,
            'teams': teams_data,
            'sale_orders': order_data,
            'team_members': team_members_data,
            'orderlines': orderline_data,
            'customers': customers,
            'won_opportunities': won_opportunities,
            'opportunities': opportunities,
            'view_ids': {
                'contribution': view_contribution_id,
                'target': view_target_id,
            },
        }

    @api.model
    def get_xlsx_report(self, data, response):
        """Generate an XLSX report for commissions"""
        if isinstance(data, str):
            data = json.loads(data)

        commissions = data.get('commissions', [])
        date_from = data.get('filters', {}).get('date_from', '')
        date_to = data.get('filters', {}).get('date_to', '')
        summary = data.get('summary', {})

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Commission Report')
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 20,
            'font_color': '#1f4e79',
            'bg_color': '#f8f9fa'
        })
        subtitle_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12,
            'font_color': '#495057',
            'italic': True
        })
        summary_label_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2c5aa0',
            'font_color': 'white',
            'border': 1,
            'border_color': '#1a4480',
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 11
        })
        summary_value_format = workbook.add_format({
            'bold': True,
            'bg_color': '#e8f1ff',
            'border': 1,
            'border_color': '#1a4480',
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 11,
            'num_format': '#,##0.00'
        })
        summary_count_format = workbook.add_format({
            'bold': True,
            'bg_color': '#e8f1ff',
            'border': 1,
            'border_color': '#1a4480',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2c5aa0',
            'font_color': 'white',
            'border': 1,
            'border_color': '#1a4480',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10
        })
        data_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'valign': 'vcenter',
            'font_size': 10
        })
        center_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10
        })
        money_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 10
        })
        alt_data_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'bg_color': '#f8f9fa',
            'valign': 'vcenter',
            'font_size': 10
        })
        alt_center_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'bg_color': '#f8f9fa',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10
        })
        alt_money_format = workbook.add_format({
            'border': 1,
            'border_color': '#dee2e6',
            'bg_color': '#f8f9fa',
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'font_size': 10
        })
        leaderboard_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16,
            'font_color': '#155724',
            'bg_color': '#d4edda',
            'border': 2,
            'border_color': '#155724'
        })
        leaderboard_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#28a745',
            'font_color': 'white',
            'border': 1,
            'border_color': '#155724',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10
        })
        column_widths = [3, 10, 22, 18, 15, 18, 16, 18, 20]
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        sheet.set_row(2, 30)
        sheet.merge_range('B3:I3', 'COMMISSION REPORT', title_format)
        sheet.set_row(3, 20)
        sheet.merge_range('B4:I4', f'Report Period: {date_from} to {date_to}',
                          subtitle_format)
        summary_start_row = 6
        section_title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'font_color': '#2c5aa0',
            'align': 'left'
        })
        sheet.write(summary_start_row, 1, 'Executive Summary',
                    section_title_format)
        summary_start_row += 2
        sheet.write(summary_start_row, 1, 'Total Sales', summary_label_format)
        sheet.write_number(summary_start_row, 2, summary.get('total_sales', 0),
                           summary_value_format)
        sheet.write(summary_start_row + 1, 1, 'Total Commission',
                    summary_label_format)
        sheet.write_number(summary_start_row + 1, 2,
                           summary.get('total_commissions', 0),
                           summary_value_format)
        sheet.write(summary_start_row + 2, 1, 'Active Sales Reps',
                    summary_label_format)
        sheet.write_number(summary_start_row + 2, 2,
                           summary.get('total_reps', 0), summary_count_format)
        sheet.write(summary_start_row + 3, 1, 'Active Plans',
                    summary_label_format)
        sheet.write(summary_start_row + 3, 2,
                    f"{summary.get('contributions', 0)} Contribution, {summary.get('targets', 0)} Target",
                    summary_count_format)
        table_start_row = summary_start_row + 6
        sheet.write(table_start_row, 1, 'Detailed Commission Breakdown',
                    section_title_format)
        table_start_row += 2
        headers = ['Sl.No', 'Salesperson', 'Plan', 'Plan Type', 'Period',
                   'Sale Amount', 'Commission Amount']
        for col, header in enumerate(headers):
            sheet.write(table_start_row, col + 1, header, header_format)
        for idx, c in enumerate(commissions, start=1):
            row = table_start_row + idx
            is_even = idx % 2 == 0
            row_data_format = alt_data_format if is_even else data_format
            row_center_format = alt_center_format if is_even else center_format
            row_money_format = alt_money_format if is_even else money_format
            sheet.write(row, 1, idx, row_center_format)
            sheet.write(row, 2, c.get('salesperson', ''), row_data_format)
            sheet.write(row, 3, c.get('plan_name', ''), row_data_format)
            sheet.write(row, 4, c.get('plan_type', ''), row_center_format)
            sheet.write(row, 5, c.get('period_name', ''), row_center_format)
            sheet.write_number(row, 6, c.get('sale_amount', 0.0),
                               row_money_format)
            sheet.write_number(row, 7, c.get('commission_amount', 0.0),
                               row_money_format)
        leaderboard_data = data.get('leaderboardData', [])  # No limit
        leaderboard_start_row = table_start_row + len(commissions) + 4
        sheet.set_row(leaderboard_start_row, 25)
        sheet.merge_range(leaderboard_start_row, 1, leaderboard_start_row, 7,
                          '🏆 LEADERBOARD - TOP PERFORMERS 🏆',
                          leaderboard_title_format)
        headers = ['Rank', 'Name', 'Total Sales', 'Total Commission']
        for col, header in enumerate(headers):
            sheet.write(leaderboard_start_row + 2, col + 2, header,
                        leaderboard_header_format)
        for idx, l in enumerate(leaderboard_data, start=1):
            row = leaderboard_start_row + 2 + idx
            rank = l.get('rank', idx)
            is_even = idx % 2 == 0
            row_data_format = alt_data_format if is_even else data_format
            row_center_format = alt_center_format if is_even else center_format
            row_money_format = alt_money_format if is_even else money_format
            sheet.write(row, 2, rank, row_center_format)
            sheet.write(row, 3, l.get('name', ''), row_data_format)
            sheet.write_number(row, 4, l.get('sale', 0), row_money_format)
            sheet.write_number(row, 5, l.get('commission', 0), row_money_format)
        footer_row = leaderboard_start_row + len(leaderboard_data) + 5
        footer_format = workbook.add_format({
            'align': 'center',
            'font_size': 9,
            'italic': True,
            'font_color': '#6c757d'
        })
        sheet.merge_range(footer_row, 1, footer_row, 7,
                          f'Report generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
                          footer_format)
        workbook.close()
        response.stream.write(output.getvalue())
        output.close()
