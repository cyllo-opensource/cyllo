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
from odoo import fields, models


class AccountingFollowUpLine(models.Model):
    _name = 'accounting.followup.line'
    _description = 'Accounting Follow Up Line'
    _rec_name = 'title'

    title = fields.Char(string='Title',
                        help='Title for the accounting follow up',
                        required=True)
    due_date = fields.Integer(help='Number of due days for follow ups')
    send_mail = fields.Boolean(
        help='Check the box for sending the reminder via mail')
    mail_template_id = fields.Many2one('mail.template',
                                       string='Mail Template',
                                       help='Choose mail template for follow-up',
                                       domain="[('model', '=', 'res.partner')]",
                                       default=lambda self: self.env.ref(
                                           'cyllo_accounting_follow_up.mail_template_payment_reminder').id)
    company_id = fields.Many2one('res.company', index=True,
                                 default=lambda self: self.env.company)
