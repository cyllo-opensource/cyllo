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
from odoo import fields, models, _


class DocumentTrash(models.Model):
    """ Manage item moved to the trash.Restore the item from the trash """
    _inherit = "document.trash"

    spreadsheet_data = fields.Binary(help="Stores spreadsheet data into trash")
    spreadsheet_id = fields.Many2one(comodel_name='spreadsheet.sheet')

    def action_restore_document(self):
        """ Function helps to restore the moved content from the
            trash
            :return : Returns the tree view of the remaining trash items"""
        doc_id = self.env['document.file'].sudo().create({
            # Creating document corresponding to the trash
            'name': self.name,
            'extension': self.extension,
            'attachment': self.attachment,
            'date': fields.Date.today(),
            'workspace_id': self.workspace_id.id,
            'user_id': self.user_id.id,
            'content_type': self.content_type,
            'brochure_url': self.brochure_url,
            'active': self.active,
            'mimetype': self.mimetype,
            'description': self.description,
            'content_url': self.content_url,
            'user_ids': self.user_ids.ids,
            'partner_id': self.partner_id,
            'days': self.days,
        })
        if doc_id.extension == 'xlsx':
            # Updating spreadsheet content with content that stored
            # in trash while deleting
            spreadsheet_id = self.env['spreadsheet.sheet'].sudo().search([('id', '=', self.spreadsheet_id.id)])
            spreadsheet_id.sudo().update({
                'converted_binary_content': self.spreadsheet_data,
                'document_file_id': doc_id.id
            })
        else:
            # Creating new attachment for the document file
            attachment_id = self.env['ir.attachment'].sudo().create(
                {'name': self.name,
                 'datas': self.attachment,
                 'res_model': 'document.file',
                 'res_id': self.id,
                 'type': 'binary',
                 'create_uid': self.env.uid,
                 'public': True
                 }
            )
            doc_id.attachment_id = attachment_id.id
        self.sudo().unlink()  # Delete the current trash contents
        return {
            'name': _('Trash'),
            'target': 'main',
            'view_mode': 'tree,form',
            'res_model': 'document.trash',
            'type': 'ir.actions.act_window',
        }
