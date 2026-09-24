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
import os
from datetime import timedelta
from unittest.mock import patch
from odoo import fields
from odoo.tests import common


class TestGoogleDriveConnector(common.TransactionCase):
    """Test methods of Google Connector"""

    @classmethod
    def setUpClass(cls):
        """Setting up values"""
        super().setUpClass()
        cls.workspace = cls.env['document.workspace'].create({
            'name': 'Test Workspace'
        })
        cls.google_drive_connector = cls.env['google.drive.connector'].create({
            'name': 'Test Connector',
            'google_client_key': 'eouqdnqedoueq11',
            'google_client_secret': 'uuyiviuouhou5',
            'workspace_id': cls.workspace.id,
            'google_drive_token_validity': fields.Datetime.now()
        })

    def test_generate_google_drive_refresh_token(self):
        """Test the generation of Google Drive access token from the
         refresh token."""
        with patch('requests.post') as mock_post:
            mock_response = {
                'access_token': 'mock_access_token',
                'expires_in': 3600  # expiry time in seconds
            }
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            self.google_drive_connector.generate_google_drive_refresh_token()
            self.assertEqual(
                self.google_drive_connector.google_drive_access_token,
                'mock_access_token')

    def test_action_get_access(self):
        """Test the generation of OAuth2 authorization URL for Google
        Drive access."""
        action_result = self.google_drive_connector.action_get_access()
        self.assertIsInstance(action_result, dict)
        self.assertIn('type', action_result)
        self.assertEqual(action_result['type'], 'ir.actions.act_url')

    def test_action_export_files(self):
        """Test the export of selected files to Google Drive."""
        with patch('requests.post') as mock_post, \
                patch('odoo.fields.Date.add') as mock_date_add:
            with open(os.path.dirname(__file__) + '/test.jpg', 'rb') as file:
                self.file_data_content = file.read()
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = json.dumps({'id': 'mock_file_id'})
            mock_date_add.return_value = fields.datetime.now() + timedelta(
                days=1)
            self.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': 'Test Attachment',
                'datas': base64.b64encode(self.file_data_content),
                'res_model': 'document.file',
                'public': True,
            })
            self.google_drive_connector.document_file_ids = [fields.Command.create({
                'name': 'Test File',
                'workspace_id': self.workspace.id,
                'attachment_id': self.attachment_id.id,
            })]
            result = self.google_drive_connector.action_export_files()
            self.assertIn('type', result)
            self.assertEqual(result['tag'], 'display_notification')
