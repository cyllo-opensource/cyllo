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
import uuid
import warnings

from odoo import _, api, fields, models
from odoo.http import request


class DocumentShare(models.Model):
    """model to share all shared document dats"""
    _name = 'document.share'
    _description = 'Document Share'

    url = fields.Char(string='File Url', readonly=True, help="Document Public URL")
    document_ids = fields.Many2many('document.file', string="Document Files", help="Related documents")
    user_ids = fields.Many2many('res.users', string="Users", help="Users associated with this record")
    unique_id_access = fields.Char(string='Unique Access ID', readonly=True, help="Unique identifier for access")

    @api.model
    def create_url(self, document_ids):
        """functon to create unique id and sharable urls for selected documents"""
        warnings.warn(f"Deprecated {self._name}.create_url(), use {self._name}.share_url() instead", DeprecationWarning)
        return self.share_url(document_ids)

    def share_url(self, document_ids):
        """functon to create unique id and sharable urls for selected documents"""
        unique_id_access = uuid.uuid4()
        url = f"""{request.httprequest.host_url[:-1]}/web/content/share/?unique={unique_id_access}"""
        self.create({'url': url, 'document_ids': document_ids, 'unique_id_access': unique_id_access})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share'),
            'res_model': 'document.share',
            'view_mode': 'form',
            'target': 'new',
            'views': [[False, "form"]],
            'context': {'default_url': url}
        }
