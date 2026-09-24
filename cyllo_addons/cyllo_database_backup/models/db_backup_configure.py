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
import boto3
import dropbox
import errno
import ftplib
import json
import logging
import os
import paramiko
import requests
import tempfile
from nc_py_api import Nextcloud

from datetime import timedelta
from werkzeug import urls
from markupsafe import Markup

import odoo
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
ONEDRIVE_SCOPE = ['offline_access openid Files.ReadWrite.All']
MICROSOFT_GRAPH_END_POINT = "https://graph.microsoft.com"
GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


class DbBackupConfigure(models.Model):
    """DbBackupConfigure class provides an interface to manage database
       backups of Local Server, Remote Server, Google Drive, Dropbox, Onedrive,
       Nextcloud and Amazon S3"""
    _name = 'db.backup.configure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Automatic Database Backup'

    name = fields.Char(required=True, help='Add the name')
    db_name = fields.Char(string='Database Name', required=True,
                          help='Name of the database')
    master_pwd = fields.Char(string='Master Password', required=True,
                             help='Master password')
    backup_format = fields.Selection([('zip', 'Zip'), ('dump', 'Dump')],
                                     default='zip', required=True,
                                     help='Format of the backup')
    backup_destination = fields.Selection([
        ('local', 'Local Storage'), ('google_drive', 'Google Drive'),
        ('ftp', 'FTP'), ('sftp', 'SFTP'),
        ('dropbox', 'Dropbox'), ('onedrive', 'Onedrive'),
        ('next_cloud', 'Next Cloud'), ('amazon_s3', 'Amazon S3')
    ], help='Destination of the backup')
    backup_path = fields.Char(help='Local storage directory path')
    sftp_host = fields.Char(help='SFTP host details')
    sftp_port = fields.Char(default=22, help='SFTP port details')
    sftp_user = fields.Char(copy=False, help='SFTP user details')
    sftp_password = fields.Char(copy=False, help='SFTP password')
    sftp_path = fields.Char(help='SFTP path details')
    ftp_host = fields.Char(help='FTP host details')
    ftp_port = fields.Char(default=21, help='FTP port details')
    ftp_user = fields.Char(copy=False, help='FTP user details')
    ftp_password = fields.Char(copy=False, help='FTP password')
    ftp_path = fields.Char(help='FTP path details')
    dropbox_client_key = fields.Char(string='Dropbox Client ID', copy=False,
                                     help='Client id of the dropbox')
    dropbox_client_secret = fields.Char(copy=False,
                                        help='Client secret id of the dropbox')
    dropbox_refresh_token = fields.Char(copy=False,
                                        help='Refresh token for the dropbox')
    is_dropbox_token_generated = fields.Boolean(
        string='Dropbox Token Generated',
        compute='_compute_is_dropbox_token_generated', copy=False,
        help='Is the dropbox token generated or not?')
    dropbox_folder = fields.Char(help='Dropbox folder')
    active = fields.Boolean(default=True, help='Is this active or not?')
    auto_remove = fields.Boolean(string='Remove Old Backups',
                                 help='Remove old backups')
    days_to_remove = fields.Integer(string='Remove After', default=30,
                                    help='Automatically delete stored backups after this specified number of days')
    google_drive_folder_key = fields.Char(string='Drive Folder ID',
                                          help='Folder id of the drive')
    notify_user = fields.Boolean(
        help='Send an email notification to user when the backup operation is successful '
             'or failed')
    user_id = fields.Many2one('res.users', help='Name of the user')
    backup_filename = fields.Char(help='For Storing generated backup filename')
    generated_exception = fields.Char(string='Exception',
                                      help='Exception Encountered while Backup generation')
    onedrive_client_key = fields.Char(string='Onedrive Client ID', copy=False,
                                      help='Client ID of the onedrive')
    onedrive_client_secret = fields.Char(copy=False,
                                         help='Client secret id of the onedrive')
    onedrive_access_token = fields.Char(copy=False,
                                        help='Access token for one drive')
    onedrive_refresh_token = fields.Char(copy=False,
                                         help='Refresh token for one drive')
    onedrive_token_validity = fields.Datetime(copy=False,
                                              help='Token validity date')
    onedrive_folder_key = fields.Char(string='Folder Name',
                                      help='Folder name of the onedrive')
    is_onedrive_token_generated = fields.Boolean(
        compute='_compute_is_onedrive_token_generated', copy=False,
        help='Whether to generate onedrive token?')
    gdrive_refresh_token = fields.Char(string='Google drive Refresh Token',
                                       copy=False,
                                       help='Refresh token for google drive')
    gdrive_access_token = fields.Char(string='Google Drive Access Token',
                                      copy=False,
                                      help='Access token for google drive')
    is_google_drive_token_generated = fields.Boolean(
        string='Google drive Token Generated',
        compute='_compute_is_google_drive_token_generated', copy=False,
        help='Google drive token generated or not')
    gdrive_client_key = fields.Char(string='Google Drive Client ID', copy=False,
                                    help='Client id of the google drive')
    gdrive_client_secret = fields.Char(string='Google Drive Client Secret',
                                       copy=False,
                                       help='Client secret id of the google drive')
    gdrive_token_validity = fields.Datetime(
        string='Google Drive Token Validity', copy=False,
        help='Token validity of the google drive')
    onedrive_redirect_uri = fields.Char(compute='_compute_redirect_uri',
                                        help='Redirect URI of the onedrive')
    gdrive_redirect_uri = fields.Char(string='Google Drive Redirect URI',
                                      compute='_compute_redirect_uri',
                                      help='Redirect URI of the google drive')
    domain = fields.Char(string='Domain Name',
                         help="Field used to store the name of a domain")
    next_cloud_user_name = fields.Char(string='User Name',
                                       help="Field used to store the user name for a Nextcloud account.")
    next_cloud_password = fields.Char(string='Password', copy=False,
                                      help="Field used to store the password for a Nextcloud account.")
    nextcloud_folder_key = fields.Char(string='Next Cloud Folder Id',
                                       help="Field used to store the unique identifier for a Nextcloud folder.")
    aws_access_key = fields.Char(string="Amazon S3 Access Key", copy=False,
                                 help="Field used to store the Access Key for an Amazon S3 bucket.")
    aws_secret_access_key = fields.Char(string='Amazon S3 Secret Key',
                                        copy=False,
                                        help="Field used to store the Secret Key for an Amazon S3 bucket.")
    bucket_file_name = fields.Char(string='Bucket Name',
                                   help="Field used to store the name of an Amazon S3 bucket.")
    aws_folder_name = fields.Char(string='File Name',
                                  help="Field used to store the name of a folder in an Amazon S3 bucket.")

    @api.depends('dropbox_refresh_token')
    def _compute_is_dropbox_token_generated(self):
        """Set True if the dropbox refresh token is generated"""
        for rec in self:
            rec.is_dropbox_token_generated = bool(rec.dropbox_refresh_token)

    @api.depends('onedrive_access_token', 'onedrive_refresh_token')
    def _compute_is_onedrive_token_generated(self):
        """Set true if onedrive tokens are generated"""
        for rec in self:
            rec.is_onedrive_token_generated = bool(
                rec.onedrive_access_token) and bool(rec.onedrive_refresh_token)

    @api.depends('gdrive_access_token', 'gdrive_refresh_token')
    def _compute_is_google_drive_token_generated(self):
        """Set True if the Google Drive refresh token is generated"""
        for rec in self:
            rec.is_google_drive_token_generated = bool(
                rec.gdrive_access_token) and bool(rec.gdrive_refresh_token)

    def _compute_redirect_uri(self):
        """Compute the redirect URI for onedrive and Google Drive"""
        for rec in self:
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            rec.onedrive_redirect_uri = base_url + '/onedrive/authentication'
            rec.gdrive_redirect_uri = base_url + '/google_drive/authentication'

    @api.constrains('db_name')
    def _check_db_credentials(self):
        """Validate entered database name and master password"""
        query = """ SELECT datname FROM pg_database """
        self.env.cr.execute(query)
        database_list = [db['datname'] for db in self.env.cr.dictfetchall()]
        if self.db_name not in database_list:
            raise ValidationError(_("Invalid Database Name!"))
        try:
            odoo.service.db.check_super(self.master_pwd)
        except Exception:
            raise ValidationError(_("Invalid Master Password!"))

    @api.constrains('days_to_remove')
    def _check_days_to_remove(self):
        """Validate entered days to remove old database backups """
        if self.auto_remove and self.days_to_remove <= 0:
            raise ValidationError(_("Remove After Day must be greater "
                                    "than zero."))

    @api.constrains('backup_path')
    def _check_local_backup_path(self):
        """Validate Local storage backup path

        Checks for:
        1. Path must start with '/'
        2. Path must be absolute
        3. Check if we have permissions to create directory
        4. Path must not contain special characters
        5. Path must not be too long
        """
        for record in self:
            path = record.backup_path
            if not path:
                return

            # 1. Check if path starts with '/'
            if not path.startswith('/'):
                raise ValidationError(_(
                    "The backup path must start with '/'. "
                    "Example: /home/backup"
                ))

            # 2. Clean and normalize the path
            try:
                clean_path = os.path.abspath(os.path.normpath(path))
                if not clean_path.startswith('/'):
                    raise ValidationError(_(
                        "Invalid path format. Please provide an absolute path."
                    ))
            except Exception as e:
                raise ValidationError(_(
                    f"Invalid path format: {str(e)}"
                ))

            # 3. Check path length
            if len(clean_path) > 4096:  # Linux max path length
                raise ValidationError(_(
                    "Path is too long. Maximum allowed length is 4096 characters."
                ))

            # 4. Check for invalid characters
            invalid_chars = set('<>:"|?*\\')
            if any(char in path for char in invalid_chars):
                raise ValidationError(_(
                    "Path contains invalid characters. "
                    "The following characters are not allowed: < > : \" | ? * \\"
                ))

            # 5. Check parent directory permissions
            parent_dir = os.path.dirname(clean_path)
            try:
                if os.path.exists(parent_dir):
                    # Check if we can write to the existing parent directory
                    if not os.access(parent_dir, os.W_OK):
                        raise ValidationError(_(
                            f"Permission denied: Cannot write to '{parent_dir}'. "
                            f"Please check directory permissions."
                        ))
                else:
                    # Check if we can create directories in the closest existing parent
                    current_dir = parent_dir
                    while not os.path.exists(current_dir):
                        current_dir = os.path.dirname(current_dir)
                        if not current_dir or current_dir == '/':
                            break

                    if not current_dir or not os.access(current_dir, os.W_OK):
                        raise ValidationError(_(
                            f"Permission denied: Cannot create directories in '{current_dir}'. "
                            f"Please check permissions."
                        ))

            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(_(
                    f"Error validating backup path: {str(e)}"
                ))

    def action_s3cloud(self):
        """If it has aws_secret_access_key, which will perform s3cloud
         operations for connection test"""
        if self.aws_access_key and self.aws_secret_access_key:
            try:
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key)
                buckets = s3.buckets.all()
                bucket_found = False
                for bucket in buckets:
                    if self.bucket_file_name == bucket.name:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("Connection Test Succeeded!"),
                                'message': _(
                                    "Everything seems properly set up!"),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                if not bucket_found:
                    raise UserError(
                        _("Bucket not found. Please check the bucket name and try again."))
            except Exception as error:
                raise UserError(_("S3 Exception: %s", error))

    def action_nextcloud(self):
        """If it has next_cloud_password, domain, and next_cloud_user_name
         which will perform an action for nextcloud connection test"""
        if self.domain and self.next_cloud_password and self.next_cloud_user_name:
            try:
                # 1. Initialize the client
                # Note: nc_auth_user and nc_auth_pass are the standard parameters here.
                nc = Nextcloud(
                    nextcloud_url=self.domain,
                    nc_auth_user=self.next_cloud_user_name,
                    nc_auth_pass=self.next_cloud_password
                )

                # 2. Perform the test
                # listdir() is the nc-py-api equivalent of list_folders().
                # If this line executes without raising an exception, the connection is valid.
                nc.files.listdir('/')

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Connection Test Succeeded!"),
                        'message': _("Successfully connected to Nextcloud!"),
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                # 3. Handle Failures
                # nc-py-api will raise an exception for 401 Unauthorized, 404, or DNS issues.
                _logger.warning("Nextcloud connection test failed: %s", e)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Connection Test Failed!"),
                        'message': _("Error: %s") % str(e),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Configuration Error"),
                    'message': _("Domain, username, or password is missing."),
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def action_dropbox(self):
        """
        This method attempts to connect to Dropbox using the configured credentials
        and validate the connection by retrieving the current account information.
        """
        try:
            if not all([self.dropbox_client_key, self.dropbox_client_secret,
                        self.dropbox_refresh_token]):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Configuration Error"),
                        'message': _(
                            "Please configure all required Dropbox credentials."),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            dbx = dropbox.Dropbox(
                app_key=self.dropbox_client_key,
                app_secret=self.dropbox_client_secret,
                oauth2_refresh_token=self.dropbox_refresh_token
            )
            account = dbx.users_get_current_account()
            _logger.info(
                "Successfully connected to Dropbox account: %s",
                account.email
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Test Succeeded!"),
                    'message': _(
                        "Connected to Dropbox account: %s") % account.email,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            error_message = _(
                "An unexpected error occurred while testing the connection.")
            _logger.error("An error occurred while testing the connection")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Test Failed"),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }

        finally:
            try:
                if 'dbx' in locals():
                    dbx.close()
            except Exception as e:
                _logger.warning("Error closing Dropbox connection: %s", str(e))

    def action_get_dropbox_auth_code(self):
        """Open a wizards to set up dropbox Authorization code"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dropbox Authorization Wizard',
            'res_model': 'dropbox.auth.code',
            'view_mode': 'form',
            'target': 'new',
            'context': {'dropbox_auth': True}
        }

    def action_get_onedrive_auth_code(self):
        """Generate onedrive authorization code"""
        authority = \
            'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        action = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "cyllo_database_backup.action_view_db_backup_configure")
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url_return = (
                base_url + '/web#id=%d&action=%d&view_type=form&model=%s' %
                (self.id, action['id'], 'db.backup.configure'))
        state = {
            'backup_config_id': self.id,
            'url_return': url_return
        }
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.onedrive_client_key,
            'state': json.dumps(state),
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': base_url + '/onedrive/authentication',
            'prompt': 'consent',
            'access_type': 'offline'
        })
        auth_url = "%s?%s" % (authority, encoded_params)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def action_get_gdrive_auth_code(self):
        """Generate google drive authorization code"""
        action = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "cyllo_database_backup.action_view_db_backup_configure")
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url_return = (
                base_url + '/web#id=%d&action=%d&view_type=form&model=%s' %
                (self.id, action['id'], 'db.backup.configure'))
        state = {
            'backup_config_id': self.id,
            'url_return': url_return
        }
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.gdrive_client_key,
            'scope': 'https://www.googleapis.com/auth/drive '
                     'https://www.googleapis.com/auth/drive.file',
            'redirect_uri': base_url + '/google_drive/authentication',
            'access_type': 'offline',
            'state': json.dumps(state),
            'approval_prompt': 'force',
        })
        auth_url = "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def action_sftp_connection(self):
        """Test the sftp and ftp connection using entered credentials"""
        if self.backup_destination == 'sftp':
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(hostname=self.sftp_host, username=self.sftp_user,
                               password=self.sftp_password,
                               port=self.sftp_port)
                sftp = client.open_sftp()
                sftp.close()
            except Exception as e:
                raise UserError(_("SFTP Exception: %s", e))
            finally:
                client.close()
        elif self.backup_destination == 'ftp':
            try:
                ftp_server = ftplib.FTP()
                ftp_server.connect(self.ftp_host, int(self.ftp_port))
                ftp_server.login(self.ftp_user, self.ftp_password)
                ftp_server.quit()
            except Exception as e:
                raise UserError(_("FTP Exception: %s", e))
        title = _("Connection Test Succeeded!")
        message = _("Everything seems properly set up!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def generate_onedrive_refresh_token(self):
        """Generate onedrive access token from refresh token if expired"""
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'scope': ONEDRIVE_SCOPE,
            'grant_type': "refresh_token",
            'redirect_uri': base_url + '/onedrive/authentication',
            'refresh_token': self.onedrive_refresh_token
        }
        try:
            res = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data=data,
                headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in
                    else False,
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !",
                              error.response.content)
            raise error

    def get_onedrive_tokens(self, authorize_code):
        """Generate onedrive tokens from authorization code."""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        data = {
            'code': authorize_code,
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'grant_type': 'authorization_code',
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': base_url + '/onedrive/authentication'
        }
        try:
            res = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data=data,
                headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in
                    else False,
                })
        except requests.HTTPError as error:
            _logger.exception("Bad microsoft onedrive request : %s !",
                              error.response.content)
            raise error

    def generate_gdrive_refresh_token(self):
        """Generate Google Drive access token from refresh token if expired"""
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.gdrive_refresh_token,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data,
                                headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in
                    else False,
                })
        except requests.HTTPError as error:
            error_key = error.response.json().get("error", "nc")
            error_msg = _(
                "An error occurred while generating the token. Your"
                "authorization code may be invalid or has already expired [%s]."
                "You should check your Client ID and secret on the Google APIs"
                " plateform or try to stop and restart your calendar synchronisation.",
                error_key)
            raise UserError(error_msg)

    def get_gdrive_tokens(self, authorize_code):
        """Generate gdrive tokens from authorization code."""
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_drive/authentication'
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, params=data,
                                headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_refresh_token': response.get('refresh_token'),
                    'gdrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in
                    else False,
                })
        except requests.HTTPError:
            error_msg = _(
                "Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise UserError(error_msg)

    def get_dropbox_auth_url(self):
        """Return dropbox authorization url"""
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key, self.dropbox_client_secret,
            token_access_type='offline')
        auth_url = dbx_auth.start()
        return auth_url

    def set_dropbox_refresh_token(self, auth_code):
        """Generate and set the dropbox refresh token from authorization code"""
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key, self.dropbox_client_secret,
            token_access_type='offline')
        outh_result = dbx_auth.finish(auth_code)
        self.dropbox_refresh_token = outh_result.refresh_token

    def _schedule_auto_backup(self):
        """ This method retrieves records from the backup configuration model
        and schedules automatic database backups based on the specified backup
        destinations. For each record, it generates a unique backup filename
        and triggers the appropriate backup method based on the
        destination type."""
        records = self.search([])
        for record in records:
            backup_time = fields.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = "%s_%s.%s" % (record.db_name, backup_time,
                                            record.backup_format)
            record.backup_filename = backup_filename
            if record.backup_destination == 'local':
                self._backup_to_local(record, backup_filename)
            elif record.backup_destination == 'ftp':
                self._backup_to_ftp(record, backup_filename)
            elif record.backup_destination == 'sftp':
                self._backup_to_sftp(record, backup_filename)
            elif record.backup_destination == 'google_drive':
                self._backup_to_google_drive(record, backup_filename)
            elif record.backup_destination == 'dropbox':
                self._backup_to_dropbox(record, backup_filename)
            elif record.backup_destination == 'onedrive':
                self._backup_to_onedrive(record, backup_filename)
            elif record.backup_destination == 'next_cloud':
                self._backup_to_nextcloud(record, backup_time)
            elif record.backup_destination == 'amazon_s3':
                self._backup_to_amazons3(record, backup_time)

    def _backup_to_local(self, record, backup_filename):
        """ Function for performing a local backup.
        This method creates a backup of the database locally on the server.
        """
        try:
            if not os.path.isdir(record.backup_path):
                os.makedirs(record.backup_path)
            backup_file = os.path.join(record.backup_path, backup_filename)
            with open(backup_file, "wb") as f:
                odoo.service.db.dump_db(record.db_name, f, record.backup_format)
            self._post_message_to_channel(
                f'Database backup stored in location {record.backup_path}')
            # Remove older backups
            if record.auto_remove:
                for filename in os.listdir(record.backup_path):
                    file = os.path.join(record.backup_path, filename)
                    create_time = fields.datetime.fromtimestamp(
                        os.path.getctime(file))
                    backup_duration = fields.datetime.utcnow() - create_time
                    if backup_duration.days >= record.days_to_remove:
                        os.remove(file)
            if record.notify_user:
                self._success_mail_send(record)
        except Exception as e:
            record.generated_exception = e
            _logger.info('FTP Exception: %s', e)
            if record.notify_user:
                self._failure_mail_send(record)

    def _backup_to_ftp(self, record, backup_filename):
        """ Function for performing a backup to an FTP server.
        This method connects to an FTP server and uploads a database backup.
        """
        try:
            ftp_server = ftplib.FTP()
            ftp_server.connect(record.ftp_host, int(record.ftp_port))
            ftp_server.login(record.ftp_user, record.ftp_password)
            ftp_server.encoding = "utf-8"
            temp = tempfile.NamedTemporaryFile(
                suffix='.%s' % record.backup_format)
            try:
                ftp_server.cwd(record.ftp_path)
            except ftplib.error_perm:
                ftp_server.mkd(record.ftp_path)
                ftp_server.cwd(record.ftp_path)
            with open(temp.name, "wb+") as tmp:
                odoo.service.db.dump_db(record.db_name, tmp,
                                        record.backup_format)
            ftp_server.storbinary('STOR %s' % backup_filename,
                                  open(temp.name, "rb"))
            self._post_message_to_channel(
                f'Database backup stored in FTP Location {record.ftp_path}')
            if record.auto_remove:
                files = ftp_server.nlst()
                for f in files:
                    create_time = fields.datetime.strptime(
                        ftp_server.sendcmd('MDTM ' + f)[4:], "%Y%m%d%H%M%S")
                    diff_days = (fields.datetime.now() - create_time).days
                    if diff_days >= record.days_to_remove:
                        ftp_server.delete(f)
            ftp_server.quit()
            if record.notify_user:
                self._success_mail_send(record)
        except Exception as e:
            record.generated_exception = e
            _logger.info('FTP Exception: %s', e)
            if record.notify_user:
                self._failure_mail_send(record)

    def _backup_to_sftp(self, record, backup_filename):
        """ Function for performing a backup to an SFTP server.
        This method connects to an SFTP server and uploads
        a database backup. """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(hostname=record.sftp_host, username=record.sftp_user,
                           password=record.sftp_password,
                           port=record.sftp_port)
            sftp = client.open_sftp()
            temp = tempfile.NamedTemporaryFile(
                suffix='.%s' % record.backup_format)
            with open(temp.name, "wb+") as tmp:
                odoo.service.db.dump_db(record.db_name, tmp,
                                        record.backup_format)
            try:
                sftp.chdir(record.sftp_path)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    sftp.mkdir(record.sftp_path)
                    sftp.chdir(record.sftp_path)
            sftp.put(temp.name, backup_filename)
            self._post_message_to_channel(
                f'Database backup stored in SFTP Location {record.sftp_path}')
            if record.auto_remove:
                files = sftp.listdir()
                expired = list(filter(lambda fl: (fields.datetime.now() - fields.datetime.fromtimestamp(
                                sftp.stat(fl).st_mtime)).days >= record.days_to_remove, files))
                for file in expired:
                    sftp.unlink(file)
            sftp.close()
            if record.notify_user:
                self._success_mail_send(record)
        except Exception as e:
            record.generated_exception = e
            _logger.info('SFTP Exception: %s', e)
            if record.notify_user:
                self._failure_mail_send(record)
        finally:
            client.close()

    def _backup_to_google_drive(self, record, backup_filename):
        """  Function for performing a backup to Google Drive.
           This method creates a backup of the database and uploads
           it to Google Drive. """
        if not record.gdrive_token_validity:
            raise ValidationError('Please enter a valid Google Drive access token')
        if record.gdrive_token_validity <= fields.Datetime.now():
            record.generate_gdrive_refresh_token()
        temp = tempfile.NamedTemporaryFile(suffix='.%s' % record.backup_format)
        with open(temp.name, "wb+") as tmp:
            odoo.service.db.dump_db(record.db_name, tmp, record.backup_format)
        try:
            if record.gdrive_refresh_token:
                if record.gdrive_token_validity <= fields.Datetime.now():
                    record.generate_gdrive_refresh_token()
                headers = {
                    "Authorization": "Bearer %s" % record.gdrive_access_token}
                para = {
                    "name": backup_filename,
                    "parents": [record.google_drive_folder_key],
                }
                files = {
                    'data': ('metadata', json.dumps(para),
                             'application/json; charset=UTF-8'),
                    'file': open(temp.name, "rb")
                }
                twe = requests.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                    headers=headers, files=files)
                response = twe.json()
                error = response.get("error")
                if error:
                    record.generated_exception = error.get("message",
                                                           "Unknown error")
                    _logger.info('Google Drive Exception: %s',
                                 record.generated_exception)
                    if record.notify_user:
                        self._failure_mail_send(record)
                else:

                    field = response.get("id")
                    self._post_message_to_channel(
                        f"Database backup stored in Google Drive Location <a target='_blank' "
                        f"href='https://drive.google.com/file/d/{field}'>https://drive.google."
                        f"com/file/d/{field}'</a>")
                    if record.auto_remove:
                        query = "parents = '%s'" % record.google_drive_folder_key
                        files_req = requests.get(
                            "https://www.googleapis.com/drive/v3/files?q=%s" % query,
                            headers=headers)
                        files = files_req.json()['files']
                        for file in files:
                            file_date_req = requests.get("https://www.googleapis.com/drive/v3/files/%s?fields=createdTime"
                                                         %file['id'], headers=headers)
                            create_time = file_date_req.json()['createdTime'][:19].replace('T', ' ')
                            diff_days = ((fields.datetime.now() - fields.datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S'))
                                         .days)
                            if diff_days >= record.days_to_remove:
                                requests.delete(
                                    "https://www.googleapis.com/drive/v3/files/%s" %
                                    file['id'], headers=headers)
                    if record.notify_user:
                        self._success_mail_send(record)
            else:
                message = "Google drive Refresh Token Not generated"
                record.generated_exception = message
                _logger.info('Google Drive Exception: %s', message)
                if record.notify_user:
                    self._failure_mail_send(record)
        except Exception as e:
            record.generated_exception = e
            _logger.info('Google Drive Exception: %s', e)
            if record.notify_user:
                self._failure_mail_send(record)

    def _backup_to_dropbox(self, record, backup_filename):
        """ Function for performing a backup to Dropbox.This method creates
         a backup of the database and uploads it to Dropbox. """
        temp = tempfile.NamedTemporaryFile(
            suffix='.%s' % record.backup_format)
        with open(temp.name, "wb+") as tmp:
            odoo.service.db.dump_db(record.db_name, tmp, record.backup_format)
        try:
            dbx = dropbox.Dropbox(app_key=record.dropbox_client_key,
                                  app_secret=record.dropbox_client_secret,
                                  oauth2_refresh_token=record.dropbox_refresh_token)
            dropbox_destination = (
                    record.dropbox_folder + '/' + backup_filename)
            dbx.files_upload(temp.read(), dropbox_destination)
            self._post_message_to_channel(
                "Database backup stored in DropBox Loaction <a target='_blank' "
                f"href='https://www.dropbox.com/home/{record.dropbox_folder}?preview="
                f"{backup_filename}'>https://www.dropbox.com/home/{record.dropbox_folder}"
                f"?preview={backup_filename}'</a>")
            if record.auto_remove:
                files = dbx.files_list_folder(record.dropbox_folder)
                file_entries = files.entries
                expired_files = list(filter(
                    lambda fl: (
                                fields.datetime.now() - fl.client_modified).days >= record.days_to_remove,
                    file_entries))
                for file in expired_files:
                    dbx.files_delete_v2(file.path_display)
            if record.notify_user:
                self._success_mail_send(record)
        except Exception as error:
            record.generated_exception = error
            _logger.info('Dropbox Exception: %s', error)
            if record.notify_user:
                self._failure_mail_send(record)

    def _backup_to_onedrive(self, record, backup_filename):
        """ Function for performing a backup to Microsoft OneDrive.
        This method creates a backup of the database and uploads
        it to Microsoft OneDrive. """
        if record.onedrive_token_validity <= fields.Datetime.now():
            record.generate_onedrive_refresh_token()
        temp = tempfile.NamedTemporaryFile(suffix='.%s' % record.backup_format)
        with open(temp.name, "wb+") as tmp:
            odoo.service.db.dump_db(record.db_name, tmp, record.backup_format)
        headers = {
            'Authorization': 'Bearer %s' % record.onedrive_access_token,
            'Content-Type': 'application/json'}
        upload_session_url = (
                MICROSOFT_GRAPH_END_POINT +
                f"/v1.0/me/drive/root:/{record.onedrive_folder_key}/{backup_filename}:/createUploadSession"
        )
        try:
            upload_session = requests.post(
                upload_session_url,
                headers=headers,
                json={}  # required body, even if empty
            )
            upload_url = upload_session.json().get('uploadUrl')
            file_size = os.path.getsize(temp.name)
            with open(temp.name, "rb") as f:
                file_data = f.read()

            headers_upload = {
                'Content-Range': f'bytes 0-{file_size - 1}/{file_size}',
                'Content-Length': str(file_size)
            }
            res = requests.put(upload_url, headers=headers_upload,
                               data=file_data)
            upload_id = res.json()
            u_id = upload_id.get('createdBy')['user']['id']
            self._post_message_to_channel(
                f"Database backup stored in OneDrive Loaction <a target='_blank' href='https://onedrive.live.com/?cid={u_id}&id={u_id}%21130&parId={u_id}&o=OneUp'>https://onedrive.live.com/?cid={u_id}&id={u_id}%21130&parId={u_id}&o=OneUp'</a>")

            if record.auto_remove:
                list_url = (MICROSOFT_GRAPH_END_POINT +
                            "/v1.0/me/drive/items/%s/children" % record.onedrive_folder_key)
                response = requests.get(list_url, headers=headers)
                files = response.json().get('value')
                for file in files:
                    create_time = file['createdDateTime'][:19].replace('T', ' ')
                    diff_days = (
                            fields.datetime.now() - fields.datetime.strptime(
                        create_time, '%Y-%m-%d %H:%M:%S')).days
                    if diff_days >= record.days_to_remove:
                        delete_url = (
                                MICROSOFT_GRAPH_END_POINT + "/v1.0/me/drive/items/%s" %
                                file['id'])
                        requests.delete(delete_url, headers=headers)
            if record.notify_user:
                self._success_mail_send(record)
        except Exception as error:
            record.generated_exception = error
            _logger.info('Onedrive Exception: %s', error)
            if record.notify_user:
                self._failure_mail_send(record)

    def _backup_to_nextcloud(self, record, backup_time):
        """
        Function for NextCloud backup. This method performs a database
        backup and uploads it to a NextCloud server.
        :param record: A record from the backup configuration model.
        """
        if record.domain and record.next_cloud_password and record.next_cloud_user_name:
            try:
                # 1. Initialize single client
                nc = Nextcloud(
                    nextcloud_url=record.domain,
                    nc_auth_user=record.next_cloud_user_name,
                    nc_auth_pass=record.next_cloud_password
                )

                folder_name = record.nextcloud_folder_key

                # 2. Check if folder exists, create if not
                # listdir() will raise an error if the folder doesn't exist,
                # so we check root first.
                root_items = nc.files.listdir('/')
                if not any(item.name == folder_name and item.is_dir for item in
                           root_items):
                    nc.files.mkdir(folder_name)

                # 3. Create database dump in a temporary file
                suffix = f'.{record.backup_format}'
                remote_file_path = f"{folder_name}/{record.db_name}_{backup_time}{suffix}"

                with tempfile.NamedTemporaryFile(suffix=suffix,
                                                 delete=True) as temp:
                    # Odoo dumps the database into the temp file
                    odoo.service.db.dump_db(record.db_name, temp,
                                            record.backup_format)
                    temp.flush()  # Ensure all data is written to disk
                    temp.seek(0)  # Reset file pointer to beginning for reading

                    # 4. Upload to Nextcloud using upload_stream with file object
                    nc.files.upload_stream(remote_file_path, temp)

                # 5. Success Notifications
                full_remote_path = f"/{remote_file_path}"
                self._post_message_to_channel(
                    f'Database backup stored in NextCloud: {full_remote_path}')

                # 6. Auto-remove old backups
                if record.auto_remove:
                    backups = nc.files.listdir(folder_name)
                    for item in backups:
                        if item.is_dir:
                            continue

                        backup_date_str = self.extract_date_from_backup(
                            item.name)
                        if not backup_date_str:
                            continue

                        backup_date = fields.Date.from_string(backup_date_str)
                        days_diff = (fields.Date.today() - backup_date).days

                        if days_diff >= record.days_to_remove:
                            nc.files.delete(item.user_path)
                if record.notify_user:
                    self._success_mail_send(record)

            except Exception as error:
                record.generated_exception = str(error)
                _logger.error('NextCloud Backup Exception: %s', error)
                if record.notify_user:
                    self._failure_mail_send(record)
        else:
            _logger.warning(
                "Missing Nextcloud configuration for backup record: %s",
                record.id)

    @staticmethod
    def extract_date_from_backup(filename):
        parts = filename.split('_')
        for part in parts:
            if part.count('-') == 2 and len(part) == 10:
                try:
                    year, month, day = part.split('-')
                    if len(year) == 4 and len(month) == 2 and len(day) == 2:
                        return part
                except ValueError:
                    continue
        return None

    def _backup_to_amazons3(self, record, backup_time):
        """This method creates a backup of the database and uploads it to an
        Amazon S3 bucket specified in the given record. It also handles
        notifications and automatic removal of older backups if configured.
        @param record: The backup record containing configuration details. """
        if record.aws_access_key and record.aws_secret_access_key:
            try:
                # Create a boto3 client for Amazon S3 with provided
                # access key id and secret access key
                bo3 = boto3.client(
                    's3',
                    aws_access_key_id=record.aws_access_key,
                    aws_secret_access_key=record.aws_secret_access_key)
                # Create a boto3 resource for Amazon S3 with provided
                # access key id and secret access key
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=record.aws_access_key,
                    aws_secret_access_key=record.aws_secret_access_key)
                # Create a folder in the specified bucket, if it
                # doesn't already exist
                s3.Object(record.bucket_file_name,
                          record.aws_folder_name + '/').put()
                bucket = s3.Bucket(record.bucket_file_name)
                # Get all the prefixes in the bucket
                prefixes = set()
                for obj in bucket.objects.all():
                    key = obj.key
                    if key.endswith('/'):
                        prefix = key[:-1]  # Remove the trailing slash
                        prefixes.add(prefix)
                # If the specified folder is present in the bucket,
                # take a backup of the database and upload it to the
                #   S3 bucket
                if record.aws_folder_name in prefixes:
                    temp = tempfile.NamedTemporaryFile(
                        suffix='.%s' % record.backup_format)
                    with open(temp.name, "wb+") as tmp:
                        odoo.service.db.dump_db(record.db_name, tmp,
                                                record.backup_format)
                    backup_file_path = temp.name
                    remote_file_path = f"{record.aws_folder_name}/{record.db_name}_" \
                                       f"{backup_time}.{record.backup_format}"
                    s3.Object(record.bucket_file_name,
                              remote_file_path).upload_file(
                        backup_file_path)
                    self._post_message_to_channel(
                        f'Database backup stored in AmazonS3'
                        f' Loacation {remote_file_path}')
                    # If notify_user is enabled, email to the
                    # user notifying them about the successful backup
                    if record.notify_user:
                        self._success_mail_send(record)
                    # If auto_remove is enabled, remove the backups that
                    # are older than specified days from the S3 bucket
                    if record.auto_remove:
                        folder_path = record.aws_folder_name
                        response = bo3.list_objects(
                            Bucket=record.bucket_file_name,
                            Prefix=folder_path)
                        today = fields.date.today()
                        for file in response['Contents']:
                            file_path = file['Key']
                            last_modified = file['LastModified']
                            date = last_modified.date()
                            age_in_days = (today - date).days
                            if age_in_days >= record.days_to_remove:
                                bo3.delete_object(
                                    Bucket=record.bucket_file_name,
                                    Key=file_path)
            except Exception as error:
                # If any error occurs, set the 'generated_exception'
                record.generated_exception = error
                _logger.info('Amazon S3 Exception: %s', error)
                # If notify_user is enabled, send email to the user
                if record.notify_user:
                    self._failure_mail_send(record)

    def _success_mail_send(self, record):
        """Send a success email notification for a database backup."""
        mail_template_success = self.env.ref(
            'cyllo_database_backup.mail_template_database_backup_notification_successful')
        mail_template_success.send_mail(record.id,
                                        force_send=True)

    def _failure_mail_send(self, record):
        """ Send a failure email notification for a database backup."""
        mail_template_failed = self.env.ref(
            'cyllo_database_backup.mail_template_database_backup_notification_failed')
        mail_template_failed.send_mail(record.id, force_send=True)

    def _post_message_to_channel(self, body):
        """ Posts a message to a specific channel."""
        channel = self.env.ref(
            'cyllo_database_backup.discuss_channel_database_backup')
        channel.message_post(
            body=Markup(body),
            author_id=self.env.user.partner_id.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
