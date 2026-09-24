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


class TestRequestDocument(common.TransactionCase):
    """Test class for request.document related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document = cls.env['request.document'].create({
            'user_id': cls.env.user.id,
            'needed_doc': 'Document XYZ',
            'workspace_id': cls.workspace_id.id
        })

    def test_action_send_document_request(self):
        """ Test the 'action_send_document_request' method.
            Verifies if a document request email is sent correctly."""
        self.document.user_id = self.env.user.id
        # Call the method to send the document request
        self.document.action_send_document_request()
        # Assert that a mail object is created and sent successfully
        sent_mail = self.env['mail.mail'].sudo().search(
            [('subject', '=', 'Document Request')])
        self.assertTrue(sent_mail, "Mail should be sent")
        self.assertEqual(sent_mail.subject, 'Document Request',
                         "Subject should match")
        self.assertEqual(sent_mail.email_to, self.env.user.partner_id.email,
                         "Recipient should match")

    def test_get_request(self):
        """Test the 'get_request' method."""
        requests = self.document.get_request()
        self.assertEqual(requests[0]['needed_doc'], 'Document XYZ')
        self.assertEqual(requests[0]['workspace'], 'Test Workspace')

    def test_document_request_accept_smart_button(self):
        """Test accepting document request via wizard and smart button action/count computation."""
        self.assertEqual(self.document.document_count, 0)
        accept_wizard = self.env['document.request.accept'].create({
            'document_request_id': self.document.id,
            'workspace_id': self.workspace_id.id,
            'filename': 'test_doc.txt',
            'document_file': b'VGVzdCBDb250ZW50',
        })
        accept_wizard.action_accept_request()
        self.assertEqual(self.document.state, 'accepted')
        self.assertEqual(self.document.document_count, 1)

        action = self.document.action_view_documents()
        self.assertEqual(action['res_model'], 'document.file')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], self.document.document_file_ids.id)
