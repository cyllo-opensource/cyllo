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
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpScrapComponentWizard(models.TransientModel):
    _name = 'mrp.scrap.component.wizard'
    _description = 'Quick Scrap Component Wizard'

    production_id = fields.Many2one(
        comodel_name='mrp.production',
        required=True
    )
    component_ids = fields.Many2many(
        comodel_name='product.product',
        compute='_compute_component_ids'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Component',
        required=True
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True
    )
    reason = fields.Char(
        string='Reason',
        help="Why is this being scrapped?"
    )

    @api.depends('production_id')
    def _compute_component_ids(self):
        """Fetch products that belong to the raw materials list of the MO."""
        for wizard in self:
            if wizard.production_id:
                wizard.component_ids = wizard.production_id.move_raw_ids.mapped('product_id')
            else:
                wizard.component_ids = False

    @api.constrains('quantity', 'product_id')
    def _check_quantity(self):
        """Ensure scrap quantity is valid and does not exceed the planned amount."""
        for wizard in self:
            if wizard.product_id and wizard.production_id:
                moves = wizard.production_id.move_raw_ids.filtered(
                    lambda m: m.product_id == wizard.product_id
                )
                max_quantity = sum(moves.mapped('product_uom_qty'))

                if wizard.quantity > max_quantity:
                    raise ValidationError(
                        _("You cannot scrap more than the planned quantity (%s) for this component.") % max_quantity
                    )
                if wizard.quantity <= 0:
                    raise ValidationError(_("Scrap quantity must be greater than 0."))

    def action_scrap_component(self):
        """Creates and executes a stock scrap record for the component."""
        self.ensure_one()

        scrap_location = self.env['stock.location'].search([
            ('scrap_location', '=', True),
            ('company_id', 'in', [self.production_id.company_id.id, False])
        ], limit=1)

        scrap_origin = self.production_id.name
        if self.reason:
            scrap_origin = f"{self.production_id.name} - Reason: {self.reason}"

        scrap_record = self.env['stock.scrap'].create({
            'production_id': self.production_id.id,
            'product_id': self.product_id.id,
            'scrap_qty': self.quantity,
            'product_uom_id': self.product_id.uom_id.id,
            'location_id': self.production_id.location_src_id.id,
            'scrap_location_id': scrap_location.id,
            'origin': scrap_origin,
            'company_id': self.production_id.company_id.id,
        })

        scrap_record.do_scrap()
        self.production_id.action_assign()

        return {'type': 'ir.actions.act_window_close'}

    def action_remove_scrap(self):
        """Removes an unconfirmed scrap record associated with this component."""
        self.ensure_one()

        existing_scrap = self.env['stock.scrap'].search([
            ('production_id', '=', self.production_id.id),
            ('product_id', '=', self.product_id.id),
            ('state', 'not in', ('done', 'cancel'))
        ], limit=1)

        if existing_scrap:
            existing_scrap.unlink()

        return {'type': 'ir.actions.act_window_close'}
