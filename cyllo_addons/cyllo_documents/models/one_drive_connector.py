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
import logging
import requests
from werkzeug import urls

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)
ONEDRIVE_SCOPE = ['offline_access openid Files.ReadWrite.All']


class OneDriveConnector(models.Model):
    """Model to manage One Drive integration"""
    _name = 'one.drive.connector'
    _description = 'One Drive Connector'

    name = fields.Char(help="Name for Connector", required=True)
    one_drive_client_key = fields.Char(string="One Drive Client Id", help="Client id from azure portal", copy=False,
                                       required=True)
    one_drive_secret = fields.Char(help="Client secret from azure portal", copy=False, required=True)
    one_drive_folder_key = fields.Char(string="One Drive Folder ID", copy=False,
                                       help="Enter folder id if you want export into specific folder")
    one_drive_access_token = fields.Char(help="Google drive access token")
    one_drive_refresh_token = fields.Char(help="Google drive refresh token")
    one_drive_token_validity = fields.Datetime(copy=False, help='Token validity of the google drive')
    state = fields.Selection(selection=[('draft', 'Draft'), ('connected', 'Connected')], default='draft',
                             help="Select the state of the item: Draft or Connected.")
    document_file_ids = fields.Many2many('document.file', string="Document Files",
                                         help='Document File')
    workspace_id = fields.Many2one('document.workspace', string='Workspace',
                                   help="Select a workspace with one drive id to upload into it",
                                   domain="[('onedrive_folder_id', '!=', False)]")

    def action_export_files(self):
        """Method to export selected files to OneDrive. This function checks the validity of the OneDrive access token,
         and if it has expired, it generates a new access token using the refresh token. It then uploads selected
         files to OneDrive.
        Returns:
            dict: A dictionary containing a notification message indicating whether the file upload was successful.
        Raises:
            UserError: If there is an exception during the file upload process. """
        if self.one_drive_token_validity <= fields.Datetime.now():
            self.generate_one_drive_refresh_token()
        access_token = self.one_drive_access_token
        if self.document_file_ids:
            try:
                if self.document_file_ids:
                    flag = 0
                    headers_base = {'Authorization': f'Bearer {access_token}'}
                    for record in self.document_file_ids:
                        file_path = record.attachment_id._full_path(record.attachment_id.store_fname)
                        filename = record.name
                        parent_id = self.workspace_id.onedrive_folder_id if self.workspace_id else \
                            (self.one_drive_folder_key if self.one_drive_folder_key else False)
                        upload_url = \
                            f'https://graph.microsoft.com/v1.0/me/drive/' \
                            f'{f"root:/{filename}" if not parent_id else f"items/{parent_id}:/{filename}"}:/content'
                        headers = {**headers_base, 'Content-Type': record.mimetype}
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        response = requests.put(upload_url, headers=headers, data=file_content)
                        if response.status_code == 201:
                            flag = 1
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': "Files Uploaded Successfully" if flag == 1 else "Files Uploading Failed",
                            'type': 'success' if flag == 1 else 'danger',
                            'sticky': False,
                        }
                    }
            except Exception as e:
                raise UserError(e)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "Please choose at least one document",
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_get_access(self):
        """Method to initiate the process of getting access to OneDrive. This function constructs an authorization
        URL and returns it as an action URL for the user to initiate the authentication process with Microsoft
        OneDrive.
        Returns:
            dict: A dictionary containing the action URL information."""
        authority = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_id = self.env.ref('cyllo_documents.action_view_one_drive_connector').id
        redirect_url = base_url + f"/web#id={self.id}&action={action_id}&view_type=form&model=one.drive.connector"
        state = {
            'one_drive_connector_id': self.id,
            'url_return': redirect_url
        }
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.one_drive_client_key,
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': base_url + '/one_drive/auth',
            'state': json.dumps(state),
            'prompt': 'consent',
            'access_type': 'offline'
        })
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f"{authority}?{encoded_params}",
        }

    def generate_one_drive_refresh_token(self):
        """Generate a OneDrive access token from a refresh token if it has expired. This function makes a request to
        the Microsoft Azure OAuth2 token endpoint to refresh the OneDrive access token using a provided refresh token.
        Raises:
            requests.HTTPError: If there is an issue with the HTTP request or response."""
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'client_id': self.one_drive_client_key,
            'client_secret': self.one_drive_secret,
            'scope': ONEDRIVE_SCOPE,
            'grant_type': "refresh_token",
            'redirect_uri': base_url + '/one_drive/auth',
            'refresh_token': self.one_drive_refresh_token
        }
        try:
            res = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                data=data, headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'one_drive_access_token': response.get('access_token'),
                    'one_drive_refresh_token': response.get('refresh_token'),
                    'one_drive_token_validity': fields.Date.add(fields.Datetime.now(), seconds=expires_in),
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !", error.response.content)
            raise error

    def get_onedrive_tokens(self, authorize_code):
        """Method to get one drive access token.
        Args:
            authorize_code:Authorization code from onedrive to generate access token"""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        data = {
            'code': authorize_code,
            'client_id': self.one_drive_client_key,
            'client_secret': self.one_drive_secret,
            'grant_type': 'authorization_code',
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': base_url + '/one_drive/auth'
        }
        try:
            res = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data, headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'one_drive_access_token': response.get('access_token'),
                    'one_drive_refresh_token': response.get('refresh_token'),
                    'one_drive_token_validity': fields.Date.add(fields.Datetime.now(), seconds=expires_in),
                    'state': 'connected'
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !", error.response.content)
            raise error

    def auto_sync_one_drive(self):
        """Method that is triggered during an auto-sync to export and import files from OneDrive. This method is
        used to synchronize files between the Odoo application and OneDrive for connected users. It checks
        the validity of the OneDrive access token and refreshes it if necessary. Then, it retrieves files and folders
        from OneDrive and imports them into Odoo as document files. """
        for rec in self.search([('state', '=', 'connected')]):
            if rec.one_drive_token_validity <= fields.Datetime.now():
                rec.generate_one_drive_refresh_token()
            access_token = rec.one_drive_access_token
            for record in self.workspace_id.search([]):
                folder_id = record.onedrive_folder_id
                if not folder_id:
                    continue
                url = (f"https://graph.microsoft.com/v1.0/me/"
                       f"drive/items/{folder_id}/children")
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("value", []):
                        file_id = item.get("id")
                        file_name = item.get("name")
                        file_url = (f"https://graph.microsoft.com/v1.0/"
                                    f"me/drive/items/{file_id}/content")
                        file_response = requests.get(file_url, headers=headers)
                        if file_response.status_code == 200:
                            file_content = file_response.content
                            base64_content = base64.b64encode(file_content).decode("utf-8")
                            if not self.env['document.file'].search([('one_drive_file_key', '=', file_id)]):
                                self.env['document.file'].action_upload_document({
                                    'file': base64_content,
                                    'file_name': file_name,
                                    'workspace_id': record.id,
                                    'one_drive_file_key': file_id})
        self.auto_sync_export_one()
        self.sync_one_drive_workspace()

    def auto_sync_export_one(self):
        """Method to export files to OneDrive during auto-sync. This method is triggered during an auto-sync process
        to export files from Odoo to OneDrive for connected users. It checks the validity of the OneDrive access
        token and refreshes it if necessary. Then, it uploads files to OneDrive and updates their corresponding
        OneDrive file keys in Odoo."""
        for rec in self.search([('state', '=', 'connected')]):
            if rec.one_drive_token_validity <= fields.Datetime.now():
                rec.generate_one_drive_refresh_token()
            access_token = rec.one_drive_access_token
            headers_base = {'Authorization': f'Bearer {access_token}'}
            for record in self.workspace_id.search([('onedrive_folder_id', '!=', False)]):
                parent_id = record.onedrive_folder_id
                for document in self.document_file_ids.search(
                        [('workspace_id', '=', record.id), ('one_drive_file_key', '=', False)]):
                    file_path = document.attachment_id._full_path(document.attachment_id.store_fname)
                    filename = document.name
                    upload_url = \
                        (f'https://graph.microsoft.com/v1.0/me/drive/'
                         f'{f"root:/{filename}" if not parent_id else f"items/{parent_id}:/{filename}"}:/content')
                    headers = {**headers_base, 'Content-Type': document.mimetype}
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    response = requests.put(upload_url, headers=headers, data=file_content)
                    if response.status_code == 201:
                        document.write({'one_drive_file_key': response.json()['id']})

    def sync_one_drive_workspace(self):
        """Synchronize workspace with OneDrive. This function checks if the synchronization with OneDrive is enabled
        in the configuration.If enabled, it iterates over connected records and performs the synchronization.
            - If the OneDrive token is expired, it generates a new refresh token.
            - Retrieves the access token for the OneDrive API.
            - Retrieves the list of folders from the user's OneDrive.
            - Checks if each folder is already associated with a workspace in the system.
            - If not, create a new workspace record for the folder.
            :return: None
            :raises: UserError if any exception occurs during the synchronization process. """
        if self.env['ir.config_parameter'].sudo().get_param('cyllo_documents.sync_one_drive_workspace'):
            for rec in self.search([('state', '=', 'connected')]):
                if rec.one_drive_token_validity <= fields.Datetime.now():
                    rec.generate_one_drive_refresh_token()
                access_token = rec.one_drive_access_token
                headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
                try:
                    drive_url = ('https://graph.microsoft.com/v1.0/me/drive/'
                                 'root/children?$filter=folder ne null')
                    response = requests.get(drive_url, headers=headers)
                    if response.status_code == 200:
                        folders = response.json()['value']
                        for folder in folders:
                            if not self.workspace_id.search([('onedrive_folder_id', '=', folder["id"])]):
                                self.workspace_id.create({'name': folder['name'],
                                                          'onedrive_folder_id': folder['id']})
                except Exception as e:
                    raise UserError(e)
