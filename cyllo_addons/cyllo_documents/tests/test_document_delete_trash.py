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


class TestDocumentDeleteTrash(common.TransactionCase):
    """Test class for document.delete.trash related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for test cases."""
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document = cls.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': cls.workspace_id.id
        })
        cls.delete_doc = cls.env['document.delete.trash'].create({
            'document_file_id': cls.document.id
        })

    def test_action_document_move_trash(self):
        """Test the 'action_document_move_trash' method.
        Validates the functionality of moving a document to the trash,
        testing both locked and unlocked states."""
        self.document.is_locked = True
        result = self.delete_doc.action_document_move_trash()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.document.is_locked = False
        result = self.delete_doc.action_document_move_trash()
        self.assertEqual(result, None)

    def test_action_document_permanent_delete(self):
        """Test the 'action_document_permanent_delete' method.
           Verifies the permanent deletion of a document from the trash,
           testing both locked and unlocked states."""
        self.document.is_locked = True
        result = self.delete_doc.action_document_permanent_delete()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Lock')
        self.document.is_locked = False
        result = self.delete_doc.action_document_permanent_delete()
        self.assertEqual(result, None)