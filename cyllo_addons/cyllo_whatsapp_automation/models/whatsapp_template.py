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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests
import json


class WhatsappTemplate(models.Model):
    _inherit = 'whatsapp.template'

    template_type = fields.Selection(
        [('custom', 'Custom'), ('flows', 'Flows')],
        string='Template Type',
        default='custom',
        required=True,
        help="Select the type of template: 'Custom' for custom templates, "
             "or 'Flows' for predefined WhatsApp flows."
    )
    flows_id = fields.Many2one(
        comodel_name='whatsapp.flows',
        string='Flow',
        domain="[('state', '=', 'published')]",
        help="The specific WhatsApp flow this template is associated with.",
    )
    action = fields.Selection(
        [('create_sale_order', 'Create Sale Order'),
         ('create_purchase_order', 'Create Purchase Order'), ],
        string='Action',
        help="Specify the action triggered by the template,"
    )

    def action_create_template(self):
        """
        Create a new WhatsApp template and handle any validation errors.

        This method checks the template's header and its associated fields,
        validates that the last field is binary, and sends the template data
        to the WhatsApp API. If the template creation fails, it handles errors
        and updates the template status accordingly.
        """
        if self.header_type == 'image':
            parts = self.binary_field_path.split('.')
            model = self.model_id.id
            flag = 0
            for part in parts:
                flag += 1
                if model:
                    field = self.env['ir.model.fields'].sudo().search(
                        [('name', '=', part), ('model_id', '=', model)])
                    if field:
                        if flag != len(parts):
                            if field.ttype == 'many2one':
                                model = self.env['ir.model'].sudo().search(
                                    [('model', '=', field.relation)]).id
                            else:
                                model = False
                        else:
                            if field.ttype != 'binary':
                                return {
                                    'type': 'ir.actions.client',
                                    'tag': 'display_notification',
                                    'params': {
                                        'message': _(
                                            'The last field must be binary'),
                                        'type': 'warning',
                                    },
                                }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _('Wrong path'),
                            'type': 'warning',
                        },
                    }
        cloud_token = self.get_whatsapp_account_details['cloud_token']
        account_uid = self.get_whatsapp_account_details['account_uid']
        headers = {'Authorization': f'Bearer {cloud_token}',
                   'Content-Type': 'application/json'}
        components = []
        if self.header_type != 'none':
            components.append(self._create_header_components())
        if self.body:
            components.append(self._create_body_components())
        if self.footer_text:
            footer = {"type": "FOOTER", "text": self.footer_text}
            components.append(footer)
        if self.is_button:
            cta = {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "url",
                        "url": self.button_url,
                        "text": self.button_name
                    },
                ]
            }
            components.append(cta)
        if self.template_type == 'catalogue':
            cta = {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "CATALOG",
                        "text": "View catalog"
                    }
                ]
            }
            components.append(cta)
        if self.flows_id:
            cta = {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "FLOW",
                        "text": self.button_name,
                        "navigate_screen": "SCREEN_ONE",
                        "flow_action": "navigate",
                        "flow_id": self.flows_id.flow_id,
                    },
                ]
            }
            components.append(cta)
        payload = {
            "name": self.template_name,
            "language": self.lang_id.code,
            "category": self.category,
            "components": components
        }
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{account_uid}/message_templates",
            json=payload, headers=headers)
        if response.status_code != 200:
            error = response.json()['error']
            if error['error_subcode'] == 100:
                raise ValidationError(
                    _('Invalid Business Account ID'))
            elif error['code'] == 190:
                raise ValidationError(
                    _('Invalid Access Token'))
            else:
                raise ValidationError(
                    _('%s\n%s\n%s', error['message'], error['error_user_title'],
                      error['error_user_msg']))
        template_response = response.json()
        self.template_uid = template_response.get('id')
        if template_response.get('status'):
            if template_response.get('status') == 'REJECTED':
                self.is_reason_update = True
                self.reason = "Template format is not correct, please check."
            self.state = template_response.get('status').lower()

    def action_send_template(self, record, attachment, partner):
        """
        Send a WhatsApp template message to the specified partners.

        Args:
            record (recordset): The record to be included in the template.
            attachment (recordset): Any attachment to be included in the message.
            partner (recordset): The recipient(s) of the template.

        Raises:
            ValidationError: If an error occurs while sending the template.
        """
        if not record:
            raise ValidationError(_('Record is missed'))
        if self.state != 'approved':
            raise ValidationError(
                _('Please approve the template before sending!'))
        cloud_token = self.get_whatsapp_account_details['cloud_token']
        phone_uid = self.get_whatsapp_account_details['phone_uid']
        headers = {'Authorization': f'Bearer {cloud_token}',
                   'Content-Type': 'application/json'}
        components = []
        for partner in partner:
            if self.header_type != 'none':
                header_values = self._get_header_component(record, attachment,
                                                           partner)
                components.append(header_values['header'])
            if self.body:
                components.append(self._get_body_component(record))
            if self.template_type in 'custom':
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": partner.whatsapp_number,
                    "type": "template",
                    "template": {
                        'name': self.template_name,
                        "language": {"code": self.lang_id.code},
                        "components": components
                    }
                }
            elif self.template_type == 'catalogue':
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": partner.whatsapp_number,
                    "type": "template",
                    "template": {
                        "name": 'cat_two_efa8f85fb06b11ef92261dacc6a38c68',
                        "language": {"code": "en_US"},
                        "components": []
                    }
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": partner.whatsapp_number,
                    "type": "template",
                    "template": {
                        'name': self.template_name,
                        "language": {
                            "code": self.lang_id.code
                        },
                        "components": components+[
                            {
                                "type": "button",
                                "sub_type": "flow",
                                "index": "0",
                                "parameters": [
                                    {
                                        "type": "action",
                                        "action": {
                                            "flow_token": json.dumps({
                                                "flow_uid": self.flows_id.flow_id,
                                                "template_uid": self.id
                                            }),
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            response = requests.post(
                f"https://graph.facebook.com/v18.0/{phone_uid}/messages",
                json=payload, headers=headers)
            if response.status_code == 200:
                template_body = self._get_formatted_template_body(record=1,
                                                                  demo_value=False)
                channel = self.env['whatsapp.channel'].search(
                    [('sender_id', '=', self.env.user.partner_id.id),
                     ('partner_id', '=', partner.id)])
                message_values = {
                    'is_template': True,
                    'template_id': self.id,
                    'flag': True,
                    'message_uid': response.json()['messages'][0]['id'],
                    'state': 'sent',
                }
                if self.header_type != 'none':
                    message_values['message_type'] = self.header_type
                    if self.header_type == 'text':
                        header = self._get_formatted_template_header(record=1,
                                                                     demo_value=False)
                        template_body = header + template_body
                    if header_values and header_values[
                        'attachment'] is not None:
                        attachment = header_values['attachment']
                        message_values['attachment_id'] = attachment.id
                    if self.header_type == 'image':
                        message_values['image'] = attachment.datas
                if channel:
                    message_values['channel_id'] = channel.id
                else:
                    channel = self.env['whatsapp.channel'].create({
                        'name': partner.name,
                        'partner_id': partner.id,
                        'sender_id': self.env.user.partner_id.id,
                        'user_id': self.env.user.id
                    })
                    message_values['channel_id'] = channel.id
                message_values['template_body'] = template_body
                msg = self.env['whatsapp.message'].create(message_values)
                channel.write({
                    'last_message': msg.message,
                    'last_messenger': "You",
                })
            else:
                error_message = response.json()['error']['message']
                raise ValidationError(_(error_message))

    def action_send_template_marketing(self, record, attachment, partner, cloud_token, phone_uid):
        """
        Send a WhatsApp template message to the specified partners.

        Args:
            record (recordset): The record to be included in the template.
            attachment (recordset): Any attachment to be included in the message.
            partner (recordset): The recipient(s) of the template.
            cloud_token : The user Whatsapp token_id
            phone_uid : The user phone_uid

        Raises:
            ValidationError: If an error occurs while sending the template.
        """
        if not record:
            raise ValidationError(_('Record is missed'))
        if self.state != 'approved':
            raise ValidationError(
                _('Please approve the template before sending!'))
        headers = {'Authorization': f'Bearer {cloud_token}',
                   'Content-Type': 'application/json'}
        components = []
        for partner in partner:
            if self.header_type != 'none':
                header_values = self._get_header_component(record, attachment,
                                                           partner)
                components.append(header_values['header'])
            if self.body:
                components.append(self._get_body_component(record))
            if self.template_type in 'custom':
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": partner.whatsapp_number,
                    "type": "template",
                    "template": {
                        'name': self.template_name,
                        "language": {"code": self.lang_id.code},
                        "components": components
                    }
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": partner.whatsapp_number,
                    "type": "template",
                    "template": {
                        'name': self.template_name,
                        "language": {
                            "code": self.lang_id.code
                        },
                        "components": components+[
                            {
                                "type": "button",
                                "sub_type": "flow",
                                "index": "0",
                                "parameters": [
                                    {
                                        "type": "action",
                                        "action": {
                                            "flow_token": json.dumps({
                                                "flow_uid": self.flows_id.flow_id,
                                                "template_uid": self.id
                                            }),
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            response = requests.post(
                f"https://graph.facebook.com/v18.0/{phone_uid}/messages",
                json=payload, headers=headers)
            if response.status_code == 200:
                template_body = self._get_formatted_template_body(record=1,
                                                                  demo_value=False)
                channel = self.env['whatsapp.channel'].search(
                    [('sender_id', '=', self.env.user.partner_id.id),
                     ('partner_id', '=', partner.id)])
                message_values = {
                    'is_template': True,
                    'template_id': self.id,
                    'flag': True,
                    'message_uid': response.json()['messages'][0]['id'],
                    'state': 'sent',
                }
                if self.header_type != 'none':
                    message_values['message_type'] = self.header_type
                    if self.header_type == 'text':
                        header = self._get_formatted_template_header(record=1,
                                                                     demo_value=False)
                        template_body = header + template_body
                    if header_values and header_values[
                        'attachment'] is not None:
                        attachment = header_values['attachment']
                        message_values['attachment_id'] = attachment.id
                    if self.header_type == 'image':
                        message_values['image'] = attachment.datas
                if channel:
                    message_values['channel_id'] = channel.id
                else:
                    channel = self.env['whatsapp.channel'].create({
                        'name': partner.name,
                        'partner_id': partner.id,
                        'sender_id': self.env.user.partner_id.id,
                        'user_id': self.env.user.id
                    })
                    message_values['channel_id'] = channel.id
                message_values['template_body'] = template_body
                msg = self.env['whatsapp.message'].create(message_values)
                channel.write({
                    'last_message': msg.message,
                    'last_messenger': "You",
                })
                return message_values['message_uid']
            else:
                error_message = response.json()['error']['message']
                raise ValidationError(_(error_message))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to handle specific actions after creating WhatsApp templates.

        If the action specified in the input values is 'create_sale_order', this method associates the newly created
        WhatsApp template with the active quotation template from the context using its `template_id` field.

        Args:
            vals_list (list): A list of dictionaries containing the values for record creation.

        Returns:
            recordset: The newly created WhatsApp template records.
        """
        res = super(WhatsappTemplate, self).create(vals_list)
        active_id = self.env.context.get('active_id')
        for record, vals in zip(res, vals_list):
            if vals.get('action') == 'create_sale_order' and active_id:
                self.env['sale.order.template'].browse(active_id).write(
                    {'template_id': record.id})
        return res
