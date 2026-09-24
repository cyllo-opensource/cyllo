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
from odoo import api, fields, models


class StockPickingTypeCarbon(models.Model):
    _name = 'stock.picking.type.carbon'
    _description = 'Inventory Operation Carbon Line'

    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', ondelete='cascade', required=True)
    source_id = fields.Many2one('carbon.source', string='Name', required=True)
    unit_id = fields.Many2one('carbon.unit', string='Unit', related='source_id.activity_unit', readonly=False, store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_ids = fields.Many2many('res.partner', string='Partners')
    product_ids = fields.Many2many('product.product', string='Products')

    @api.onchange('source_id')
    def _onchange_source_id(self):
        if self.source_id:
            self.unit_id = self.source_id.activity_unit
        else:
            self.unit_id = False


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    carbon_line_ids = fields.One2many('stock.picking.type.carbon', 'picking_type_id', string='Green Metrics')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            picking._update_carbon_activities()
        return res

    def _update_carbon_activities(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        
        # Check if there are emission sources configured on the picking type
        if not self.picking_type_id or not self.picking_type_id.carbon_line_ids:
            return

        # Find or open today's draft carbon calculation: a calculation that is
        # already submitted/approved/done must not receive new activities.
        calc = self.env['carbon.calc']._get_or_create_draft_calc(today, self.company_id)

        # Calculate the quantity: sum of done quantities of the moves in the picking
        total_qty = sum(move.quantity for move in self.move_ids)
        if total_qty <= 0.0:
            total_qty = 1.0  # Fallback to 1 activity/operation if quantity is 0

        for line in self.picking_type_id.carbon_line_ids:
            # Check partner match
            partner_match = True
            if line.partner_ids:
                partner_match = self.partner_id and (self.partner_id in line.partner_ids)

            # Check product match
            product_match = True
            if line.product_ids:
                picking_products = self.move_ids.mapped('product_id')
                product_match = any(p in line.product_ids for p in picking_products)

            if not (partner_match and product_match):
                continue

            source = line.source_id
            all_factors = source.air_factor_ids + source.sound_factor_ids + source.water_factor_ids
            # Only factors valid on the transfer date may be used.
            for factor in all_factors._filter_valid_on(today):
                # Looked up across calculations, so a transfer never lands twice
                # when its previous calculation has already been closed.
                existing_activity = self.env['carbon.activity'].search([
                    ('picking_id', '=', self.id),
                    ('source_id', '=', source.id),
                    ('factor_id', '=', factor.id),
                    ('date', '=', today),
                    ('company_id', '=', self.company_id.id),
                ], limit=1)
                
                vals = {
                    'name': self.name,
                    'date': today,
                    'calculation_id': calc.id,
                    'picking_id': self.id,
                    'source_id': source.id,
                    'factor_id': factor.id,
                    'quantity': total_qty,
                    'uom_id': line.unit_id.id or source.activity_unit.id,
                    'company_id': self.company_id.id,
                }
                
                if existing_activity:
                    if existing_activity._is_carbon_locked():
                        continue
                    if abs(existing_activity.quantity - total_qty) > 0.0001:
                        existing_activity.write({
                            'name': self.name,
                            'quantity': total_qty
                        })
                else:
                    self.env['carbon.activity'].create(vals)
