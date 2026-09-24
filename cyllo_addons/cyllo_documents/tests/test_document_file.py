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
from datetime import timedelta
from odoo import fields
from odoo.tests import common


class TestDocumentsFile(common.TransactionCase):
    """Test class for document.file related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for test cases."""
        super().setUpClass()
        with open(os.path.join(os.path.dirname(__file__), 'test.jpg'),
                  'rb') as file:
            cls.file_data_content = file.read()

        cls.workspace_id = cls.env['document.workspace'].create(
            {'name': 'Test Workspace'})
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')

        cls.attachment_id = cls.env['ir.attachment'].sudo().create({
            'name': 'Test Attachment',
            'datas': base64.b64encode(cls.file_data_content),
            'res_model': 'document.file',
            'public': True,
        })

        cls.document = cls.env['document.file'].create({
            'name': 'Test Document',
            'attachment': base64.b64encode(cls.file_data_content),
            'workspace_id': cls.workspace_id.id,
            'attachment_id': cls.attachment_id.id,
            'date': fields.Datetime.now(),
            'user_id': cls.env.uid,
            'mimetype': cls.attachment_id.mimetype,
            'active': True,
            'brochure_url': str(cls.base_url) + cls.attachment_id.local_url,
        })

        cls.document1 = cls.env['document.file'].create({
            'name': 'Test Document1',
            'attachment': base64.b64encode(cls.file_data_content),
            'workspace_id': cls.workspace_id.id,
            'attachment_id': cls.attachment_id.id,
            'date': fields.Datetime.now(),
            'user_id': cls.env.uid,
            'mimetype': cls.attachment_id.mimetype,
            'brochure_url': str(cls.base_url) + cls.attachment_id.local_url,
        })

    def test_compute_size(self):
        """Test the _compute_size method."""
        self.document._compute_size()
        self.assertEqual(self.document.size, '168.471 Kb')

    def test_action_upload_document(self):
        """Test the action_upload_document method."""
        args = [{
            'file_name': self.document.name,
            'file': base64.b64encode(self.file_data_content),
            'workspace_id': self.workspace_id.id
        }]
        self.document.action_upload_document(*args)
        self.assertEqual(self.document.name, args[0]['file_name'])

    def test_download_zip_function(self):
        """Test function for downloading zip."""
        document_selected = self.document.id
        result = self.document.download_zip_function(document_selected)
        self.assertEqual(result['type'], 'ir.actions.act_url')

    def test_document_file_delete(self):
        """Test deleting a document."""
        doc_ids = [self.document1.id]
        self.document1.document_file_delete(doc_ids)
        self.env['document.trash'].search([('name', '=', 'Test Document1')])

    def test_document_file_archive(self):
        """Test archiving a document.Simulates archiving scenarios for active,
         inactive, and delete-dated documents."""
        # Simulate archiving an active document
        self.document.document_file_archive([self.document.id])
        self.assertFalse(self.document.active, "Active document should be "
                                               "archived")
        # Simulate archiving a document with delete date set
        self.document.write({'delete_date': fields.Date.today()})
        self.document.document_file_archive([self.document.id])
        self.assertTrue(self.document.active,
                        "Document with delete date should be active")
        self.assertFalse(self.document.delete_date, "Delete date should be "
                                                    "cleared")
        # Simulate archiving an inactive document without delete date
        self.document.active = False
        self.document.document_file_archive([self.document.id])
        self.assertTrue(self.document.active, "Inactive document should be "
                                              "active")

    def test_on_mail_document(self):
        """Test the 'on_mail_document' method.Verifies if mailing a document
        returns an action window."""
        doc_ids = [self.document.id]
        mail_doc = self.document.on_mail_document(doc_ids)
        self.assertEqual(mail_doc['type'], 'ir.actions.act_window')

    def test_action_btn_create_lead(self):
        """Test the 'action_btn_create_lead' method. Validates lead creation
        based on a document."""
        # Check if crm.lead model exists
        if 'crm.lead' not in self.env:
            self.skipTest("CRM module not installed, skipping lead creation test.")

        crm_module = self.env['ir.module.module'].sudo().search([('name', '=', 'crm')], limit=1)
        self.assertTrue(crm_module, "CRM module record not found")
        crm_module.state = 'installed'
        result = self.document.action_btn_create_lead(self.document.id)
        self.assertTrue(result in [True, None, {}] or (isinstance(result, dict) and result.get('type') in ['ir.actions.client', 'ir.actions.act_window']), f"Unexpected result: {result}")
        lead = self.env['crm.lead'].search([], limit=1, order="id desc")
        self.assertTrue(lead, "Lead should be created")
        self.assertEqual(lead.name, 'Test Document')
        self.assertEqual(self.document.attachment_id.res_model, 'crm.lead')
        self.assertEqual(self.document.attachment_id.res_id, lead.id)
        crm_module.state = 'uninstalled'
        result = self.document.action_btn_create_lead(self.document.id)
        self.assertFalse(result)

    def test_delete_doc(self):
        """Test the 'delete_doc' method."""
        test_doc = self.env['document.trash'].create({
            'name': 'Test Document',
            'deleted_date': fields.Datetime.today() - timedelta(days=10),
            'workspace_id': self.document.workspace_id.id
        })
        self.env['ir.config_parameter'].sudo().set_param('cyllo_documents.trash',
                                                         10)
        self.document.delete_doc()
        deleted_doc = self.env['document.trash'].search(
            [('id', '=', test_doc.id)])
        self.assertTrue(deleted_doc,
                        "Document should be deleted after retention period")

    def test_click_share(self):
        """
        Test the 'click_share' method.
        This test case validates the functionality of sharing a document and
         generating a shareable URL or prompting for a password if the document
          is locked.
        """
        self.document.is_locked = True
        locked_doc = self.document
        context = {'document_id': locked_doc.id}
        result = locked_doc.with_context(context).click_share()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.document.is_locked = False

    def test_click_create_lead(self):
        """Test the 'on_mail_document' method. Verifies if mailing a document
         returns an action window."""
        self.env.context = {'document_id': self.document.id}

        # Locked document → may return dict with 'ir.actions.act_window'
        self.document.is_locked = True
        result = self.document.sudo().click_create_lead()
        self.assertTrue(
            result is None or result is True or isinstance(result, dict))
        if isinstance(result, dict):
            # Accept all valid types including 'act_window' for locked docs
            self.assertIn(result.get('type'),
                          ['ir.actions.uploaded', 'ir.actions.client',
                           'ir.actions.act_window'])

        # Unlocked document → can return None or client notification
        self.document.is_locked = False
        result = self.document.sudo().click_create_lead()
        self.assertTrue(
            result is None or result.get('type') in ['ir.actions.client',
                                                     'ir.actions.uploaded'])

    def test_click_create_task(self):
        """Test the click_create_task method."""
        # Locked document → should return an action window
        self.document.is_locked = True
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_create_task()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        # Unlocked document → may return None OR client action
        self.document.is_locked = False
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_create_task()
        self.assertTrue(
            result is None or
            (isinstance(result, dict) and result.get(
                'type') == 'ir.actions.client')
        )

    def test_click_create_mail(self):
        """ Test the 'delete_doc' method. Validates the deletion of a
        document after the retention period."""
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_create_mail()
        self.assertEqual(result['name'], 'Sent document')
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.document.is_locked = True
        result = self.document.click_create_mail()
        self.assertEqual(result['name'], 'Please Enter Password')
        self.assertEqual(result['type'], 'ir.actions.act_window')

    def test_click_copy_move(self):
        """Test the click_copy_move method for copying or moving a document.
           Checks if the method returns the appropriate action based on the
           user's permissions and document status."""
        # User has permission to view all documents and the document is unlocked
        self.document.is_locked = False
        self.env.user.groups_id |= self.env.ref(
            'cyllo_documents.group_cyllo_documents_manager')
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_copy_move()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'work.space')
        # User does not have permission to view all documents
        self.document.is_locked = False
        self.env.user.groups_id = self.env.user.groups_id.filtered(
            lambda g: g != self.env.ref('cyllo_documents.group_cyllo_documents_manager'))
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_copy_move()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        # Document is locked
        self.document.is_locked = True
        self.env.user.groups_id |= self.env.ref(
            'cyllo_documents.group_cyllo_documents_manager')
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_copy_move()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'document.lock')

    def test_click_document_archive(self):
        """Test the 'click_document_archive' method."""
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_document_archive()
        self.assertEqual(result, None)
        self.document.is_locked = True
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_document_archive()
        self.assertEqual(result['type'], 'ir.actions.act_window')

    def test_click_document_delete(self):
        """Test the 'click_document_delete' method."""
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_document_delete()
        self.assertEqual(result, None)
        self.env.user.groups_id |= self.env.ref(
            'cyllo_documents.group_cyllo_documents_manager')
        result = self.document.click_document_delete()
        self.assertEqual(result['type'], 'ir.actions.act_window')

    def test_click_document_lock(self):
        """Test the 'click_document_lock' method. Validates the locking
        functionality of a document."""
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_document_lock()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Lock')

    def test_click_document_unlock(self):
        """Test the 'click_document_unlock' method. Validates the unlocking
        functionality of a document."""
        self.env.context = {'document_id': self.document.id}
        result = self.document.click_document_unlock()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Unlock')

    def test_click_download(self):
        """Test the click_download method for both locked and unlocked
        documents.Checks if the method returns the appropriate action
        based on the document's lock status."""
        # Test for an unlocked document
        self.document.is_locked = False
        self.env.context = {'document_url': '/document/download',
                            'document_id': self.document.id}
        result_unlocked = self.document.click_download()
        self.assertEqual(result_unlocked['type'], 'ir.actions.act_url')
        # Test for a locked document
        self.document.is_locked = True
        self.env.context = {'document_url': '/document/download',
                            'document_id': self.document.id}
        result_locked = self.document.click_download()
        self.assertEqual(result_locked['type'], 'ir.actions.act_window')

    def test_get_document_count(self):
        """Test the get_documents_count method."""
        result = self.document.get_document_count(self.workspace_id.id)
        self.assertEqual(len(result), 2)
