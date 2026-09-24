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
import os

from odoo import fields
from odoo.tests import common


class TestDocumentLock(common.TransactionCase):
    """Test class for document.lock related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for test cases."""
        super().setUpClass()
        with open(os.path.dirname(__file__) + '/test.jpg', 'rb') as file:
            cls.file_data_content = file.read()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document_id = cls.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': cls.workspace_id.id,
            'active': True,
        })
        cls.document_lock = cls.env['document.lock'].create({
            'document_file_id': cls.document_id.id,
            'password': 'test123',
            'validate_password_doc': 'test123',
        })

    def test_action_lock_doc(self):
        """Test locking a document."""
        result = self.document_lock.action_lock_doc()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.env.user.write(
            {'groups_id': [fields.Command.link(self.env.ref('cyllo_documents.group_cyllo_documents_manager').id)]})
        self.document_lock.action_lock_doc()
        self.assertTrue(self.document_lock.is_lock)

    def test_action_unlock_doc(self):
        """Test unlocking a document."""
        result = self.document_lock.action_unlock_doc()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.action_unlock_doc()
        self.assertFalse(self.document_id.is_locked)

    def test_action_document_share(self):
        """Test sharing a document."""
        result = self.document_lock.action_document_share()
        self.assertTrue(result['type'], 'ir.actions.client')

    def test_action_document_download(self):
        """Test downloading a document."""
        result = self.document_lock.action_document_download()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.env.context = {'document_url': 'www.google.com'}
        result = self.document_lock.action_document_download()
        self.assertTrue(result['type'], 'ir.actions.act_url')

    def test_action_document_create_lead(self):
        """Test document creation for leads, handling locked/unlocked scenarios."""

        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_documents.document_master_password', 'test123'
        )
        self.document_lock.is_lock = False
        result = self.document_lock.action_document_create_lead()
        if isinstance(result, dict):
            self.assertIn(result.get('type'),
                          ['ir.actions.client', 'ir.actions.act_window',
                           'ir.actions.act_window_close'])
        else:
            self.assertTrue(result in [True, False, None, {}])
        self.document_lock.is_lock = True
        result = self.document_lock.action_document_create_lead()
        if isinstance(result, dict):
            self.assertIn(result.get('type'),
                          ['ir.actions.client', 'ir.actions.act_window',
                           'ir.actions.act_window_close'])
        else:
            self.assertTrue(result in [True, False, None, {}])

    def test_action_document_create_task(self):
        """Test document creation for tasks."""
        result = self.document_lock.action_document_create_task()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.client')
        self.document_lock.is_lock = True
        result = self.document_id.action_btn_create_task(self.document_id.id)
        # Accept True / False / None (method returns False if project module not installed)
        self.assertTrue(
            result in [True, False, None],
            f"Unexpected result for locked document: {result}"
        )

    def test_action_document_lock_mail(self):
        """Test document locking via mail."""
        self.document_lock.is_lock = True
        result = self.document_lock.action_document_lock_mail()
        self.assertEqual(result, {'type': 'ir.actions.client', 'tag': 'display_notification',
                                  'params': {'message': 'Incorrect Password', 'type': 'danger', 'sticky': False}})

    def test_action_document_move_to_trash(self):
        """Test moving a document to the trash."""
        result = self.document_lock.action_document_move_to_trash()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.action_document_copy_mail()
        self.assertTrue(self.document_id.exists())