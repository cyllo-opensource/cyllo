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

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConsolidationPeriod(models.Model):
    """This model represents specific periods within a consolidation chart,
    defining the start and end dates for consolidation activities."""
    _name = 'consolidation.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Period'
    _rec_name = 'chart_id'
    _check_company_auto = True

    chart_id = fields.Many2one(
        'consolidation.chart', string='Consolidation', required=True,
        help='Associated consolidation chart')
    currency_id = fields.Many2one(
        'res.currency', string="Target Currency",
        related="chart_id.currency_id", store=True,
        help='Target currency for this consolidation period')
    state = fields.Selection(
        [('draft', 'Draft'), ('closed', 'Closed')], default='draft',
        string='Status', required=True,
        help='Status of the consolidation period')
    start_date = fields.Date(required=True,
                             help='Start date of the consolidation period')
    end_date = fields.Date(required=True,
                           help='End date of the consolidation period')
    account_ids_count = fields.Integer(
        string='Account Count', compute='_compute_account_ids_count',
        help='Count of accounts associated with this consolidation period')
    journal_ids = fields.One2many(
        'consolidation.journal', 'period_id', string="Journals",
        help="Journals associated with this consolidation period")
    journal_ids_count = fields.Integer(
        string='Journal Count', compute='_compute_journal_ids_count',
        help="Count of journals associated with this consolidation period")
    dates = fields.Char(string='Date', compute='_compute_dates',
                        help='Date representation')
    company_period_ids = fields.One2many(
        'consolidation.company.period', 'period_id',
        help='Linked records from consolidation company periods')
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the record without removing it.")
    total_amount = fields.Monetary(
        string="Total Amount", help="Total amount of consolidation report",
        compute='_compute_total_amount')

    @api.model_create_multi
    def create(self, vals_list):
        """Create method overridden to create Consolidation Periods and
        associated Company Periods.
        :param vals_list: List of dictionaries containing values for creating
        Consolidation Periods.
        :return: Created Consolidation Periods."""
        res = super(ConsolidationPeriod, self).create(vals_list)
        for company_id in res.chart_id.company_ids:
            res.company_period_ids.create({
                'company_id': company_id.id,
                'period_id': res.id,
                'start_date': res.start_date,
                'end_date': res.end_date,
            })
        return res

    @api.depends('start_date', 'end_date')
    def _compute_dates(self):
        """Sets the 'dates' field based on 'start_date' and 'end_date'
        fields"""
        for rec in self:
            if rec.start_date.month == rec.end_date.month and rec.start_date.year == rec.end_date.year:
                rec.dates = rec.start_date.strftime('%b %Y')
            else:
                rec.dates = f"{rec.start_date.strftime('%b %Y')} - {rec.end_date.strftime('%b %Y')}"

    @api.depends('chart_id')
    def _compute_account_ids_count(self):
        """ This method calculates and updates the 'account_ids_count' field
        by retrieving the count of accounts
        linked to the consolidation chart associated with this period."""
        for rec in self:
            count = rec.chart_id.account_ids_count
            rec.account_ids_count = count

    @api.depends('journal_ids')
    def _compute_journal_ids_count(self):
        """This method calculates and updates the 'journal_ids_count' field by
        retrieving the count of journals linked to this consolidation
        period."""
        for rec in self:
            count = len(rec.journal_ids)
            rec.journal_ids_count = count

    @api.depends('journal_ids')
    def _compute_total_amount(self):
        """This method calculates and updates the total_amount field by
        calculating journals balance linked to this consolidation period."""
        for rec in self:
            rec.total_amount = sum(
                rec.journal_ids.journal_line_ids.mapped('balance'))

    def action_close(self):
        """Close the consolidation period."""
        self.write({'state': 'closed'})

    def action_draft(self):
        """Set the consolidation period back to draft."""
        self.write({'state': 'draft'})

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        """Check if the start date is before the end date."""
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be less than End Date")

    def action_open_accounts(self):
        """This action opens a window displaying the accounts associated with
        this consolidation period."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidation Accounts',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.account',
            'target': 'current',
            'domain': [('chart_id', '=', self.chart_id.id)],
            'context': {'default_chart_id': self.chart_id.id},
        }

    def action_state(self):
        """Change the state of the consolidation period."""
        self.write({'state': 'closed' if self.state == 'draft' else 'draft'})

    def action_create_journal(self):
        """Create consolidation journals for the current consolidation
        period."""
        for company_id in self.chart_id.company_ids:
            if company_id.id not in self.company_period_ids.company_id.ids:
                self.company_period_ids.create({
                    'company_id': company_id.id,
                    'period_id': self.id,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                })
            journal_id = self.journal_ids.search([
                ('period_id', '=', self.id),
                ('company_id', '=', company_id.id)])
            if not journal_id:
                journal_id = self.journal_ids.create({
                    'name': f'{company_id.name} Consolidated Journal',
                    'chart_id': self.chart_id.id,
                    'period_id': self.id,
                    'company_id': company_id.id
                })
            else:
                journal_id = self.journal_ids.search(
                    [('period_id', '=', self.id),
                     ('company_id', '=', company_id.id)])
                journal_id.journal_line_ids.unlink()
            for account_id in self.chart_id.account_ids:
                balance = 0
                for account in account_id.account_ids:
                    balance += sum(self.env['account.move.line'].search(
                        [('account_id', '=', account.id),
                         ('company_id', '=', company_id.id),
                         ('date', '>=', self.start_date),
                         ('date', '<=', self.end_date)]).mapped('balance'))
                for company_period_id in self.company_period_ids:
                    if company_id == company_period_id.company_id and company_period_id.consolidation_rate != 100:
                        balance = ((company_period_id.consolidation_rate / 100) * balance)
                if self.chart_id.is_currency_different:
                    company_currency_id = company_id.currency_id
                    target_currency_id = self.currency_id
                    balance = company_currency_id._convert(balance, target_currency_id)
                if account_id.is_invert_sign:
                    balance = -balance
                if self.chart_id.is_invert_sign:
                    balance = -balance
                journal_id.journal_line_ids.create({
                    'journal_id': journal_id.id,
                    'group_id': account_id.group_id.id,
                    'account_id': account_id.id,
                    'balance': balance,
                })

    def action_open_journals(self):
        """Action to open consolidated journals associated with the
        consolidation chart."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidated Journals',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.journal',
            'target': 'current',
            'domain': [('period_id', '=', self.id)],
            'context': {'create': False, 'edit': False},
        }

    @api.model
    def get_filter(self, active_id):
        """Retrieves filter data related to a specific active_id.
        It browses the period_id based on the provided active_id, fetches
        journals associated with the period, and gathers period comparison data
        based on the chart_id of the period."""
        if isinstance(active_id, self.__class__):
            active_id = active_id.id  # Convert model instance to ID
        period_id = self.browse(int(active_id)) if isinstance(active_id, (int, str)) else active_id
        journal = [(journal_id.id, journal_id.name) for journal_id in period_id.journal_ids]
        period_ids = self.env['consolidation.period'].search(
            [('chart_id', '=', period_id.chart_id.id)])
        comparison = [(pid.id, f'{pid.chart_id.name} ({pid.dates})')
                      for pid in period_ids if pid.id != int(active_id) and pid.journal_ids]
        filter_data = {'journal': journal, 'comparison': comparison}
        return filter_data

    @api.model
    def view_report(self, active_id, dictionary):
        """Generate a consolidated report based on the provided active ID.
        Args:
            - active_id (int): ID of the active period.
        Returns:
            - dict: A dictionary containing consolidated report data including
            groups, accounts, child items, and currency symbol."""
        period_id = self.browse(active_id)
        currency_symbol = period_id.currency_id.symbol
        account_ids = self.env['consolidation.account'].search(
            [('chart_id', '=', period_id.chart_id.id)])
        all_group = self.env['consolidation.group'].search(
            [('chart_id', '=', period_id.chart_id.id),
             ('group_id', '=', False)])
        if len(dictionary['selected_group']) > 0:
            group_ids = self.env['consolidation.group'].search(
                [('chart_id', '=', period_id.chart_id.id),
                 ('id', 'in', dictionary['selected_group'])])
        else:
            group_ids = self.env['consolidation.group'].search(
                [('chart_id', '=', period_id.chart_id.id)])
        group, child, accounts, total = [], [], [], []
        company_ids = period_id.journal_ids.company_id
        if dictionary['selected_journal']:
            selected_journal_ids = dictionary['selected_journal']
            company_ids = period_id.journal_ids.filtered(lambda r: r.id in selected_journal_ids).mapped('company_id')
            header = [[f"{company_period.company_id.name} Consolidated Journal",
                       f"Conso Rate: {company_period.consolidation_rate}%"]
                      for company_period in period_id.company_period_ids if company_period.company_id in company_ids]
        elif dictionary['selected_comparison']:
            dictionary['selected_comparison'].extend([active_id])
            period_ids = self.browse(dictionary['selected_comparison'])
            header = [([f'{period_id.chart_id.name}', f' ({period_id.dates})']) for period_id in period_ids]
            for group_id in group_ids:
                list_to_extend = []
                if group_id.group_id:
                    list_to_extend.extend([group_id.group_id.id, group_id.id, group_id.name])
                else:
                    list_to_extend.extend([group_id.id, group_id.name])
                for period_id in period_ids:
                    balance = sum(self.env['consolidation.journal.line'].search([
                        ('group_id', 'in', [group_id.id] + group_id.group_ids.ids
                        if group_id.group_ids else [group_id.id]),
                        ('journal_id', 'in', period_id.journal_ids.ids)]).mapped('balance'))
                    list_to_extend.extend([round(balance,2)])
                group_total = sum(list_to_extend[-len(period_ids):])
                list_to_extend.extend([group_total])
                if group_id.group_id:
                    child.append(list_to_extend)
                else:
                    group.append(list_to_extend)
            for account_id in account_ids:
                val = [account_id.group_id.id, account_id.name]
                total = 0
                for period_id in period_ids:
                    balance = sum(
                        self.env['consolidation.journal.line'].search(
                        [('account_id', '=', account_id.id),
                         ('journal_id', 'in', period_id.journal_ids.ids)]).mapped('balance'))
                    val.append(balance)
                    total += balance
                val.append(total)
                accounts.append(val)
            total_list = [sum(period_id.journal_ids.mapped('total')) for period_id in period_ids]
            total = list(map(lambda x: round(x, 2), total_list))
        else:
            header = [[f"{company_id.name} Consolidated Journal", f"Conso Rate: {company_period.consolidation_rate}%"]
                        for company_id in company_ids
                        for company_period in period_id.company_period_ids.filtered(
                    lambda p: p.company_id == company_id)]
        if period_id.journal_ids and dictionary['selected_comparison'] == []:
            for group_id in group_ids:
                list_to_extend = []
                if group_id.group_id:
                    list_to_extend.extend(
                        [group_id.group_id.id, group_id.id, group_id.name])
                else:
                    list_to_extend.extend([group_id.id, group_id.name])
                for company_id in company_ids:
                    balance = sum(self.env['consolidation.journal.line'].search([
                        ('group_id', 'in', [group_id.id] + group_id.group_ids.ids
                        if group_id.group_ids else [group_id.id]),
                        ('journal_id.company_id', '=', company_id.id),
                        ('journal_id', 'in', period_id.journal_ids.ids)]).mapped('balance'))
                    list_to_extend.extend([round(balance,2)])
                group_total = sum(list_to_extend[-len(company_ids):])
                list_to_extend.extend([round(group_total, 2)])
                if group_id.group_id:
                    child.append(list_to_extend)
                else:
                    group.append(list_to_extend)
            for account_id in account_ids:
                val = [account_id.group_id.id, account_id.name]
                total = 0
                for company_id in company_ids:
                    balance = sum(self.env['consolidation.journal.line'].search([
                        ('account_id', '=', account_id.id),
                        ('journal_id.company_id', '=', company_id.id),
                        ('journal_id', 'in', period_id.journal_ids.ids)]).mapped('balance'))
                    val.append(balance)
                    total += balance
                val.append(round(total, 2))
                accounts.append(val)
            total_list = period_id.journal_ids.filtered(
                lambda rec: rec.company_id in company_ids).mapped('total')
            total = list(map(lambda x: round(x, 2), total_list))
        data = {'group': group, 'all_group': all_group.read(), 'accounts': accounts, 'child': child,
                'symbol': currency_symbol, 'header': header, 'total': total}
        return data

    @api.model
    def get_xlsx_report(self, data, response):
        """Generate an Excel report based on the provided data.
        :param data: The data used to generate the report.
        :type data: str (JSON format)
        :param response: The response object to write the report to.
        :type response: object
        # :param report_name: The name of the report.
        # :type report_name: str
        :return: None"""
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px', 'border': 1,
             'bg_color': '#D3D3D3', 'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px', 'border': 1,
             'bg_color': '#D3D3D3', 'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px', 'border': 1,
             'border_color': 'black'})
        sub_total_body = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '12px', 'border': 1,
             'border_color': 'black'})
        amount_txt = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px', 'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format(
            {'align': 'center', 'font_size': '10px', 'border': 1})
        txt_amount = workbook.add_format(
            {'align': 'center', 'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.merge_range('A2:D2', "Consolidated Balance", head)
        sheet.write('B4:b4', 'Journal', filter_head)
        sheet.write('B5:b4', 'Comparison', filter_head)
        sheet.write('B6:b4', 'Group', filter_head)
        if data['journal']:
            display_names = [journal for journal in data['journal']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C4:G4', display_names_str, filter_body)
        if data['comparison']:
            display_names = [comparison for comparison in data['comparison']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C5:G5', display_names_str, filter_body)
        if data['selected_group_name']:
            display_names = [comparison[0] for comparison in data['selected_group_name']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C6:G6', display_names_str, filter_body)
        col = 0
        if data['data']:
            sheet.merge_range('A9:A10', ' ', sub_heading)
            for header in data['data']['header']:
                col += 1
                sheet.set_column(col, col, 35)
                sheet.write(8, col, header[0], sub_heading)
                sheet.write(9, col, header[1], sub_heading)
            sheet.write(8, col + 1, 'Total', sub_heading)
            sheet.write(9, col + 1, '', sub_heading)
            sheet.set_column(col + 1, col + 1, 20)
            row = 9
            total_row = 0
        if data['data']['group']:
            sub_total = [0] * len(data['data']['group'][0][2:])
            for group in data['data']['group']:
                col = 0
                row += 1
                sheet.write(row, col, group[1], filter_body)
                for index, amount in enumerate(group):
                    if index >= 2:
                        col += 1
                        sheet.write(row, col, amount, amount_txt)
                for child in data['data']['child']:
                    if child[0] == group[0]:
                        row += 1
                        col = 0
                        sheet.write(row, col, child[2], side_heading_sub)
                        for index, amount in enumerate(child):
                            if index >= 3:
                                col += 1
                                sheet.write(row, col, amount, amount_txt)
                        for accounts in data['data']['accounts']:
                            if child[1] == accounts[0]:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts[1], txt_name)
                                for index, amount in enumerate(accounts):
                                    if index >= 2:
                                        col += 1
                                        sheet.write(row, col, amount, txt_amount)
                for accounts in data['data']['accounts']:
                    if group[0] == accounts[0]:
                        row += 1
                        col = 0
                        sheet.write(row, col, accounts[1], txt_name)
                        for index, amount in enumerate(accounts):
                            if index >= 2:
                                col += 1
                                sheet.write(row, col, amount, txt_amount)
                row += 1
                col = 0
                sheet.write(row, col, f'Total {group[1]}', filter_body)
                for index, amount in enumerate(group):
                    if index >= 2:
                        col += 1
                        sheet.write(row, col, amount, amount_txt)
                total_row = row
                for i in range(len(sub_total)):
                    sub_total[i] += group[i + 2]
            col = 0
            sheet.write(total_row + 2, col, 'Total', sub_total_body)
            for amount in sub_total:
                col += 1
                sheet.write(total_row + 2, col, amount, amount_txt)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
