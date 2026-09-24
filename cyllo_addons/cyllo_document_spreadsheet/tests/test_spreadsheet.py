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
from odoo.tests.common import TransactionCase


class TestSpreadsheet(TransactionCase):

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
        cls.spreadsheet = cls.env['spreadsheet.sheet'].create({
            'name': 'Test Spreadsheet Sheet',
            'is_document': True,
            'document_file_id': cls.doc_file.id,
        })

    def test_create(self):
        self.spreadsheet.create([{'name': 'Test Spreadsheet Sheet',
            'is_document': True,}])
        latest_attachment = self.env['ir.attachment'].search([], limit=1, order="id desc")
        latest_spreadsheet = self.env['spreadsheet.sheet'].search([], limit=1, order="id desc")
        new_doc_file = self.env['document.file'].search([], limit=1, order="id desc")
        self.assertEqual(latest_attachment.name, 'Test Spreadsheet Sheet')
        self.assertEqual(latest_attachment.res_model, 'document.file')
        self.assertEqual(latest_attachment.res_id, latest_spreadsheet.id)
        self.assertEqual(latest_attachment.public, True)
        self.assertEqual(latest_attachment.type, 'binary')
        workspace_id = self.env.ref(
            "cyllo_document_spreadsheet.document_workspace_spreadsheet")
        self.assertEqual(new_doc_file.name, 'Test Spreadsheet Sheet')
        self.assertEqual(new_doc_file.extension, 'xlsx')
        self.assertEqual(new_doc_file.date, fields.Datetime.now())
        self.assertEqual(new_doc_file.workspace_id, workspace_id)
        self.assertEqual(new_doc_file.attachment_id, latest_attachment)
        self.assertEqual(new_doc_file.is_excel, True)
        self.assertEqual(new_doc_file.spreadsheet_id, latest_spreadsheet)
        self.assertEqual(new_doc_file.attachment, latest_spreadsheet.binary_content)
        self.assertEqual(latest_spreadsheet.document_file_id, new_doc_file)

    def test_write(self):
        self.spreadsheet.name = 'Test Spreadsheet Sheet'
        rec = self.env['document.file'].sudo().search([('id', '=', self.spreadsheet.document_file_id.id)])
        self.assertEqual(rec.name, 'Test Spreadsheet Sheet')
        self.assertEqual(rec.attachment, False)



