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
import requests
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.http import request


class GoogleDriveConnector(models.Model):
    """Model to manage Google Drive integration"""
    _name = 'google.drive.connector'
    _description = "Google Drive Connector"

    name = fields.Char(help="Name for Connector", required=True)
    google_client_key = fields.Char(string="Google Drive Client ID", help="Client id from google cloud console",
                                    copy=False, required=True)
    google_client_secret = fields.Char(help="Client secret from google cloud console", copy=False, required=True)
    google_drive_folder_key = fields.Char(
        string="Google Drive Folder Id", copy=False, help="Enter folder id if you want export into specific folder")
    google_drive_access_token = fields.Char(help="Google drive access token ")
    google_drive_refresh_token = fields.Char(help="Google drive refresh token")
    google_drive_token_validity = fields.Datetime(copy=False, help='Token validity of the google drive')
    is_gdrive_access = fields.Boolean(string="Google Drive Access", help="Got google drive Access or not")
    document_file_ids = fields.Many2many('document.file', string="Document Files",
                                         help='Document File')
    workspace_id = fields.Many2one('document.workspace', string='Workspace',
                                   help="Select a workspace with google drive id to upload into it",
                                   domain="[('google_drive_folder_id', '!=', False)]")
    state = fields.Selection(selection=[('draft', 'Draft'), ('connected', 'Connected')],
                             default='draft', help="State of the item: Draft or Connected.")

    def action_get_access(self):
        """Generate an OAuth2 authorization URL for obtaining Google Drive access. This method constructs an OAuth2
        authorization URL that users can visit to grant access to their Google Drive account. The generated URL
        includes necessary parameters such as the client ID, scope, redirect URI, and state.
        :return: A dictionary with the URL information for redirection.
        :rtype: dict """
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_id = self.env.ref('cyllo_documents.action_view_google_drive_connector').id
        redirect_url = base_url + ('/web#id=%d&action=%d&view_type=form&model'
                                   '=%s') % (self.id, action_id, 'google.drive.connector')
        state = {'google_drive_connector_id': self.id, 'url_return': redirect_url}
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.google_client_key,
            'scope': 'https://www.googleapis.com/auth/drive '
                     'https://www.googleapis.com/auth/drive.file',
            'redirect_uri': base_url + '/google_drive/auth',
            'state': json.dumps(state),
            'access_type': 'offline',
            'approval_prompt': 'force',
        })
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f'https://accounts.google.com/o/oauth2/auth?{encoded_params}',
        }

    def action_export_files(self):
        """Export selected files to Google Drive. This method exports the selected files to Google Drive. It
        first checks the validity of the Google Drive access token and refreshes it if necessary. Then, it uploads
        the selected files to Google Drive.
        :return: A dictionary with a success or failure message.
        :rtype: dict"""
        if self.google_drive_token_validity <= fields.Datetime.now():
            self.generate_google_drive_refresh_token()
        access_token = self.google_drive_access_token
        parent_folder_id = self.workspace_id.google_drive_folder_id \
            if self.workspace_id else self.google_drive_folder_key if self.google_drive_folder_key else False
        if self.document_file_ids:
            headers = {"Authorization": f"Bearer {access_token}"}
            flag = 0
            for record in self.document_file_ids:
                file_path = record.attachment_id._full_path(record.attachment_id.store_fname)
                metadata = {"name": record.name}
                upload_url = ("https://www.googleapis.com/upload/drive/v3/"
                              "files?uploadType=multipart")
                if parent_folder_id:
                    metadata["parents"] = [parent_folder_id]
                files = {
                    "metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
                    "file": (record.name, open(file_path, "rb"), record.mimetype)}
                response = requests.post(upload_url, headers=headers, files=files)
                if response.status_code == 200:
                    record.write({'google_drive_file_key': response.json()['id']})
                    flag = 1
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "Files Uploaded Successfully" if flag else
                    "Files Uploading Failed ,"
                    "May be Files already exist in Drive",
                    'type': 'success' if flag else 'danger',
                    'sticky': False,
                }
            }
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

    def generate_google_drive_refresh_token(self):
        """Generate a new Google Drive access token from the refresh token if it has expired. This method attempts
        to generate a new Google Drive access token using the provided refresh token. If the refresh token is valid
        and not expired, it obtains a new access token, updates the access token and its validity period, and stores
        them in the database.
        :return: None
        :raises: UserError if an error occurs during the token generation
         process, such as invalid credentials or an expired refresh token."""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.google_drive_refresh_token,
            'client_id': self.google_client_key,
            'client_secret': self.google_client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.post('https://accounts.google.com/o/oauth2/token', data=data, headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'google_drive_access_token': response.get('access_token'),
                    'google_drive_token_validity': fields.Date.add(fields.Datetime.now(), seconds=expires_in)})
        except requests.HTTPError as error:
            error_key = error.response.json().get("error", "nc")
            error_msg = _("An error occurred while generating the token. Your authorization code may be invalid or "
                          "has already expired [%s]. You should check your Client ID and secret on the Google APIs"
                          " plateform or try to stop and restart your calendar synchronisation.", error_key)
            raise UserError(error_msg)

    def get_google_drive_tokens(self, authorize_code):
        """Exchange an authorization code for Google Drive tokens.
        :param authorize_code: The authorization code received from
        Google Drive.
        :type authorize_code: str
        :return: A dictionary containing Google Drive tokens and related data.
        :rtype: dict
        """
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self.google_client_key,
            'client_secret': self.google_client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_drive/auth'
        }
        try:
            res = requests.post('https://accounts.google.com/o/oauth2/token', params=data, headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'google_drive_access_token': response.get('access_token'),
                    'google_drive_refresh_token': response.get('refresh_token'),
                    'google_drive_token_validity': fields.Date.add(fields.Datetime.now(), seconds=expires_in),
                    'is_gdrive_access': True,
                    'state': 'connected'
                })
        except requests.HTTPError:
            error_msg = _(
                "Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise UserError(error_msg)

    def auto_sync_google_drive(self):
        """Method works while auto sync is triggered to export and import files from Google Drive"""
        self.auto_sync_export_google()
        self.sync_google_workspace()
        for rec in self.search([('state', '=', 'connected')]):
            if rec.google_drive_token_validity <= fields.Datetime.now():
                rec.generate_google_drive_refresh_token()
            access_token = rec.google_drive_access_token
            for record in self.workspace_id.search([('google_drive_folder_id', '!=', False)]):
                folder_id = record.google_drive_folder_id
                params = {'q': f"'{folder_id}' in parents and trashed=false"}
                headers = {'Authorization': f'Bearer {access_token}'}
                list_files_url = 'https://www.googleapis.com/drive/v3/files'
                try:
                    list_files_response = requests.get(list_files_url, headers=headers, params=params)
                    list_files_response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    continue
                for file_data in list_files_response.json().get('files', []):
                    try:
                        file_response = requests.get(
                            f'https://www.googleapis.com/drive/v3/files/'
                            f'{file_data["id"]}?alt=media', headers=headers, params=params)
                        file_response.raise_for_status()
                    except requests.exceptions.RequestException as e:
                        continue
                    if file_response.status_code == 200:
                        try:
                            if not (
                                    self.env['document.file'].search(
                                        [('google_drive_file_key', '=', file_data["id"])])):
                                self.env['document.file'].action_upload_document({
                                    'file': base64.b64encode(file_response.content).decode('utf-8'),
                                    'file_name': file_data['name'],
                                    'workspace_id': record.id,
                                    'google_drive_file_key': file_data["id"]
                                })
                        except Exception as e:
                            raise UserError(e)

    def auto_sync_export_google(self):
        """Automatically synchronize files with Google Drive. This method is triggered during automatic
        synchronization to export and import files from Google Drive. It checks for the validity of the Google Drive
        access token, refreshes it if necessary, and then imports files from Google Drive to the current workspace.
        :return: None """
        for rec in self.search([('state', '=', 'connected')]):
            if rec.google_drive_token_validity <= fields.Datetime.now():
                rec.generate_google_drive_refresh_token()
            access_token = rec.google_drive_access_token
            headers = {"Authorization": f"Bearer {access_token}"}
            for record in self.workspace_id.search([('google_drive_folder_id', '!=', False)]):
                parent_folder_id = record.google_drive_folder_id
                for document in self.document_file_ids.search(
                        [('workspace_id', '=', record.id), ('google_drive_file_key', '=', False)]):
                    file_path = document.attachment_id._full_path(document.attachment_id.store_fname)
                    metadata = {"name": document.name}
                    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
                    if parent_folder_id:
                        metadata["parents"] = [parent_folder_id]
                    files = {"metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
                             "file": (document.name, open(file_path, "rb"), document.mimetype)}
                    response = requests.post(upload_url, headers=headers, files=files)
                    if response.status_code == 200:
                        document.write({'google_drive_file_key': response.json()['id']})

    def sync_google_workspace(self):
        """The function for getting the google location of the work space"""
        if self.env['ir.config_parameter'].sudo().get_param('cyllo_documents.sync_google_workspace'):
            for rec in self.search([('state', '=', 'connected')]):
                if rec.google_drive_token_validity <= fields.Datetime.now():
                    rec.generate_google_drive_refresh_token()
                access_token = rec.google_drive_access_token
                drive_api_url = "https://www.googleapis.com/drive/v3/files"
                query_params = {'q': "mimeType='application/vnd.google-apps.folder' and trashed=false",
                                'fields': "files(id, name)", 'access_token': access_token}
                try:
                    response = requests.get(drive_api_url, params=query_params)
                    response.raise_for_status()
                    folders_data = response.json()
                    folders = folders_data.get('files', [])
                    for folder in folders:
                        if not self.workspace_id.search([('google_drive_folder_id', '=', folder["id"])]):
                            self.workspace_id.create({'name': folder['name'], 'google_drive_folder_id': folder['id']})
                except requests.exceptions.RequestException as e:
                    raise UserError(e)
