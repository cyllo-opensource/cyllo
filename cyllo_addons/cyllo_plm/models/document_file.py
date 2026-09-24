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

from odoo import fields, models, api
from odoo.http import request


class DocumentFile(models.Model):
    _inherit = 'document.file'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        help='Engineering Change Order associated with this document.',
        ondelete='cascade'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Create document files and link them to the active Engineering Change Order (ECO)
        and default PLM workspace if applicable.
        """
        eco_id = self.env.context.get('default_eco_id')
        if not eco_id and self.env.context.get('active_model') == 'plm.eco':
            eco_id = self.env.context.get('active_id')
        if not eco_id:
            try:
                if request and request.session.get('active_eco_id'):
                    eco_id = request.session.get('active_eco_id')
            except Exception:
                pass
        plm_workspace = self.env.ref("cyllo_plm.document_workspace_plm", raise_if_not_found=False)
        plm_workspace_id = plm_workspace.id if plm_workspace else False
        for vals in vals_list:
            if eco_id:
                if not vals.get('eco_id'):
                    vals['eco_id'] = eco_id
                if plm_workspace_id:
                    vals['workspace_id'] = plm_workspace_id
        return super().create(vals_list)