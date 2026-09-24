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
import logging
import json
from odoo import _
from odoo.tests.common import TransactionCase
_LOGGER = logging.getLogger(__name__)


class TestDocumentFile(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.doc_file = cls.env['document.file'].create({
            'name': 'XYZ Report.xlsx',
            'extension': "xlsx",
            'workspace_id': cls.workspace_id.id,
            'is_excel': True,
        })
        with open(os.path.dirname(__file__) + '/test_document_file.py', 'rb') as file:
            cls.file_data_content = file.read()

    def test_action_upload_document(self):
        self.doc_file.action_upload_document({
            'file_name': self.doc_file.name,
            'file': base64.b64encode(self.file_data_content),
            'workspace_id': self.doc_file.workspace_id.id
        })
        latest_spreadsheet = self.env['spreadsheet.sheet'].search([], limit=1, order="id desc")
        self.assertEqual(latest_spreadsheet.is_document, True)
        self.assertEqual(latest_spreadsheet.binary_content, base64.b64encode(self.file_data_content))
        self.assertEqual(latest_spreadsheet.name, self.doc_file.name)

    def test_download_xlsx_record(self):
        spreadsheet_id = self.env['spreadsheet.sheet'].sudo().search([('document_file_id', '=', self.doc_file.id)])
        self.assertEqual(self.doc_file.download_xlsx_record(), {
            'type': "ir.actions.client",
            'tag': "download_spreadsheet",
            'params': {
                'name': spreadsheet_id.name,
                'files': json.dumps(spreadsheet_id.sheet_json)
            },
        })

    def test_download_zip_function(self):
        self.assertEqual(self.doc_file.download_zip_function(self.doc_file.ids), {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'message': _(
                            "Multiple file download is not available for excel"
                            " files.Please download individually"),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                })


