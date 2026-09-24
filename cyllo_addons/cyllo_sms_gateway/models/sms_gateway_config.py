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
from odoo import _, fields, models


class SmsGatewayConfig(models.Model):
    """
    Class to save the user credential details for the SMS gateways.
    """
    _name = 'sms.gateway.config'
    _description = 'SMS Gateway Configuration'
    _check_company_auto = True

    # Disabled D7 SMS provider integration.
    # Reason: D7 requires a verified business account.
    # - Personal accounts are not accepted (unless freelance, but never approved).
    # - Business signup is blocked from cybrosys.info for "security reasons".
    # Hence, code is commented until an alternative provider is finalized.

    name = fields.Char(help="Name of the SMS gateway", readonly=True)
    image_128 = fields.Image(string="Image")
    twilio_account_sid = fields.Char(string='Account SID', company_dependent=True, help='Account SID for Twilio.')
    twilio_auth_token = fields.Char(string='Auth Token', company_dependent=True, help='Auth token for Twilio.')
    twilio_phone_number = fields.Char(string='Twilio Number', company_dependent=True, help='Twilio phone number.')
    # d7_api = fields.Char(string='Api Key', company_dependent=True, help='Generate key from d7 and add here.')
    click_send_email = fields.Char(string="Username", company_dependent=True, help="Enter click send email address.")
    click_send_api = fields.Char(string="Api Key", company_dependent=True, help="Enter click send api key.")
    clicksend_receipt_rule_id = fields.Char('Clicksend Receipt Rule')
    is_active = fields.Boolean(company_dependent=True, string="Active", help="Active gateway")
    company_id = fields.Many2one('res.company', company_dependent=True,
                                 default=lambda self: self.env.company, help='Active company.')

    def action_test_connection(self):
        """
            Open a new window to test the SMS connection.
            :return: Dictionary with action details to open a form view for
            sending SMS.
        """
        return {
            'name': _('Send SMS'),
            'type': 'ir.actions.act_window',
            'res_model': 'send.sms',
            'context': {
                'default_sms_id': self.id,
            },
            'view_mode': 'form',
            'target': 'new'
        }

    def action_activate(self):
        """
        This method sets the 'is_active' flag to True, indicating that the SMS
        gateway configuration is active and ready to use.
        """
        self.company_id = self.env.company.id
        self.is_active = True

    def action_deactivate(self):
        """
        This method deactivates the SMS gateway configuration based on its name.
        Depending on the gateway type ('D7', 'TWILIO', or 'CLICK SEND'),
        it resets specific fields to empty strings and sets the 'is_active'
        flag to False.
        """
        self.company_id = False
        reset_fields = {
            # "D7": ["d7_api"],
            "TWILIO": ["twilio_phone_number", "twilio_account_sid", "twilio_auth_token"],
            "CLICK SEND": ["click_send_api", "click_send_email"]
        }
        if self.name in reset_fields:
            for field in reset_fields[self.name]:
                setattr(self, field, "")
        self.is_active = False
