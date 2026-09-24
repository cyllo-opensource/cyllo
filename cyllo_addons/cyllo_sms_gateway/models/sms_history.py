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
""" This module helps to see the history of all SMSes send. """
from odoo import fields, models


class SmsHistory(models.Model):
    """
    This model stores the details of all the SMS messages that have been
    sent, including the gateway name, date of sending, mobile phone number,
    and SMS text.
    """
    _name = 'sms.history'
    _description = 'SMS History'
    _rec_name = 'sms_mobile'

    sms_gateway_id = fields.Many2one('sms.gateway.config',
                                     string='Gateway', help='The SMS Gateway.', readonly=True)
    sms_date = fields.Datetime(string='Date', default=fields.Datetime.now,
                               readonly=True, help='Date of sending message(current day).')
    sms_mobile = fields.Char(readonly=True, string='Mobile Number', help='Phone Number to send SMS.')
    sms_text = fields.Text(help='The message to be sent.', readonly=True)
    sms_status = fields.Char(string='Status', help='Sms Status', readonly=True)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company, help='Active company.')
    user_id = fields.Many2one('res.users', readonly=True, help="User who send this message")
    sid = fields.Char(string='SID', help='The Unique SMS ID')
