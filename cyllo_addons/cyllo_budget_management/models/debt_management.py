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
from datetime import timedelta

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


class DebtManagement(models.Model):
    """ Model used to store Debt management details, perform debt related
    functions """
    _name = 'debt.management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Debt Management System'
    _rec_name = 'display_name'

    display_name = fields.Char(
        help='display name of document request', default=_('New'), copy=False)
    debt_type = fields.Selection(
        selection=[('lend', 'Lend'), ('borrow', 'Borrow')], required=True,
        help='choose the debt type')
    person_id = fields.Many2one(
        'res.partner', 'Person ',
        help='The person whom you would like to give/take', required=True)
    amount = fields.Monetary(currency_field='currency_id',
                             help='The amount of debt')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    balance_amount = fields.Monetary(
        string='Balance', tracking=True, currency_field='currency_id',
        help='Balance amount', copy=False,readonly=True,compute='_compute_balance_amount')
    date = fields.Date(default=fields.datetime.now(), help='Debt Date')
    payback_period = fields.Selection(
        selection=[('week', 'Week'), ('month', 'Month')],
        help='Choose the payback period')
    payback_date = fields.Date(help='Choose the payback date', required=True)
    returned_or_not = fields.Boolean(
        string='Returned?', readonly=True, tracking=True,
        help='True if completely returned', copy=False)
    partially_returned = fields.Boolean(
        help='True if Partially returned', readonly=True, copy=False)
    returned_date = fields.Date(tracking=True, help='Returned Date', copy=False)
    returned_amount = fields.Monetary(copy=False, readonly=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('lend_borrow', 'Lent/Borrowed'),
                   ('partial_return', 'Partially Returned'),
                   ('return', 'Returned'), ('cancel', 'Cancelled')],
        default='draft', readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 help='Name of the company of the user')

    @api.model_create_multi
    def create(self, vals_list):
        """Super the create function in debt.management to generate sequences"""
        for vals in vals_list:
            if not vals.get('display_name') or vals['display_name'] == _('New'):
                vals['display_name'] = self.env['ir.sequence'].next_by_code(
                    'debt.management') or _('New')
        return super().create(vals_list)

    def action_confirm_debt(self):
        """Confirms the debt and make the payment according to debt type"""
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'debt.payback.wizard',
            'name': 'Payment Confirmation',
            'context': self.env.context,
            'views': [[self.env.ref(
                'cyllo_budget_management.view_debt_payback_wizard_confirm_form').id,
                       'form']],
            'target': 'new'
        }

    def action_cancel_debt(self):
        """Cancel the debt"""
        self.state = 'cancel'

    @api.onchange('payback_period', 'date')
    def _onchange_payback_period(self):
        """Set the payback date according to the payback period"""
        if self.payback_period == 'week':
            self.payback_date = self.date + timedelta(7)
        elif self.payback_period == 'month':
            self.payback_date = self.date + timedelta(30)

    def action_view_payments(self):
        """ Shows The payments related to the debt """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments'),
            'res_model': 'account.payment',
            'domain': [('ref', 'ilike', self.display_name)],
            'views': [[False, 'tree'], [False, 'form']],
        }

    @api.constrains('payback_date')
    def _check_payback_date(self):
        """Constrains for the payback date"""
        if self.payback_date < fields.date.today():
            raise ValidationError(
                'Payback date should be greater than Lent/Borrowed date')

    def payback_mail(self):
        """Scheduled action for sending mail reminding the payback date"""
        records_to_payback = self.search(
            [('state', 'not in', ['draft', 'cancel', 'return']),
             ('payback_date', '!=', False)]).filtered(
            lambda x: x.payback_date == fields.date.today() + timedelta(
                1))  # removed .date() from payback_date.date()
        for record in records_to_payback:
            mail_template = self.env.ref(
                'cyllo_budget_management.mail_template_payback_alert')
            email_values = {'email_to': record.person_id.email}
            mail_template.send_mail(record.id, email_values=email_values,
                                    force_send=True)
            email_values_user = {'email_to': self.env.user.email}
            mail_template.send_mail(record.id, email_values=email_values_user,
                                    force_send=True)

    def action_generate_xlsx(self):
        """Action created for generate xlsx report for debt management"""
        record = self.browse(self.env.context.get('active_id'))
        data = {
            'states': dict(record._fields['state'].selection),
            'state': record.state,
            'person_id': record.person_id.name,
            'amount': record.amount,
            'date': record.date,
            'payback_period': record.payback_period,
            'payback_date': record.payback_date if record.payback_date else False,
            'partially_returned': record.partially_returned,
            'balance_amount': record.balance_amount,
            'returned_or_not': record.returned_or_not,
            'returned_date': record.returned_date if record.returned_date else False,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'debt.management',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Excel Report',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        """Write the values in to the xlsx sheet which fetched """
        parsed_data = json.loads(data)
        status = parsed_data['states']
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '24px'})
        head_class = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '18px'})
        sub_class = workbook.add_format(
            {'align': 'center', 'font_size': '14px'})
        thin_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        txt = workbook.add_format({'font_size': '12px', 'align': 'center'})
        if parsed_data.get('partially_returned'):
            sheet.merge_range('B9:H10', 'DEBT MANAGEMENT REPORT', head)
            sheet.write('B12', 'Debt State', thin_head)
            sheet.merge_range('B13:H13', 'Debt Report', head_class)
            sheet.write('B15', 'Person', thin_head)
            sheet.write('C15', 'Amount', thin_head)
            sheet.write('D15', 'Date', thin_head)
            sheet.write('E15', 'PayBack Period', thin_head)
            sheet.write('F15', 'PayBack Date', thin_head)
            sheet.write('G15', 'Balance To Pay', thin_head)
            sheet.write('H15', 'Returned Date', thin_head)
            sheet.write(11, 2,
                        status[parsed_data.get('state')] if parsed_data.get(
                            'state') else "", sub_class)
            sheet.write(16, 1, parsed_data.get('person_id'), txt)
            sheet.write(16, 2, parsed_data.get('amount'), txt)
            sheet.write(16, 3, parsed_data.get('date'), txt)
            sheet.write(16, 4, parsed_data.get('payback_period'), txt)
            sheet.write(16, 5, parsed_data.get('payback_date'), txt)
            sheet.write(16, 6, parsed_data.get('balance_amount'), txt)
            sheet.write(16, 7, parsed_data.get('returned_date'), txt)
        else:
            sheet.merge_range('B9:G10', 'DEBT MANAGEMENT REPORT', head)
            sheet.write('B12', 'Debt State', thin_head)
            sheet.merge_range('B13:G13', 'Debt Report', head_class)
            sheet.write('B15', 'Person', thin_head)
            sheet.write('C15', 'Amount', thin_head)
            sheet.write('D15', 'Date', thin_head)
            sheet.write('E15', 'PayBack Period', thin_head)
            sheet.write('F15', 'PayBack Date', thin_head)
            sheet.write('G15', 'Returned Date', thin_head)
            sheet.write(11, 2,
                        status[parsed_data.get('state')] if parsed_data.get(
                            'state') else "", sub_class)
            sheet.write(16, 1, parsed_data.get('person_id'), txt)
            sheet.write(16, 2, parsed_data.get('amount'), txt)
            sheet.write(16, 3, parsed_data.get('date'), txt)
            sheet.write(16, 4, parsed_data.get('payback_period'), txt)
            sheet.write(16, 5, parsed_data.get('payback_date'), txt)
            sheet.write(16, 6, parsed_data.get('returned_date'), txt)
        sheet.set_column(1, 8, 22)
        sheet.set_row(11, 24)
        sheet.set_row(12, 24)
        sheet.set_row(14, 24)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
    @api.depends('amount')
    def _compute_balance_amount(self):
        for debt in self:
            debt.balance_amount = debt.amount - debt.returned_amount

