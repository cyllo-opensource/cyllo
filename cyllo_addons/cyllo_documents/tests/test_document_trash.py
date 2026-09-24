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
from odoo import fields
from odoo.tests import common


class TestDocumentTrash(common.TransactionCase):
    """Test class for document.trash related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.trash_doc = cls.env['document.trash'].create({
            'name': 'Test Document',
            'date': fields.Datetime.now(),
            'workspace_id': cls.workspace_id.id,
            'user_id': cls.env.user.id,
        })

    def test_action_restore_document(self):
        """Test the 'get_request' method.
        Verifies if the method correctly retrieves requests for the current
        user."""
        results = self.trash_doc.action_restore_document()
        self.assertEqual(results['name'], 'Trash')
        self.assertEqual(results['target'], 'main')

    def test_onchange_days(self):
        """Test the '_onchange_days' method."""
        self.trash_doc.days = 10
        self.trash_doc._onchange_days()
        expected_date = fields.Date.add(fields.Date.today(), days=10)
        self.assertEqual(expected_date, self.trash_doc.delete_date)

    def test_auto_delete_doc(self):
        """Test the 'auto_delete_doc' method."""
        self.trash_doc.auto_delete = True
        self.trash_doc.delete_date = fields.Date.today()
        self.trash_doc.auto_delete_doc()
        self.assertFalse(self.trash_doc.exists())
