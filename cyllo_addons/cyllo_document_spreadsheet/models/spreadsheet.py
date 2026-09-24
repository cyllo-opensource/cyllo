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
from odoo import api, fields, models


class Spreadsheet(models.Model):
    _inherit = 'spreadsheet.sheet'

    document_file_id = fields.Many2one('document.file',
                                       help="For getting record from document"
                                       )
    is_document = fields.Boolean(help="Identifying document element")

    @api.model_create_multi
    def create(self, vals_list):
        """ Created document while creating spreadsheet from the
                    spreadsheet module directly"""
        spreadsheet = super().create(vals_list)
        workspace_id = self.env.ref(
            "cyllo_document_spreadsheet.document_workspace_spreadsheet")
        if not spreadsheet.document_file_id:
            # Creating attachment for the document
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': spreadsheet.name,
                'res_model': 'document.file',
                'res_id': spreadsheet.id,
                'type': 'binary',
                'public': True,
            })
            # Creating document record for the spreadsheet
            document_id = self.env['document.file'].sudo().create({
                'name': spreadsheet.name,
                'extension': 'xlsx',
                'date': fields.Datetime.now(),
                'workspace_id': workspace_id.id,
                'attachment_id': attachment_id.id,
                'is_excel': True,
                "spreadsheet_id": spreadsheet.id
            })
            if spreadsheet.converted_binary_content:
                # Updating the file content and file id
                document_id.sudo().update({
                    'attachment': spreadsheet.converted_binary_content,
                })
            else:
                document_id.sudo().update({
                    'attachment': spreadsheet.binary_content,
                })
            spreadsheet.sudo().update({
                'document_file_id': document_id
            })
        return spreadsheet

    def write(self, vals):
        """To write in the spreadsheet which created from document"""
        rec = self.env['document.file'].sudo().search([('id', '=', self.document_file_id.id)])
        rec.write({
            'name': self.name,
            'attachment': self.converted_binary_content or self.binary_content,
        })
        return super().write(vals)
