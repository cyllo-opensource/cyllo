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
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError


class DocumentWorkspace(models.Model):
    """ Model to store document workspace """
    _name = 'document.workspace'
    _description = 'Document Workspace'
    _inherit = 'mail.thread'

    name = fields.Char(required=True, help="Name of the WorkSpace.")
    display_name = fields.Char(string='Workspace', compute='_compute_display_name', help="Name of the workSpace.")
    company_id = fields.Many2one('res.company', help="WorkSpace belongs to this company",
                                 default=lambda self: self.env.company)
    description = fields.Text(help="Description about the workSpace")
    document_count = fields.Integer(compute='_compute_document_count',
                                    help="Number of documents uploaded under this workSpace")
    privacy_visibility = fields.Selection([
        ('followers', 'Invited internal users (private)'), ('employees', 'All internal users')],
        string='Visibility', required=True, default='employees',
        help='- Invited internal users: when following a workspace, internal users will get access to all of its '
             'documents without distinction \n\n All internal users: all internal users can access the workspace and'
             ' all of its documents without distinction.\n\n')
    google_drive_folder_id = fields.Char(string='Google drive folder id',
                                         help='Id of workspace in google drive if created', copy=False, readonly=True)
    onedrive_folder_id = fields.Char(string='One drive folder id', help='Id of workspace in one drive if created',
                                     copy=False, readonly=True)

    def _compute_document_count(self):
        """ Calculate the number of documents associated with this workspace. This function computes the count of
        documents that belong to the current workspace."""
        for record in self:
            record.document_count = self.env['document.file'].search_count(
                [('workspace_id', '=', self.id)])

    def write(self, vals):
        """Update the WorkSpace's name and rename corresponding folders in Google Drive and OneDrive if valid
        access tokens are available. This function updates the name of the document workspace and ensures that any
        corresponding folders in Google Drive and OneDrive are renamed accordingly. If valid access tokens are
        available for these cloud storage services, the function uses the tokens to perform the renaming.
        :param vals: A dictionary of values to update in the workspace.
        :type vals: dict
        :return: True if the write operation was successful.
        :rtype: bool
        :raises: UserError if an error occurs during the renaming process."""
        res = super(DocumentWorkspace, self).write(vals) if vals else True
        if vals.get('privacy_visibility') == 'followers':
            self.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        if vals.get('name'):
            for record in self.env['google.drive.connector'].search([('state', '=', 'connected')]):
                if record.google_drive_token_validity <= fields.Datetime.now():
                    record.generate_google_drive_refresh_token()
                access_token = record.google_drive_access_token
                try:
                    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
                    rename_metadata = {'name': vals.get('name')}
                    requests.patch(f'https://www.googleapis.com/drive/v3/files/{self.google_drive_folder_id}',
                                   headers=headers, json=rename_metadata)
                except Exception as e:
                    raise UserError(e)
            for rec in self.env['one.drive.connector'].search([('state', '=', 'connected')]):
                if rec.one_drive_token_validity <= fields.Datetime.now():
                    rec.generate_one_drive_refresh_token()
                access_token = rec.one_drive_access_token
                try:
                    headers = {"Authorization": f"Bearer {access_token}",
                               "Content-Type": "application/json"}
                    data = {"name": vals.get('name')}
                    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{self.onedrive_folder_id}"
                    requests.patch(url, headers=headers, json=data)
                except Exception as e:
                    raise UserError(e)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Create a document workspace and corresponding folders in Google Drive and OneDrive (if valid access tokens
        are available). This method creates a document workspace and, if valid access tokens for Google Drive and
        OneDrive are available, it also creates folders with the same name in these cloud storage services to
        organize documents associated with the workspace.
        :param vals_list: A list of dictionaries containing values for creating the workspace.
        :type vals_list: list of dict
        :return: The created document workspace record.
        :rtype: DocumentWorkspace
        :raises: UserError if an error occurs during folder creation or if access tokens are invalid or expired."""
        for record in self.env['google.drive.connector'].search([('state', '=', 'connected')]):
            if record.google_drive_token_validity <= fields.Datetime.now():
                record.generate_google_drive_refresh_token()
            access_token = record.google_drive_access_token
            file_id = vals_list[0].get('google_drive_folder_id')
            url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(url, headers=headers)
            if not response.status_code == 200:
                folder_metadata = {'name': vals_list[0].get('name'),
                                   'mimeType': 'application/vnd.google-apps.folder'}
                headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
                try:
                    response = requests.post('https://www.googleapis.com/drive/v3/files',
                                             headers=headers, json=folder_metadata)
                    if response.status_code == 200:
                        vals_list[0]['google_drive_folder_id'] = response.json()["id"]
                except requests.exceptions.RequestException as e:
                    raise UserError(e)
        for rec in self.env['one.drive.connector'].search([('state', '=', 'connected')]):
            if rec.one_drive_token_validity <= fields.Datetime.now():
                rec.generate_one_drive_refresh_token()
            try:
                access_token = rec.one_drive_access_token
                url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
                data = {"name": vals_list[0].get('name'), "folder": {}}
                headers = {"Authorization": f'Bearer {access_token}',
                           "Content-Type": "application/json"}
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 201:
                    vals_list[0]['onedrive_folder_id'] = response.json()["id"]
            except Exception as e:
                raise UserError(e)
        res = super(DocumentWorkspace, self).create(vals_list)
        return res

    def unlink(self):
        """Delete a document workspace and its corresponding folders in Google Drive and OneDrive (if they exist).
        This method deletes a document workspace and, if the workspace has associated folders in Google Drive and
        OneDrive, it deletes these folders as well. It ensures that the folders in cloud storage are removed when
        the workspace is deleted.
        :return: True if the document workspace is successfully deleted, otherwise raises a UserError in case of any
        errors during deletion.
        :rtype: bool
        :raises: UserError if an error occurs during folder deletion or if access tokens are invalid or expired."""
        for workspace in self:
            if workspace.google_drive_folder_id:
                for record in self.env['google.drive.connector'].search([('state', '=', 'connected')]):
                    if (record.google_drive_token_validity <= fields.Datetime.now()):
                        record.generate_google_drive_refresh_token()
                    url = f'https://www.googleapis.com/drive/v3/files/{workspace.google_drive_folder_id}'
                    headers = {'Authorization': f'Bearer {record.google_drive_access_token}'}
                    try:
                        requests.delete(url, headers=headers)
                    except requests.RequestException as e:
                        raise UserError(e)
            if workspace.onedrive_folder_id:
                for rec in self.env['one.drive.connector'].search([('state', '=', 'connected')]):
                    if rec.one_drive_token_validity <= fields.Datetime.now():
                        rec.generate_one_drive_refresh_token()
                    access_token = rec.one_drive_access_token
                    folder_id = workspace.onedrive_folder_id
                    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}"
                    headers = {"Authorization": f"Bearer {access_token}"}
                    try:
                        requests.delete(url, headers=headers)
                    except Exception as e:
                        raise UserError(e)
        return super().unlink()

    def action_button_view_document(self):
        """ Open the Kanban view of associated documents. This function opens the Kanban view displaying documents
        associated with the current workspace.
        :return: Action to open the Kanban view """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.file',
            'name': self.name,
            'view_mode': 'kanban,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('workspace_id', '=', self.id)]
        }

    @api.model
    def work_spaces(self):
        """ Retrieve and send workspace data to the front-end. This function searches for all existing document
        workspaces and prepares a list of dictionaries containing their IDs and names. This list is intended to be
        sent to the front-end for user display.
        :return: A list of dictionaries, each containing 'id' and 'name' keys
                 representing workspace IDs and names."""
        workspace_ids = self.env['document.workspace'].search([])
        workspace_list = [{'id': i.id, 'name': i.name} for i in workspace_ids]
        return workspace_list
