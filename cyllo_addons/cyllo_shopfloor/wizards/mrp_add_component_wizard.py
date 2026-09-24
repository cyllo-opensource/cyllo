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
from odoo import models, fields, api


class MrpAddComponentWizard(models.TransientModel):
    _name = 'mrp.add.component.wizard'
    _description = 'Quick Add Component to MO'

    production_id = fields.Many2one(
        comodel_name='mrp.production',
        required=True
    )
    allow_any_product = fields.Boolean(
        string='Add New Product',
        default=False,
        help="If checked, all products will be available to add."
    )
    mo_product_ids = fields.Many2many(
        comodel_name='product.product',
        compute='_compute_mo_product_ids'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True
    )
    needed_quantity = fields.Float(
        string='Needed Quantity',
        compute='_compute_needed_quantity'
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        related='product_id.uom_id'
    )

    @api.depends('production_id')
    def _compute_mo_product_ids(self):
        """Fetch the products already existing in the MO's component list."""
        for wizard in self:
            if wizard.production_id:
                wizard.mo_product_ids = wizard.production_id.move_raw_ids.mapped('product_id')
            else:
                wizard.mo_product_ids = False

    @api.depends('product_id', 'production_id')
    def _compute_needed_quantity(self):
        """Calculate the original required quantity from the MO for the selected product."""
        for wizard in self:
            if wizard.product_id and wizard.production_id:
                component_moves = wizard.production_id.move_raw_ids.filtered(
                    lambda move: move.product_id == wizard.product_id
                )
                total_uom_qty = sum(component_moves.mapped('product_uom_qty'))
                total_qty = sum(component_moves.mapped('quantity'))
                wizard.needed_quantity = total_uom_qty - total_qty
            else:
                wizard.needed_quantity = 0.0

    @api.onchange('allow_any_product')
    def _onchange_allow_any_product(self):
        """Clear the product_id if 'Allow Any' is toggled OFF and the current product is invalid."""
        if not self.allow_any_product and self.product_id and self.production_id:
            valid_mo_products = self.production_id.move_raw_ids.mapped('product_id')
            if self.product_id not in valid_mo_products:
                self.product_id = False

    def action_add_component(self):
        """Creates or updates the component line on the Manufacturing Order."""
        self.ensure_one()
        existing_move = self.production_id.move_raw_ids.filtered(
            lambda m: m.product_id == self.product_id and m.state not in ('done', 'cancel')
        )

        if existing_move:
            existing_move.quantity += self.quantity
        else:
            self.env['stock.move'].create({
                'name': self.production_id.name,
                'raw_material_production_id': self.production_id.id,
                'product_id': self.product_id.id,
                'product_uom_qty': self.quantity,
                'quantity': self.quantity,
                'product_uom': self.product_id.uom_id.id,
                'location_id': self.production_id.location_src_id.id,
                'location_dest_id': self.production_id.production_location_id.id,
                'company_id': self.production_id.company_id.id,
            })

        return {'type': 'ir.actions.act_window_close'}

    def action_remove_component(self):
        """Removes the specified component from the Manufacturing Order."""
        self.ensure_one()
        existing_move = self.production_id.move_raw_ids.filtered(
            lambda m: m.product_id == self.product_id and m.state not in ('done', 'cancel')
        )

        if existing_move:
            existing_move.unlink()

        return {'type': 'ir.actions.act_window_close'}
