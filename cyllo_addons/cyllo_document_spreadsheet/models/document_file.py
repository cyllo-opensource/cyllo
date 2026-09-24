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
import json
from odoo import _, api, fields, models


class DocumentFile(models.Model):
    """ Used for managing document files"""
    _inherit = "document.file"

    is_excel = fields.Boolean(help="For identifying excel record")
    spreadsheet_id = fields.Many2one("spreadsheet.sheet", ondelete="cascade")
    excel_thumbnail = fields.Image(help='Preview image of XLS', related="spreadsheet_id.image_1920")

    @api.model
    def action_upload_document(self, *args):
        """ Changing the default workspace for Excel into Spreadsheet
            :param args: Details of the uploaded file
        """
        value = args[0] if args else {}
        file_name = value.get('file_name') or ''
        file_data = value.get('file')
        if isinstance(file_name, str) and '.xlsx' in file_name and file_data:
            self.env['spreadsheet.sheet'].create({
                "is_document": True,
                "binary_content": file_data,
                "name": file_name,
            })
        else:
            return super().action_upload_document(*args)

    def download_xlsx_record(self):
        """To download the clicked Xlsx file"""
        spreadsheet_id = self.env['spreadsheet.sheet'].sudo().search([('document_file_id', '=', self.id)])
        return {
            'type': "ir.actions.client",
            'tag': "download_spreadsheet",
            'params': {
                'name': spreadsheet_id.name,
                'files': json.dumps(spreadsheet_id.sheet_json)
            },
        }

    def unlink(self):
        """ Passing spreadsheet content to the trash while moving Excel
            file to the trash"""
        if self.extension == "xlsx":
            spreadsheet_id = self.env['spreadsheet.sheet'].search(
                [('document_file_id', '=', self.id)])
            trash_id = self.env['document.trash'].sudo().search(
                [('doc_no', '=', self.id)])
            # Updating trash with spreadsheet content
            trash_id.update({
                'spreadsheet_data': spreadsheet_id.converted_binary_content,
                'spreadsheet_id':spreadsheet_id.id
            })
        return super(DocumentFile, self).unlink()

    @api.model
    def download_zip_function(self, document_selected):
        """ For downloading multiple file as a zip
            :param document_selected: Ids of the selected documents
        """
        for document in self.sudo().browse(document_selected):
            if document.extension == "xlsx":
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'message': _(
                            "Multiple file download is not available for excel"
                            " files.Please download individually"),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
        return super(DocumentFile, self).download_zip_function(
            document_selected)
