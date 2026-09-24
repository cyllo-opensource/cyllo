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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qcp_count = fields.Integer(compute='_compute_quality_control_points')
    quality_control_point_ids = fields.Many2many('quality.control.point', compute='_compute_quality_control_points')

    def _compute_quality_control_points(self):
        for product in self:
            category_ids = []
            category = product.categ_id
            while category:
                category_ids.append(category.id)
                category = category.parent_id
            domain = ['|',
                '&',
                ('qc_check_for', '=', 'product'),
                ('product_ids', 'in', product.product_variant_id.id),
                '&',
                ('qc_check_for', '=', 'category'),
                ('product_category_ids', 'in', category_ids),
            ]
            quality_control_points = self.env['quality.control.point'].search(domain)
            product.qcp_count = len(quality_control_points)
            product.quality_control_point_ids = [fields.Command.set(quality_control_points.ids)]

    def action_view_quality_points(self):
        return {
            'name': 'Quality Control Points',
            'view_mode': 'tree,form',
            'res_model': 'quality.control.point',
            'domain': [('id', 'in', self.quality_control_point_ids.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
