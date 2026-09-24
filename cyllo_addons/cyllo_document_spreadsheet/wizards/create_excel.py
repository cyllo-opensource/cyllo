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
from odoo import fields, models
from odoo.exceptions import UserError


class CreateExcel(models.TransientModel):
    """ Wizard that used to create spreadsheet from kanban view"""
    _name = "create.excel"
    _description = "Wizard for Creating Excel Sheet"

    name = fields.Char(help="Name of the spreadsheet")

    def action_create_spreadsheet(self):
        """Creating spreadsheet from the wizard"""
        access_rights = self.env['ir.model.access'].sudo().search([
            ('model_id.model', '=', 'spreadsheet.sheet'),
            ('group_id', 'in', self.env.user.groups_id.ids),
            ('perm_read', '=', True),
        ], limit=1)
        if not access_rights:
            raise UserError(
                "You do not have access to the Spreadsheet module. "
                "Please contact your administrator to request access."
            )
        workspace_id = self.env.ref("cyllo_document_spreadsheet.document_workspace_spreadsheet")
        name = self.name or "Untitled spreadsheet"
        # Creating document for spreadsheet document
        document_id = self.env['document.file'].sudo().create({
            'name': name,
            'date': fields.Datetime.now(),
            'extension': 'xlsx',
            'workspace_id': workspace_id.id,
            'is_excel': True
        })
        spreadsheet_id = self.env['spreadsheet.sheet'].sudo().create({
            "name": name,
            'document_file_id': document_id.id,
        })
        return {
            'type': "ir.actions.client",
            'tag': "main_spreadsheet",
            'context': {
                'resId': spreadsheet_id.id,
            },
        }
