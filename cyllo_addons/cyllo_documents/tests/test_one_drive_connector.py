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
import os
from unittest.mock import patch
from odoo import fields
from odoo.tests import common


class TestOneDriveConnector(common.TransactionCase):
    """Test one drive connector"""

    @classmethod
    def setUpClass(cls):
        """Set up values"""
        super().setUpClass()
        with open(os.path.dirname(__file__) + '/test.jpg', 'rb') as file:
            cls.file_data_content = file.read()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.attachment_id = cls.env['ir.attachment'].sudo().create({
            'name': 'Test Attachment',
            'datas': base64.b64encode(cls.file_data_content),
            'res_model': 'document.file',
            'public': True,
        })
        cls.one_drive_connector = cls.env['one.drive.connector'].create({
            'name': 'Test Connection',
            'one_drive_client_key': 'test key',
            'one_drive_secret': 'test secret',
            'one_drive_token_validity': fields.Date.add(fields.Date.today(), days=7)
        })

    def test_generate_one_drive_refresh_token(self):
        """Test OneDrive refresh token generation."""
        with patch('requests.post') as mock_post:
            mock_response = {
                'access_token': 'sample_access_token',
                'refresh_token': 'sample_refresh_token',
                'expires_in': 3600
            }
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            self.one_drive_connector.generate_one_drive_refresh_token()
            self.assertEqual(self.one_drive_connector.one_drive_access_token, 'sample_access_token')
            self.assertEqual(self.one_drive_connector.one_drive_refresh_token, 'sample_refresh_token')

    def test_action_get_access(self):
        """Test action to get OneDrive access."""
        result = self.one_drive_connector.action_get_access()
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertEqual(result['target'], 'self')

    def test_action_export_files(self):
        """Test action to export files to OneDrive."""
        with patch('requests.put') as mock_put:
            mock_response = {
                'access_token': 'sample_access_token',
                'refresh_token': 'sample_refresh_token',
                'expires_in': 3600
            }
            mock_put.return_value.status_code = 201
            mock_put.return_value.json.return_value = mock_response
            self.one_drive_connector.document_file_ids = [fields.Command.create({
                'name': 'Test File',
                'attachment_id': self.attachment_id.id,
                'workspace_id': self.workspace_id.id,
                'mimetype': self.attachment_id.mimetype
            })]
            result = self.one_drive_connector.action_export_files()
            self.assertEqual(result['type'], 'ir.actions.client')
            self.assertEqual(result['tag'], 'display_notification')
            self.assertEqual(result['params']['type'], 'success')
            self.assertEqual(result['params']['sticky'], False)

    def test_auto_sync_export_one(self):
        """Test automatic synchronization of exporting to OneDrive."""
        self.one_drive_connector.state = 'connected'
        self.one_drive_connector.one_drive_access_token = 'Sample Token'
        self.workspace_id.onedrive_folder_id = 'Test Folder'
        with patch('requests.put') as mock_put:
            mock_response = {
                'access_token': 'sample_access_token',
                'refresh_token': 'sample_refresh_token',
                'id': 'mocked_file_key',
                'expires_in': 3600
            }
            mock_put.return_value.status_code = 201
            mock_put.return_value.json.return_value = mock_response
            self.one_drive_connector.document_file_ids = [fields.Command.create({
                'name': 'Test File',
                'attachment_id': self.attachment_id.id,
                'workspace_id': self.workspace_id.id,
                'mimetype': self.attachment_id.mimetype
            })]
            self.one_drive_connector.auto_sync_export_one()
            self.assertEqual(self.one_drive_connector.document_file_ids.one_drive_file_key, mock_response['id'])

    def test_sync_one_drive_workspace(self):
        """Test synchronization of OneDrive workspace."""
        self.one_drive_connector.env['ir.config_parameter'].set_param(
            'cyllo_documents.sync_one_drive_workspace',
            'cyllo_documents.sync_one_drive_workspace')
        self.one_drive_connector.state = 'connected'
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            with patch('requests.get') as mock_get:
                mock_response = {'value': [{'id': 'folder_id_1', 'name': 'Folder 1'}]}
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = mock_response
                self.one_drive_connector.sync_one_drive_workspace()
                self.one_drive_connector.workspace_id = self.workspace_id.search(
                    [('name', '=', mock_response['value'][0]['name'])]).id
                self.assertTrue(self.workspace_id, self.one_drive_connector.workspace_id)
