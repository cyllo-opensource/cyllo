# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    display_extend_warranty = fields.Boolean(
        compute='_compute_display_extend_warranty')

    @api.depends('order_line.is_under_warranty')
    def _compute_display_extend_warranty(self):
        is_extend_warranty = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_sales.is_extend_warranty')
        for order in self:
            order.display_extend_warranty = is_extend_warranty and any(
                line.is_under_warranty for line in order.order_line)

    def action_extend_warranty(self):
        self.ensure_one()
        has_warranty = any(
            line.product_id._get_warranty_definition()[0] > 0 for line in
            self.order_line)
        if not has_warranty:
            raise UserError(
                _("This Sale Order does not contain any products with a valid warranty to extend."))
        warranty_lines = self.order_line.filtered('is_under_warranty')
        ctx = {
            'default_order_id': self.id,
        }
        if len(warranty_lines) == 1:
            ctx['default_line_ids'] = [(6, 0, warranty_lines.ids)]
        return {
            'name': 'Extend Warranty',
            'type': 'ir.actions.act_window',
            'res_model': 'warranty.extension.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'cyllo_warranty_sale.warranty_extension_wizard_view_form_sale').id,
            'target': 'new',
            'context': ctx,
        }
