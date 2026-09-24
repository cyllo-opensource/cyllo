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

from odoo import api, fields, models, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    version = fields.Char(
        string='Version',
        default='1',
        copy=False,
        help='Current revision/version of this Bill of Materials.',
    )
    eco_ids = fields.One2many(
        'plm.eco',
        'bom_id',
        string='Engineering Change Orders',
    )
    eco_count = fields.Integer(
        string='Engineering Changes',
        compute='_compute_eco_count',
    )

    @api.depends('eco_ids')
    def _compute_eco_count(self):
        """ Compute the total number of ECOs linked to this BOM. """
        for bom in self:
            bom.eco_count = len(bom.sudo().eco_ids)

    def action_view_plm_ecos(self):
        """ Return action window displaying linked ECO records. """
        self.ensure_one()
        return {
            'name': _('ECOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco',
            'view_mode': 'tree,form',
            'domain' : [('bom_id', '=', self.id)],
        }

