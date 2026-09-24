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
import base64
import calendar
import io
from datetime import timedelta

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils, json


class BudgetBudget(models.Model):
    """ Model used to store budgets, perform budget related functions """
    _name = 'budget.budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Budget Management'

    name = fields.Char(string='Budget Name', help='Give a name to the budget',
                       required=True)
    responsible_id = fields.Many2one(
        'res.users', string='Responsible Person', help="the responsible person",
        default=lambda self: self.env.uid, readonly=True)
    period_type = fields.Selection(
        selection=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'),
                   ('year', 'Year')], help='Choose the period')
    start_date = fields.Date(
        string='From', default=fields.datetime.today(),
        help='choose the starting date', tracking=True, required=True)
    end_date = fields.Date(
        string='To', compute='_compute_end_date', store=True, readonly=False,
        tracking=True, help="add the end date of budget management",
        required=True)
    budget_line_ids = fields.One2many(
        'budget.lines', 'budget_id', help="connect with model budget lines")
    description = fields.Html(help="add the description")
    last_updated = fields.Datetime(readonly=True, tracking=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirm', 'Confirmed'),
                   ('approve', 'Approved'), ('cancel', 'Cancelled'),
                   ('reject', 'Rejected'), ('expire', 'Expired')],
        default='draft', help="state of the budget management", tracking=True)
    stage = fields.Selection(
        selection=[('success', 'Success'), ('fail', 'Failed')],
        help="stages of the budget management", tracking=True)
    due_date = fields.Date(
        help='Due date of the budget if any payments are pending')
    company_id = fields.Many2one('res.company', 'Company', readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 help='Name of the company of the user')
    active = fields.Boolean(default=True)
    compute_me = fields.Boolean(compute='_compute_compute_me')
    success_rate = fields.Float(string='Success Rate', default=1,
                                help='Determines the stage of the budget '
                                     'checking Achievement and SuccessRates')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)", self.name)
        return super().copy(default=default)

    @api.depends('start_date', 'period_type')
    def _compute_end_date(self):
        """Compute the end date of the budget period based on the start date,
         period flag, and period type."""
        for record in self:
            if record.period_type == 'day':
                record.end_date = record.start_date
            elif record.period_type == 'week':
                record.end_date = record.start_date + timedelta(6)
            elif record.period_type == 'month':
                record.end_date = record.start_date + timedelta(
                    calendar.monthrange(record.start_date.year,
                                        record.start_date.month)[1] - 1)
            elif record.period_type == 'year':
                record.end_date = record.start_date + timedelta(
                    sum(calendar.monthrange(record.start_date.year, month)[1]
                        for month in range(1, 13)) - 1)
            else:
                record.end_date = False
            record.due_date = record.end_date

    @api.depends('budget_line_ids', 'success_rate')
    def _compute_compute_me(self):
        """Compute The Achievement and Practical amount When the Budget is
         Opened"""
        for record in self:
            if record.budget_line_ids:
                record.action_compute_budget()
            record.compute_me = True

    def action_compute_budget(self):
        """
          This method calculates the budget for each line in the budget lines
          of the current budget object.
          calculates the practical amount and achievement for each line,and
          sets the stage of each line based on the achievement. It also
          calculates the total achievement for all lines and sets the stage of
          the budget.
          """
        self.last_updated = fields.datetime.now()
        if self.budget_line_ids and self.start_date and self.end_date:
            total = 0
            for line in self.budget_line_ids:
                if line.analytic_account_id:
                    if line.include_child:
                        analytic_accounts = line.analytic_account_id.analytic_account_ids.ids
                        analytic_accounts.append(line.analytic_account_id.id)
                        if line.analytic_account_id.analytic_account_ids:
                            for record in line.analytic_account_id.analytic_account_ids:
                                child_analytic_line = self.env[
                                    'budget.lines.configuration'].search(
                                    [('budget_line_id', '=', line.id),
                                     ('analytic_account_id', '=', record.id)])
                                child_analytic_line_moves = self.env[
                                    'account.analytic.line'].search(
                                    [('date', '>=', line.start_date),
                                     ('date', '<=', line.end_date),
                                     ('account_id', '=',
                                      child_analytic_line.analytic_account_id.id)])
                                if line.account_ids:
                                    child_analytic_line.practical_amount = sum(
                                        child_analytic_line_moves.filtered(
                                            lambda
                                                rec: rec.general_account_id.id in line.account_ids.ids).mapped(
                                            'amount'))
                                else:
                                    child_analytic_line.practical_amount = sum(
                                        child_analytic_line_moves.mapped(
                                            'amount'))
                                if line.start_date <= fields.date.today() <= line.end_date:
                                    child_analytic_line_theoretical_amount = (
                                                                                     child_analytic_line.amount / int(
                                                                                 (
                                                                                         line.end_date - line.start_date).days + 1)) * (
                                                                                     int(
                                                                                         (
                                                                                                 fields.date.today() - line.start_date).days) + 1)
                                elif line.end_date < fields.date.today():
                                    child_analytic_line_theoretical_amount = child_analytic_line.amount
                                else:
                                    child_analytic_line_theoretical_amount = 0
                                child_analytic_line.achievement = (
                                        child_analytic_line.practical_amount / child_analytic_line_theoretical_amount) \
                                    if child_analytic_line_theoretical_amount else False
                    else:
                        analytic_accounts = [line.analytic_account_id.id]
                    line_moves = self.env['account.analytic.line'].search(
                        [('date', '>=', line.start_date),
                         ('date', '<=', line.end_date),
                         ('account_id', 'in', analytic_accounts)])
                    if line.account_ids:
                        line.practical_amount = sum(line_moves.filtered(
                            lambda
                                rec: rec.general_account_id.id in line.account_ids.ids).mapped(
                            'amount'))
                    else:
                        line.practical_amount = sum(line_moves.mapped('amount'))
                else:
                    accounts = line.account_ids.ids
                    line.practical_amount = -sum(
                        self.env['account.move.line'].search(
                            [('date', '>=', line.start_date),
                             ('date', '<=', line.end_date),
                             ('account_id', 'in', accounts)]).mapped('balance'))
                if line.practical_amount and line.theoretical_amount:
                    line.achievement = line.practical_amount / line.theoretical_amount
                else:
                    line.achievement = 0
                if line.achievement >= self.success_rate:
                    line.stage = 'success' if line.budget_type == 'earn' else 'fail'
                else:
                    line.stage = 'fail' if line.budget_type == 'earn' else 'success'
                total += line.achievement * 100 if line.budget_type == 'earn' else -line.achievement * 100
            success_count = sum(
                1 for line in self.budget_line_ids if line.stage == 'success')
            total_lines = len(self.budget_line_ids)
            self.stage = 'success' if success_count > total_lines / 2 else 'fail'

    def action_confirm_budget(self):
        """ This method is used to confirm the budget. It changes the state of
         the budget to `confirm`."""
        self.state = 'confirm'

    def action_approve_budget(self):
        """ This method changes the state of the budget to `approve`."""
        self.state = 'approve'
        mail_template = self.env.ref(
            'cyllo_budget_management.mail_template_budget_approve_mail')
        email_values = {'email_to': self.responsible_id.partner_id.email, }
        data_id = self.pdf_as_mail_attachment(self.id)
        mail_template.attachment_ids = [fields.Command.set([data_id.id])]
        self.env['mail.template'].browse(mail_template.id).send_mail(
            self.id, email_values=email_values, force_send=True)
        mail_template.attachment_ids = [fields.Command.unlink(data_id.id)]

    def action_cancel_budget(self):
        """ This method changes the state of the budget to `cancelled`."""
        self.state = 'cancel'
        mail_template = self.env.ref(
            'cyllo_budget_management.mail_template_budget_cancel_mail')
        email_values = {'email_to': self.responsible_id.partner_id.email, }
        data_id = self.pdf_as_mail_attachment(self.id)
        mail_template.attachment_ids = [fields.Command.set([data_id.id])]
        self.env['mail.template'].browse(mail_template.id).send_mail(
            self.id, email_values=email_values, force_send=True)
        mail_template.attachment_ids = [fields.Command.unlink(data_id.id)]

    def action_reset_to_draft(self):
        """ This method changes the state of the budget to `draft`."""
        self.state = 'draft'

    def action_reject_budget(self):
        """This method the budget rejected, and state changes to 'Rejected'"""
        self.state = 'reject'

    @api.constrains('due_date')
    def _check_due_date(self):
        """Constraint to check whether the due date is greater  than end date"""
        if self.due_date and self.due_date < self.end_date:
            raise ValidationError(
                'Due date should be Greater than or Equal to End Date')

    def pdf_as_mail_attachment(self, res_id):
        """This method creates pdf attachment"""
        budget_report_template_id = self.env[
            'ir.actions.report']._render_qweb_pdf(
            report_ref='cyllo_budget_management.report_budget_pdf',
            data=None, res_ids=res_id)
        data_record = base64.b64encode(budget_report_template_id[0])
        ir_values = {
            'name': "Budget Report",
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        return data_id

    def budget_delay_mail(self):
        """Scheduled action for sending mail reminding the low rate of budget
         achievement"""
        low_achievement_budget = self.search([('stage', '=', 'fail'),
                                              ('state', '=', 'approve')])
        for line in low_achievement_budget:
            line.action_compute_budget()
            if line.stage == 'fail' and line.due_date == fields.date.today() + timedelta(
                    2):
                data_id = self.pdf_as_mail_attachment(line.id)
                mail_template = self.env.ref(
                    'cyllo_budget_management.mail_template_budget_delay_mail')
                email_values = {
                    'email_to': line.responsible_id.partner_id.email, }
                mail_template.attachment_ids = [
                    fields.Command.set([data_id.id])]
                self.env['mail.template'].browse(mail_template.id).send_mail(
                    line.id, email_values=email_values, force_send=True)
                mail_template.attachment_ids = [
                    fields.Command.unlink(data_id.id)]
        expired_budgets = self.search(
            [('state', 'not in', ['expire', 'cancel']),
             ('end_date', '<', fields.date.today())])
        for line in expired_budgets:
            line.state = 'expire'
            mail_template = self.env.ref(
                'cyllo_budget_management.mail_template_budget_expiry_mail')
            email_values = {'email_to': self.responsible_id.partner_id.email, }
            data_id = self.pdf_as_mail_attachment(line.id)
            mail_template.attachment_ids = [fields.Command.set([data_id.id])]
            self.env['mail.template'].browse(mail_template.id).send_mail(
                line.id, email_values=email_values, force_send=True)
            mail_template.attachment_ids = [fields.Command.unlink(data_id.id)]

    def action_generate_xlsx(self):
        """ This method generates an Excel report for the budget lines
        associated with the current budget object. """
        budget = self.browse(self.env.context.get('active_id'))
        budget_lines = []
        for record in budget.budget_line_ids:
            records = {
                'analytic': record.analytic_account_id.name,
                'budget_type': record.budget_type,
                'start_date': record.start_date,
                'end_date': record.end_date,
                'planned_amount': record.planned_amount,
                'achievement': record.achievement,
                'include_child': record.include_child
            }
            configure_lines = []
            for line in self.env['budget.lines.configuration'].search(
                    [('budget_line_id', '=', record.id)]):
                lines = {
                    'analytic': line.analytic_account_id.name,
                    'amount': line.amount,
                    'achievement': line.achievement,
                }
                configure_lines.append(lines)
            records['sub_categories'] = configure_lines
            budget_lines.append(records)
        data = {
            'name': budget.name,
            'start_date': budget.start_date,
            'end_date': budget.end_date,
            'budget_lines': budget_lines
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'budget.budget',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Excel Report',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        """This method generates an Excel report from the provided data."""
        parsed_data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head_class = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '18px'})
        thin_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        sub_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '12px'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '24px'})
        txt = workbook.add_format({'font_size': '11px', 'align': 'center'})
        sheet.merge_range('C9:H10', 'BUDGET MANAGEMENT REPORT', head)
        sheet.write('C12', 'Name', thin_head)
        sheet.write('C13', 'Start Date', thin_head)
        sheet.write('G13', 'End Date', thin_head)
        sheet.merge_range('C14:H14', 'Budget Report', head_class)
        sheet.write('C16', 'Analytic Account', thin_head)
        sheet.write('D16', 'Budget Type', thin_head)
        sheet.write('E16', 'Start Date', thin_head)
        sheet.write('F16', 'End Date', thin_head)
        sheet.write('G16', 'Planned Amount', thin_head)
        sheet.write('H16', 'Achievement', thin_head)
        sheet.set_column(2, 7, 23)
        sheet.set_row(11, 24)
        sheet.set_row(12, 24)
        sheet.set_row(13, 24)
        sheet.set_row(15, 24)
        sheet.write(11, 3, parsed_data.get('name'), txt)
        sheet.write(12, 3, parsed_data.get('start_date'), txt)
        sheet.write(12, 7, parsed_data.get('end_date'), txt)
        row = 16
        for budget_lines in parsed_data['budget_lines']:
            sheet.write(row, 2, budget_lines.get('analytic'), txt)
            sheet.write(row, 3, budget_lines.get('budget_type'), txt)
            sheet.write(row, 4, budget_lines.get('start_date'), txt)
            sheet.write(row, 5, budget_lines.get('end_date'), txt)
            sheet.write(row, 6, budget_lines.get('planned_amount'), txt)
            sheet.write(row, 7, budget_lines.get('achievement'), txt)
            if budget_lines.get('include_child'):
                row = row + 2
                sheet.write('F' + str(row), 'Analytic', sub_head)
                sheet.write('G' + str(row), 'Planned Amount', sub_head)
                sheet.write('H' + str(row), 'Achievement', sub_head)
                for sub_categories in budget_lines.get('sub_categories'):
                    sheet.write(row, 5, sub_categories.get('analytic'), txt)
                    sheet.write(row, 6, sub_categories.get('amount'), txt)
                    sheet.write(row, 7, sub_categories.get('achievement'), txt)
                    row += 1
            row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        """ Constraints to check Start date and End Date Validations"""
        if self.end_date < self.start_date:
            raise ValidationError('End Date Should be Greater Than  Start date')

    @api.onchange('end_date')
    def _onchange_end_date(self):
        """ Change the Start date When End Date changes according to The chosen period type"""
        if self.period_type == 'day':
            self.start_date = self.end_date
        elif self.period_type == 'week':
            self.start_date = self.end_date - timedelta(6)
        elif self.period_type == 'month':
            end_date_month = timedelta(
                calendar.monthrange(self.end_date.year, self.end_date.month)[1])
            if timedelta(self.end_date.day) < end_date_month:
                end_date_previous_month = (
                        self.end_date.replace(day=1) - timedelta(1)).month
                self.start_date = self.end_date - timedelta(
                    calendar.monthrange(self.end_date.year,
                                        end_date_previous_month)[1] - 1)
            else:
                self.start_date = self.end_date - timedelta(
                    calendar.monthrange(self.end_date.year,
                                        self.end_date.month)[1] - 1)
        elif self.period_type == 'year':
            self.start_date = self.end_date - timedelta(
                sum(calendar.monthrange(self.end_date.year - 1, month)[1] for
                    month in range(1, 13)))
        self.due_date = self.end_date

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date(self):
        """Onchange function to change the Budget Line dates"""
        if self.budget_line_ids and self.start_date and self.end_date:
            for line in self.budget_line_ids:
                line.start_date = self.start_date
                line.end_date = self.end_date
