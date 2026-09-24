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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    version = fields.Char(
        string='Version',
        default='1',
        copy=False,
        help='Current revision/version of this product template.',
    )
    eco_ids = fields.One2many(
        'plm.eco',
        'product_id',
        string='Engineering Change Orders',
    )
    eco_count = fields.Integer(
        string='Engineering Changes',
        compute='_compute_eco_count',
    )

    @api.depends('eco_ids')
    def _compute_eco_count(self):
        """ Compute the total number of ECOs linked to this product. """
        for template in self:
            template.eco_count = len(template.eco_ids)

    def write(self, vals):
        """ Synchronize version updates with related BoMs. """
        res = super(ProductTemplate, self).write(vals)
        if 'version' in vals:
            for template in self:
                # Find related BoMs and synchronize version to keep them in sync
                boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', template.id)])
                if boms:
                    boms.write({'version': vals['version']})
        return res

    def action_view_plm_ecos(self):
        """ Return action window displaying linked ECO records. """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("cyllo_plm.action_view_plm_eco")
        action['domain'] = [('product_id', '=', self.id)]
        action['context'] = {
            'default_product_id': self.id,
        }
        return action

