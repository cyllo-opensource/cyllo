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
import json
import re
import requests
from datetime import datetime, timedelta
from odoo import _, fields, models
from werkzeug import urls

ACCESS = ["Contacts.ReadWrite openid Files.ReadWrite.All Tasks.ReadWrite"
          " Presence.Read.All User.Read User.ReadWrite.All offline_access"]


class CylloOfficeConnector(models.Model):
    """ Class to define field to cyllo.office.connector for saving credential of office"""
    _name = 'cyllo.office.connector'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Office Connector Instance"

    name = fields.Char(help="Name of the connector")
    type = fields.Selection(
        [('contact', 'Contact'), ('file', 'File'), ('task', 'Task')],
        required=True,
        default="contact", help="Type of operation")
    client_number = fields.Char(string="Client Id", required=True,
                                help="Id of client on office 365 ")
    client_secrets = fields.Char(required=True,
                                 help="Secrets of client on office 365 ")
    access_token = fields.Char(help="office 365 access token")
    access_refresh_token = fields.Char(string="Refresh Token",
                                       help="office 365 refresh token")
    state = fields.Selection([('new', 'Not Connected'), ('sync', 'Connected'),
                              ('expired', 'Expired')],
                             'Status', readonly=True, index=True, default='new',
                             help='State of Office 365 instance')
    ir_attachment_ids = fields.Many2many('ir.attachment',
                                         string='File to Upload',
                                         help="Choose file to upload")
    onedrive_token_validity = fields.Datetime(string='Access token valid till',
                                              help="the access token will be valid till this time")
    office_contact_api_url = fields.Char(string="Contact Api Url",
                                         default="https://graph.microsoft.com/v1.0/me/contacts",
                                         help="Api url to get contact from the office 365")
    office_file_api_url = fields.Char(string="File Api Url",
                                      default="https://graph.microsoft.com/v1.0/me/drive/root:",
                                      help="Api url to upload file to the office 365")
    office_to_do_api_url = fields.Char(string="To Do Api Url",
                                       default="https://graph.microsoft.com/v1.0/me/todo/lists",
                                       help="Api url to access to do of office 365")
    task_list = fields.Char(string="List of Task",
                            help="Id of list where to do have to save")
    contact_synced = fields.Boolean(string="Contact Sync",
                                    compute='_compute_contact_synced',
                                    help="Represent contact synced or not")
    to_do_synced = fields.Boolean(string="Task Sync",
                                  help="Represent To do synced or not")
    contact_synced_expiration_date = fields.Datetime(
        string="Expiration of contact syncing",
        help="Expiration date of the syncing of contact")
    to_do_synced_expiration_date = fields.Datetime(
        string="Expiration of To DO syncing",
        help="Expiration date of the syncing of To DO")
    contact_create_subscription_number = fields.Char(
        help="Id of subscription contact creation")
    contact_update_subscription_number = fields.Char(
        help="Id of subscription contact update")
    contact_delete_subscription_number = fields.Char(
        help="Id of subscription contact deletion")
    to_do_create_subscription_number = fields.Char(
        string="To DO Create Subscription Id",
        help="Id of subscription To DO creation")
    to_do_update_subscription_number = fields.Char(
        string="To DO Update Subscription Id",
        help="Id of subscription To DO update")
    to_do_delete_subscription_number = fields.Char(
        string="To DO Delete Subscription Id",
        help="Id of subscription To DO deletion")
    company_id = fields.Many2one('res.company', required=True,
         default=lambda self: self.env.company,
         help='Select the company')

    def _compute_contact_synced(self):
        """Compute the contact synchronization status."""
        for instance in self:
            if instance.contact_synced_expiration_date:
                if instance.contact_synced_expiration_date <= datetime.today():
                    instance.contact_synced = False
                else:
                    instance.contact_synced = True
            else:
                instance.contact_synced = False
            if instance.to_do_synced_expiration_date:
                if instance.to_do_synced_expiration_date <= datetime.today():
                    instance.to_do_synced = False
                else:
                    instance.to_do_synced = True
            else:
                instance.to_do_synced = False

    def action_disconnect(self):
        """Function to disconnect the instance"""
        if self.to_do_synced or self.contact_synced:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Instance is synced with office ,Unsync the instance to disconnect"),
                    'type': 'danger',
                },
            }
        self.write({
            'access_token': False,
            'state': 'new',
        })

    def action_sync_contact(self):
        """ Synchronize contacts with Office 365."""
        try:
            if self.env['ir.config_parameter'].sudo().get_param(
                    'cyllo_office_365_connector.contact_office_connector_id'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Already one account is connected"),
                        'type': 'warning',
                    },
                }
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            headers = {
                'Authorization': 'Bearer ' + self.access_token,
                'Content-Type': 'application/json',
            }
            expiration_datetime = datetime.utcnow() + timedelta(minutes=10070)
            expiration_datetime_str = expiration_datetime.strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            data_creation = {
                "changeType": "created",
                "notificationUrl": f'{base_url}/office/contacts/create',
                "resource": "/me/contacts",
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            data_deletion = {
                "changeType": "deleted",
                "notificationUrl": f'{base_url}/office/contacts/deleted',
                "resource": "/me/contacts",
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            data_update = {
                "changeType": "updated",
                "notificationUrl": f'{base_url}/office/contacts/updated',
                "resource": "/me/contacts",
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            response_creation = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_creation)
            self.contact_create_subscription_number = response_creation.json()[
                'id']
            response_deletion = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_deletion)
            self.contact_delete_subscription_number = response_deletion.json()[
                'id']
            response_update = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_update)
            self.contact_update_subscription_number = response_update.json()[
                'id']
            if (response_creation.status_code == 201 and
                    response_deletion.status_code == 201 and
                    response_update.status_code == 201):
                self.contact_synced_expiration_date = expiration_datetime
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.contact_office_connector_id',
                    self.id)
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.contact_office_access_token',
                    self.access_token)
                self._compute_contact_synced()
                self.message_post(body=_(
                    'Webhook subscriptions for contact created successfully.'),
                                  message_type="notification",
                                  subtype_xmlid="mail.mt_comment")
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Failed to create webhook subscriptions."),
                        'type': 'danger',
                    },
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Syncing Failed"),
                    'type': 'warning',
                },
            }

    def action_unsync_contact(self):
        """ Unsubscribe from contact webhook subscriptions."""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            create_api_url = (f'https://graph.microsoft.com/v1.0/subscriptions/'
                              f'{self.contact_create_subscription_number}')
            delete_api_url = (f'https://graph.microsoft.com/v1.0/subscriptions/'
                              f'{self.contact_delete_subscription_number}')
            update_api_url = (f'https://graph.microsoft.com/v1.0/subscriptions/'
                              f'{self.contact_update_subscription_number}')
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response_create = requests.delete(create_api_url, headers=headers)
            response_delete = requests.delete(delete_api_url, headers=headers)
            response_update = requests.delete(update_api_url, headers=headers)
            if (response_create.status_code == 204 and
                    response_delete.status_code == 204 and response_update.status_code == 204):
                self.contact_synced_expiration_date = False
                self._compute_contact_synced()
                self.contact_create_subscription_number = False
                self.contact_delete_subscription_number = False
                self.contact_update_subscription_number = False
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.contact_office_connector_id',
                    False)
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.contact_office_access_token',
                    False)
                self.message_post(body=_(
                    'Webhook subscriptions for contact deleted successfully.'),
                                  message_type="notification",
                                  subtype_xmlid="mail.mt_comment")
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_sync_todo(self):
        """ Synchronize to-do tasks with Office 365."""
        try:
            if self.env['ir.config_parameter'].sudo().get_param(
                    'cyllo_office_365_connector.todo_office_connector_id'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Already one account is connected"),
                        'type': 'warning',
                    },
                }
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            headers = {
                'Authorization': 'Bearer ' + self.access_token,
                'Content-Type': 'application/json',
            }
            expiration_datetime = datetime.utcnow() + timedelta(minutes=4230)
            expiration_datetime_str = expiration_datetime.strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            export_record = {'displayName': self.name}
            if not self.task_list:
                task_list = requests.post(self.office_to_do_api_url,
                                          headers=headers, json=export_record)
                self.task_list = task_list.json()['id']
            data_creation = {
                "changeType": "created",
                "notificationUrl": f'{base_url}/office/to_do/create',
                "resource": f'/me/todo/lists/{self.task_list}/tasks',
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            data_deletion = {
                "changeType": "deleted",
                "notificationUrl": f'{base_url}/office/to_do/deleted',
                "resource": f'/me/todo/lists/{self.task_list}/tasks',
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            data_update = {
                "changeType": "updated",
                "notificationUrl": f'{base_url}/office/to_do/updated',
                "resource": f'/me/todo/lists/{self.task_list}/tasks',
                "expirationDateTime": expiration_datetime_str,
                "clientState": "secretClientState"
            }
            response_creation = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_creation)
            self.to_do_create_subscription_number = response_creation.json()[
                'id']
            response_deletion = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_deletion)
            self.to_do_delete_subscription_number = response_deletion.json()[
                'id']
            response_update = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers, json=data_update)
            self.to_do_update_subscription_number = response_update.json()['id']
            if (
                    response_creation.status_code == 201 and response_deletion.status_code == 201 and
                    response_update.status_code == 201):
                self._compute_contact_synced()
                self.to_do_synced_expiration_date = expiration_datetime
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.todo_office_connector_id',
                    self.id)
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.office_todo_access_token',
                    self.access_token)
                self.message_post(body=_(
                    'Webhook subscriptions for to do created successfully. Any change in the list %s will be effected'
                    ' in cyllo, if there is no list with name %s create one in the office 365 .',
                    self.name, self.name), message_type="notification",
                    subtype_xmlid="mail.mt_comment")
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Failed to create webhook subscriptions."),
                        'type': 'danger',
                    },
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_unsync_todo(self):
        """ Unsubscribe from contact webhook subscriptions."""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            # Microsoft Graph API endpoint for deleting a subscription
            create_api_url = f'https://graph.microsoft.com/v1.0/subscriptions/{self.to_do_create_subscription_number}'
            delete_api_url = f'https://graph.microsoft.com/v1.0/subscriptions/{self.to_do_delete_subscription_number}'
            update_api_url = f'https://graph.microsoft.com/v1.0/subscriptions/{self.to_do_update_subscription_number}'
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response_create = requests.delete(create_api_url, headers=headers)
            response_delete = requests.delete(delete_api_url, headers=headers)
            response_update = requests.delete(update_api_url, headers=headers)
            if (response_create.status_code == 204 and
                    response_delete.status_code == 204 and response_update.status_code == 204):
                self.to_do_synced_expiration_date = False
                self._compute_contact_synced()
                self.to_do_create_subscription_number = False
                self.to_do_delete_subscription_number = False
                self.to_do_update_subscription_number = False
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.todo_office_connector_id',
                    False)
                self.env['ir.config_parameter'].sudo().set_param(
                    'cyllo_office_365_connector.office_todo_access_token',
                    False)
                self.message_post(body=_(
                    'Webhook subscriptions for to do deleted successfully.'),
                                  message_type="notification",
                                  subtype_xmlid="mail.mt_comment")
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_upload(self):
        """Function to upload file to the one drive"""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            for attachment in self.ir_attachment_ids:
                file_name = attachment.name
                folder_name = self.env.company.name
                upload_url = f'{self.office_file_api_url}/{folder_name}/{file_name}:/content'
                file_data = base64.b64decode(attachment.datas)
                headers = {'Authorization': 'Bearer ' + self.access_token}
                response = requests.put(upload_url, data=file_data,
                                        headers=headers)
                if response.status_code not in (201, 200):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("Upload is incomplete"),
                            'type': 'warning',
                        },
                    }
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("File Uploaded"),
                    'type': 'success',
                },
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_token_access(self):
        """Method to get access from Office 365"""
        authority = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_id = self.env.ref(
            'cyllo_office_365_connector.action_view_connector').id
        redirect_url = (
                    base_url + f'/web#id={self.id}&action={action_id}&view_type=form&model=cyllo.office.connector')
        state = {'office_connector_id': self.id, 'url_return': redirect_url}
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.client_number,
            'scope': ' '.join(ACCESS),
            'redirect_uri': base_url + '/office/auth',
            'state': json.dumps(state),
            'prompt': 'consent',
            'access_type': 'offline'
        })
        auth_url = "%s?%s" % (authority, encoded_params)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def get_office_365_tokens(self, authorize_code):
        """Function to set the Authorization  access token"""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        data = {
            'code': authorize_code,
            'client_id': self.client_number,
            'client_secret': self.client_secrets,
            'grant_type': 'authorization_code',
            'scope': ' '.join(ACCESS),
            'redirect_uri': base_url + '/office/auth'
        }
        try:
            res = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data=data, headers=headers)
            res.raise_for_status()
            response = res.json()
            if response:
                if self.env['ir.config_parameter'].sudo().get_param(
                        'cyllo_office_365_connector.contact_office_access_token'):
                    self.env['ir.config_parameter'].sudo().set_param(
                        'cyllo_office_365_connector.contact_office_access_token',
                        response.get('access_token'))
                if self.env['ir.config_parameter'].sudo().get_param(
                        'cyllo_office_365_connector.office_todo_access_token'):
                    self.env['ir.config_parameter'].sudo().set_param(
                        'cyllo_office_365_connector.office_todo_access_token',
                        response.get('access_token'))
                self.write({
                    'access_token': response.get('access_token'),
                    'access_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=response.get('expires_in')) if response.get(
                        'expires_in') else False,
                    'state': 'sync',
                })
        except requests.HTTPError:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_refresh_office_365_tokens(self):
        """Function to refresh access token after its expiring"""
        data = {
            'client_id': self.client_number,
            'client_secret': self.client_secrets,
            'scope': ACCESS,
            'grant_type': "refresh_token",
            'redirect_uri': self.env['ir.config_parameter'].get_param(
                'web.base.url') + '/office/auth',
            'refresh_token': self.access_refresh_token
        }
        try:
            res = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data=data,
                headers={"Content-type": "application/x-www-form-urlencoded"})
            res.raise_for_status()
            if res.status_code == 200:
                response = res.json()
                self.write({
                    'access_token': response.get('access_token'),
                    'access_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=int(
                            response.get('expires_in'))) if response.get(
                        'expires_in') else False,
                    'state': 'sync',
                })
                if self.env['ir.config_parameter'].sudo().get_param(
                        'cyllo_office_365_connector.contact_office_access_token'):
                    self.env['ir.config_parameter'].sudo().set_param(
                        'cyllo_office_365_connector.contact_office_access_token',
                        response['access_token'])
                if self.env['ir.config_parameter'].sudo().get_param(
                        'cyllo_office_365_connector.office_todo_access_token'):
                    self.env['ir.config_parameter'].sudo().set_param(
                        'cyllo_office_365_connector.office_todo_access_token',
                        response['access_token'])
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Failed to Reconnect"),
                        'type': 'warning',
                    },
                }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Operation Failed"),
                    'type': 'warning',
                },
            }

    def action_get_office365_contacts(self):
        """Function to import contact"""
        if self.onedrive_token_validity <= fields.Datetime.now():
            self.action_refresh_office_365_tokens()
        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            response = requests.get(self.office_contact_api_url,
                                    headers=headers)
            response.raise_for_status()
            contacts_data = response.json()
            if not contacts_data['value']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Nothing to Import"),
                        'type': 'warning',
                    },
                }
            odoo_contact_id = self.env[
                'cyllo.office.connector.line'].search(
                [('type', '=', 'partner')]).mapped('office_365_identifier')
            for contact in contacts_data['value']:
                country = False
                state = False
                if contact['id'] not in odoo_contact_id and contact[
                    'displayName']:
                    if contact['homeAddress'].get('countryOrRegion'):
                        country = self.env['res.country'].search(
                            [('name', '=', contact['homeAddress'][
                                'countryOrRegion'].capitalize())], limit=1)
                    if contact['homeAddress'].get('state'):
                        state = self.env['res.country.state'].search(
                            [('name', '=',
                              contact['homeAddress']['state'].capitalize()),
                             ('country_id', '=', country.id)], limit=1)
                    created_contact = self.env['res.partner'].create({
                        'name': contact['displayName'],
                        'mobile': contact['mobilePhone'] if contact[
                            'mobilePhone'] else None,
                        'email': contact['emailAddresses'][0]['address'] if
                        contact['emailAddresses'] else None,
                        'street': contact['homeAddress']['street'] if contact[
                            'homeAddress'] else None,
                        'city': contact['homeAddress']['city'] if contact[
                            'homeAddress'] else None,
                        'country_id': country.id if country else None,
                        'state_id': state.id if state else None,
                        'comment': contact['personalNotes'] if contact[
                            'personalNotes'] else None,
                        'zip': contact['homeAddress']['postalCode'] if contact[
                            'homeAddress'] else None,
                    })
                    created_contact.sudo().update({
                        'office_connectors_ids': [fields.Command.create(
                            {'office_365_identifier': contact['id'],
                             'connector_id': self.id,
                             'type': 'partner',
                             'partner_id': created_contact.id})]
                    })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("All Contact Synced Successfully"),
                    'type': 'success',
                },
            }
        except requests.HTTPError:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Contact Importing Failed"),
                    'type': 'warning',
                },
            }

    def action_export_contacts(self):
        """Function to export contact"""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            odoo_contacts = self.env['res.partner'].search([])
            for contact in odoo_contacts:
                if self.id not in contact.office_connectors_ids.mapped(
                        'connector_id.id'):
                    contact_data = {
                        "givenName": contact.name,
                        "emailAddresses": [],
                        "homeAddress": {
                            "street": contact.street or "",
                            "city": contact.city or "",
                            "state": contact.state_id.name or "",
                            "postalCode": contact.zip or "",
                            "countryOrRegion": contact.country_id.display_name or "",
                        },
                    }
                    if contact.email:
                        contact_data["emailAddresses"].append(
                            {"address": contact.email, "name": contact.name})
                    if contact.mobile:
                        contact_data["mobilePhone"] = contact.mobile
                    headers = {"Authorization": f"Bearer {self.access_token}",
                               "Content-Type": "application/json"}
                    response = requests.post(self.office_contact_api_url,
                                             json=contact_data, headers=headers)
                    if response.status_code != 201:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _("Exporting Failed"),
                                'type': 'warning',
                            },
                        }
                    contact.office_365_identifier = response.json()['id']
                    contact.sudo().update({
                        'office_connectors_ids': [
                            fields.Command.create(
                                {'office_365_identifier': response.json()['id'],
                                 'connector_id': self.id,
                                 'type': 'partner',
                                 'partner_id': contact.id})]
                    })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("All Contact Exported Successfully"),
                    'type': 'success',
                }
            }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Exporting Failed"),
                    'type': 'warning',
                },
            }

    def action_import_to_do(self):
        """Import to-do activities from Office 365."""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            headers = {'Authorization': 'Bearer ' + self.access_token,
                       'Content-Type': 'application/json'}
            response = requests.get(self.office_to_do_api_url, headers=headers)
            task_lists = response.json().get('value', [])
            for task_list in task_lists:
                task_list_id = task_list['id']
                tasks_url = f'{self.office_to_do_api_url}/{task_list_id}/tasks'
                tasks_response = requests.get(tasks_url, headers=headers)
                if tasks_response.status_code == 200:
                    tasks = tasks_response.json().get('value', [])
                    odoo_to_do_connectors = self.env[
                        'cyllo.office.connector.line'].search([
                        ('type', '=', 'activity')]).mapped(
                        'office_365_identifier')
                    for task in tasks:
                        if task['id'] not in odoo_to_do_connectors and task[
                            'id']:
                            due_date = fields.Date.context_today(self)
                            if task['status'] != 'completed':
                                activity_type = self.env[
                                    'mail.activity.type'].sudo().search(
                                    [('name', '=', 'To-Do')])
                                if not activity_type:
                                    activity_type = self.env[
                                        'mail.activity.type'].sudo().create({
                                        'name': 'To-Do', 'category': 'default'})
                                if 'dueDateTime' in task:
                                    due_date_time = task['dueDateTime'][
                                        'dateTime'][:-8]
                                    due_date = datetime.strptime(due_date_time,
                                                                 '%Y-%m-%dT%H:%M:%S').date()
                                activity = self.env['mail.activity'].create({
                                    'summary': task['title'],
                                    'activity_type_id': activity_type.id,
                                    'note': task['body']['content'],
                                    'date_deadline': due_date if due_date else None,
                                    'res_model_id': self.env[
                                        'ir.model']._get_id('res.partner'),
                                    'res_id': self.env.user.partner_id.id,
                                    'user_id': self.env.user.id,
                                })
                                activity.sudo().update({
                                    'office_connectors_ids': [
                                        fields.Command.create({
                                            'office_365_identifier': task['id'],
                                            'connector_id': self.id,
                                            'type': 'activity',
                                            'activity_id': activity.id})]})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("Imported all Activities"),
                            'type': 'success',
                        },
                    }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Importing Failed"),
                    'type': 'warning',
                },
            }

    def action_export_to_do(self):
        """Export to-do activities to Office 365."""
        try:
            if self.onedrive_token_validity <= fields.Datetime.now():
                self.action_refresh_office_365_tokens()
            headers = {
                'Authorization': 'Bearer ' + self.access_token,
                'Content-Type': 'application/json',
            }
            activities_to_export = self.env['mail.activity'].search([])
            export_record = {'displayName': self.name}
            if not self.task_list:
                task_list = requests.post(self.office_to_do_api_url,
                                          headers=headers, json=export_record)
                self.task_list = task_list.json()['id']
            tasks_url = f'{self.office_to_do_api_url}/{self.task_list}/tasks'
            for activity in activities_to_export:
                if self.id not in activity.office_connectors_ids.mapped(
                        'connector_id.id') and activity.summary:
                    due_date_time = activity.date_deadline.isoformat() if (
                        activity.date_deadline) else None
                    note = re.compile(r'<[^>]+>').sub('', activity.note) if (
                        activity.note) else None
                    export_record = {
                        'title': activity.summary,
                        'body': {"content": note if activity.note else None},
                        'dueDateTime': {
                            "dateTime": due_date_time if due_date_time else None,
                            'TimeZone': 'UTC' if due_date_time else None
                        },
                    }
                    response = requests.post(tasks_url, headers=headers,
                                             json=export_record)
                    if response.status_code != 201:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _("Exporting Failed"),
                                'type': 'warning',
                            },
                        }
                    activity.sudo().update({
                        'office_connectors_ids': [
                            fields.Command.create(
                                {'office_365_identifier': response.json()['id'],
                                 'connector_id': self.id,
                                 'type': 'activity',
                                 'activity_id': activity.id})]})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("All activities Exported Successfully"),
                    'type': 'success',
                },
            }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Exporting Failed"),
                    'type': 'warning',
                },
            }


