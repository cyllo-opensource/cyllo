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
""" This module helps to add the sms details in the wizard and send SMS. """
from __future__ import print_function
import clicksend_client
import json
import requests
from twilio.rest import Client
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SendSms(models.TransientModel):
    """
    Class for the wizard to send SMS.
    Methods:
        action_send_sms():
            Button action to send SMS.
    """
    _name = 'send.sms'
    _description = 'Wizard to send SMS'
    _check_company_auto = True

    sms_id = fields.Many2one('sms.gateway.config', string='Provider',
                             domain="[('is_active','=',True)]",
                             required=True,
                             help='Gateway record with credentials')
    sms_to = fields.Char(string='Phone Number', required=True,
                         help='Enter the number to send the SMS')
    text = fields.Text(required=True, help='Enter the text for the SMS')
    partner_ids = fields.Many2many('res.partner', string="Customer",
                                   help="Select customer.")
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 help='Active company.')

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """
            Function to add recipient data for sms_to field
        """
        partners = []
        for partner_id in self.partner_ids:
            phone_number = partner_id.mobile or partner_id.phone
            partners.append(
                phone_number or f"No phone number for {partner_id.name}")
        self.sms_to = ', '.join(partners)

    def action_send_sms(self):
        """
        Function to send SMS using different SMS gateway
        """
        if self.sms_id.name == 'TWILIO':
            for number in self.sms_to.split(','):
                if number:
                    try:
                        client = Client(self.sms_id.twilio_account_sid,
                                        self.sms_id.twilio_auth_token)
                        web_base_url = self.env[
                            'ir.config_parameter'].sudo().get_param(
                            'web.base.url')
                        status_callback_url = web_base_url + '/twilio/status' if web_base_url else None
                        response = client.messages.create(body=self.text,
                                                          from_=self.sms_id.twilio_phone_number,
                                                          status_callback=status_callback_url,
                                                          to=number)
                        response_status = response.status if response else None
                        response_sid = response.sid if response.sid else None
                        self.sudo().create_sms_history(response_status,
                                                       response_sid)
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {'title': _('Success'),
                                       'type': 'success',
                                       'message': _(
                                           'Message has successfully sent.'),
                                       'next': {
                                           'type': 'ir.actions.act_window_close'},
                                       }}
                    except Exception as e:
                        self.create_sms_history(e, None)
                        return {'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {'title': _('Error'),
                                           'type': 'warning',
                                           'message': e,
                                           'next': {
                                               'type': 'ir.actions.act_window_close'}}}
        elif self.sms_id.name == 'D7':
            for number in self.sms_to.split(','):
                web_base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                status_callback_url = f"{web_base_url}/D7/status" if web_base_url else None
                if number:
                    payload = json.dumps({
                        "messages": [{"channel": "sms", "recipients": [number],
                                      "content": self.text, "msg_type": "text",
                                      "data_coding": "text"}],
                        "message_globals": {
                            "originator": "SignOTP",
                            "report_url": status_callback_url}})
                    headers = {'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'Authorization': 'Bearer ' + self.sms_id.d7_api}
                    try:
                        response = requests.request("POST",
                                                    "https://api.d7networks.com/messages/v1/send",
                                                    headers=headers,
                                                    data=payload)
                        if response.status_code == 200:
                            data = response.json()
                            sid = data.get('request_id', None)
                            status = data.get('status')
                            self.create_sms_history(status, sid)
                            return {'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'title': _('Success'),
                                        'type': 'success',
                                        'message': _(
                                            'Message request successfully accepted.'),
                                        'next': {
                                            'type': 'ir.actions.act_window_close'}}}
                        else:
                            sid = response.json().get('request_id', None)
                            status = response.json()["detail"][0][
                                'code'] if isinstance(response.json()["detail"],
                                                      list) \
                                else response.json()["detail"]['code']
                            self.create_sms_history(status, sid)
                            return {'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'title': _('Error'),
                                        'type': 'warning',
                                        'message': status,
                                        'next': {
                                            'type': 'ir.actions.act_window_close'}}}
                    except Exception as e:
                        raise ValidationError(_(e))
        elif self.sms_id.name == 'CLICK SEND':
            # Set up configuration
            configuration = clicksend_client.Configuration()
            configuration.username = self.sms_id.click_send_email
            configuration.password = self.sms_id.click_send_api
            api_instance = clicksend_client.SMSApi(
                clicksend_client.ApiClient(configuration))
            api_instance_delivery = clicksend_client.SMSDeliveryReceiptRulesApi(
                clicksend_client.ApiClient(configuration))
            # Prepare SMS messages
            sms_messages = [
                clicksend_client.SmsMessage(source="php", body=self.text,
                                            to=number.strip(),
                                            schedule=1436874701)
                for number in self.sms_to.split(',') if number.strip()
            ]
            # Create the message collection
            sms_message_collection = clicksend_client.SmsMessageCollection(
                messages=sms_messages)
            try:
                # Send SMS messages
                response = api_instance.sms_send_post(sms_message_collection)
                response = literal_eval(response.replace("'", "\""))
                message_info = response.get('data', {}).get('messages', [{}])[0]
                status = message_info.get('status')
                message_id = message_info.get('message_id')
                # Log SMS history and check the message status
                self.create_sms_history(status, message_id)
                if status not in ["SUCCESS", "CREATED"]:
                    return self._display_notification(_('Warning'), status,
                                                      'warning')
                # Define callback URL
                web_base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                status_callback_url = f"{web_base_url}/clicksend/status" if web_base_url else None
                # Check existing receipt rules
                if self.sms_id.clicksend_receipt_rule_id:
                    api_response_view_rules = api_instance_delivery.sms_delivery_receipt_automations_get(
                        page=1, limit=20)
                    api_response_view_rules = literal_eval(
                        api_response_view_rules)
                    receipt_report_rules = api_response_view_rules.get('data',
                                                                       {}).get(
                        'data', [])
                    # Check if a matching rule exists
                    rule_matched = any(rule[
                                           'receipt_rule_id'] == self.sms_id.clicksend_receipt_rule_id
                                       for rule in receipt_report_rules)
                    if not rule_matched:
                        self._create_receipt_rule(api_instance_delivery,
                                                  status_callback_url)
                else:
                    # Create new receipt rule if none exists
                    self._create_receipt_rule(api_instance_delivery,
                                              status_callback_url)
                # Success notification
                return self._display_notification(_('Success'),
                                                  _('Successfully authenticated.'),
                                                  'success')
            except Exception as e:
                error_message = getattr(e, 'reason', str(e))
                self.create_sms_history(error_message, None)
                return self._display_notification(_('Error'), error_message,
                                                  'warning')

    def _display_notification(self, title, message, type_='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'type': type_,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    def _create_receipt_rule(self, api_instance_delivery, callback_url):
        delivery_receipt_rule = clicksend_client.DeliveryReceiptRule(
            rule_name="Cyllo Report Rule",
            match_type=1,
            action="URL",
            action_address=callback_url,
            enabled=1
        )
        api_response_delivery = api_instance_delivery.sms_delivery_receipt_automation_post(
            delivery_receipt_rule)
        api_response_delivery = literal_eval(api_response_delivery)
        receipt_rule_id = api_response_delivery.get('data', {}).get(
            'receipt_rule_id')
        self.sms_id.clicksend_receipt_rule_id = receipt_rule_id if receipt_rule_id else None

    def create_sms_history(self, response, sid):
        """Create an entry in the SMS history with details of the SMS
        """
        status = response
        self.env['sms.history'].sudo().create({
            'user_id': self.env.user.id,
            'sms_gateway_id': self.sms_id.id,
            'sms_mobile': self.sms_to,
            'sms_text': self.text,
            'sid': sid,
            'sms_status': status
        })
