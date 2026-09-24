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
from odoo.tests import common


class TestResConfigSettings(common.TransactionCase):
    """Test class for ResConfigSettings methods."""

    def setUp(self):
        """Set up test environment."""
        super(TestResConfigSettings, self).setUp()
        self.res_config_settings = self.env['res.config.settings'].create({})

    def test_action_google_drive_accounts(self):
        """Test action_google_drive_accounts method."""
        action = self.res_config_settings.action_google_drive_accounts()
        self.assertEqual(action['res_model'], 'google.drive.connector')
        self.assertIn('name', action)
        self.assertEqual(action['view_mode'], 'tree,form')
        self.assertEqual(action['target'], 'current')

    def test_action_one_drive_accounts(self):
        """Test action_one_drive_accounts method."""
        action = self.res_config_settings.action_one_drive_accounts()
        self.assertEqual(action['res_model'], 'one.drive.connector')
        self.assertIn('name', action)
        self.assertEqual(action['view_mode'], 'tree,form')
        self.assertEqual(action['target'], 'current')

    def test_create(self):
        """Test create method."""
        vals_list = [{'auto_sync_google_drive': 3, 'auto_sync_one_drive': 5}]
        self.res_config_settings.create(vals_list)
        google_drive_sync = self.env.ref(
            'cyllo_documents.ir_cron_sync_google_drive')
        one_drive_sync = self.env.ref('cyllo_documents.ir_cron_sync_one_drive')
        self.assertEqual(google_drive_sync.interval_type, 'days')
        self.assertEqual(google_drive_sync.interval_number, 3)
        self.assertEqual(one_drive_sync.interval_type, 'days')
        self.assertEqual(one_drive_sync.interval_number, 5)

    def test_is_crm_installed(self):
        """Test is_crm_installed method."""
        document_file = self.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': self.env['document.workspace'].create({
                'name': 'Test Workspace'
            }).id
        })
        vals_list = [{'module_crm': True}]
        self.res_config_settings.is_crm_installed(vals_list)
        for record in document_file:
            self.assertTrue(record.is_crm_install)

    def test_is_project_installed(self):
        """Test is_project_installed method."""
        document_file = self.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': self.env['document.workspace'].create({
                'name': 'Test Workspace'
            }).id
        })
        vals_list = [{'module_project': True}]
        self.res_config_settings.is_project_installed(vals_list)
        for record in document_file:
            self.assertTrue(record.is_project_install)
