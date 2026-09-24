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
from odoo.tests import TransactionCase, tagged
from unittest.mock import patch
import base64


@tagged('-at_install', 'post_install')
class TestAccountJournal(TransactionCase):
    """
    Test suite for validating invoice creation behavior in the `account.journal` model
    when using the invoice digitization flow.

    These tests ensure:
        - `_create_document_from_attachment()` is called correctly.
        - `process_auto_digitization()` is triggered for each created invoice.
        - The returned action structure changes depending on whether one or multiple invoices are created.
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepare reusable test data and environment once for the entire suite.
        Creates a journal, sample attachment, and sample invoices for testing digitization behaviors.
        """
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.Journal = cls.env['account.journal']
        cls.Move = cls.env['account.move']

        cls.journal = cls.Journal.create({
            'name': 'Test Digitization Journal',
            'type': 'purchase',
            'code': 'TDJ'
        })

        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'invoice.pdf',
            'type': 'binary',
            'datas': base64.b64encode(b"PDF Data").decode(),
            'mimetype': 'application/pdf'
        })

        cls.invoice1 = cls.Move.create({'move_type': 'in_invoice'})
        cls.invoice2 = cls.Move.create({'move_type': 'in_invoice'})

    def test_create_document_from_attachment(self):
        """
        Validate that:
            - A single invoice returns a form view action and triggers digitization once.
            - Multiple invoices return a list/kanban/form action and digitization is triggered.
            - `_create_document_from_attachment()` is always called as the main processing entry point.
        """
        with patch.object(
            self.journal.__class__,
            '_create_document_from_attachment',
            return_value=self.invoice1
        ) as mock_create_single, \
        patch.object(
            self.invoice1.__class__,
            'process_auto_digitization'
        ) as mock_digitize_single:

            action_single = self.journal.create_document_from_attachment([self.attachment.id])

        mock_create_single.assert_called_once()
        mock_digitize_single.assert_called_once()

        self.assertEqual(action_single['res_model'], 'account.move')
        self.assertIn('form', action_single.get('view_mode'))
        self.assertEqual(action_single['res_id'], self.invoice1.id)

        with patch.object(
            self.journal.__class__,
            '_create_document_from_attachment',
            return_value=self.invoice1 + self.invoice2
        ) as mock_create_multi, \
        patch.object(
            self.invoice1.__class__,
            'process_auto_digitization'
        ) as mock_digitize_multi:

            action_multi = self.journal.create_document_from_attachment([self.attachment.id])

        mock_create_multi.assert_called_once()
        mock_digitize_multi.assert_called()

        self.assertIn('list', action_multi.get('view_mode'))
        self.assertIn('kanban', action_multi.get('view_mode'))
        self.assertTrue(len(action_multi['domain']) > 0)
