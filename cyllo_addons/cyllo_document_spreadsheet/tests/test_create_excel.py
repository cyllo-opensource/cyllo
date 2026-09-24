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


class TestCreateExcel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.excel = cls.env['create.excel'].create({
            'name': 'XYZ Report.xlsx',
        })

    def test_action_create_spreadsheet(self):
        val = self.excel.action_create_spreadsheet()
        workspace_id = self.env.ref("cyllo_document_spreadsheet.document_workspace_spreadsheet")
        new_doc_file = self.env['document.file'].search([], limit=1, order="id desc")
        new_spreadsheet = self.env['spreadsheet.sheet'].search([], limit=1, order="id desc")
        self.assertEqual(new_doc_file.name, self.excel.name)
        self.assertEqual(new_doc_file.date, fields.Datetime.now())
        self.assertEqual(new_doc_file.extension, 'xlsx')
        self.assertEqual(new_doc_file.workspace_id, workspace_id.id)
        self.assertEqual(new_doc_file.is_excel, True)
        self.assertEqual(new_spreadsheet.name, self.excel.name)
        self.assertEqual(new_spreadsheet.document_file_id, new_doc_file.id)
        self.assertEqual(val, {
            'type': "ir.actions.client",
            'tag': "main_spreadsheet",
            'context': {
                'resId': new_spreadsheet.id,
            },
        })
