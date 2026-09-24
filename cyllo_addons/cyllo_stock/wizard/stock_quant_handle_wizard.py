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
from odoo.exceptions import ValidationError
from odoo.models import BaseModel


class StockQuantHandleWizard(models.TransientModel):
    _name = 'stock.quant.handle.wizard'
    _description = 'Manage Expiring Quantities'

    quant_id = fields.Many2one('stock.quant', string="Quant", required=True)
    product_id = fields.Many2one('product.product', string="Product", related='quant_id.product_id',
                                 readonly=True)
    qty = fields.Float(related='quant_id.quantity', readonly=True)
    location_id = fields.Many2one('stock.location', related='quant_id.location_id', readonly=True)
    lot_id = fields.Many2one('stock.lot', related='quant_id.lot_id', readonly=True)
    expiry_risk_level = fields.Selection(related='quant_id.expiry_risk_level', readonly=True)
    expiration_date = fields.Datetime(
        compute='_compute_expiration_date',
        readonly=True,
    )
    action_type = fields.Selection([
        ('discount', 'Add Discount'),
        ('scrap', 'Move to Scrap Location'),
        ('deliver', 'Deliver to Anyone'),
        ('return', 'Return to Purchase Order')
    ], string="Action", default='discount', required=True)

    discount = fields.Float(string="Discount (%)")
    scrap_location_id = fields.Many2one('stock.location', string="Scrap Location",
                                        domain="[('scrap_location', '=', True)]")

    @api.depends('quant_id', 'quant_id.lot_id')
    def _compute_expiration_date(self):
        for record in self:
            record.expiration_date = False
            lot = record.quant_id.lot_id
            if lot and 'expiration_date' in lot._fields:
                record.expiration_date = lot.expiration_date

    def action_proceed(self):
        self.ensure_one()
        res = {'type': 'ir.actions.act_window_close'}
        company = self.quant_id.company_id or self.env.company
        company_id = company.id

        if self.action_type == 'discount':
            if not self.quant_id.lot_id:
                raise ValidationError(
                    _("A lot/serial number is required to apply a lot-specific discount."))
            # Add discount on this lot only
            self.quant_id.lot_id.sudo().default_discount = self.discount

        elif self.action_type == 'scrap':
            if not self.scrap_location_id:
                raise ValidationError(_("Please choose a scrap location."))
            # Create scrap order and validate it
            scrap = self.env['stock.scrap'].sudo().create({
                'product_id': self.product_id.id,
                'scrap_qty': self.quant_id.quantity,
                'product_uom_id': self.product_id.uom_id.id,
                'location_id': self.quant_id.location_id.id,
                'scrap_location_id': self.scrap_location_id.id,
                'lot_id': self.quant_id.lot_id.id,
                'package_id': self.quant_id.package_id.id,
                'owner_id': self.quant_id.owner_id.id,
                'company_id': company_id,
            })
            scrap.with_context(inventory_mode=False).action_validate()

        elif self.action_type == 'deliver':
            # Redirect to delivery page to select customer
            picking_type = self.env['stock.picking.type'].sudo().search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', company_id)
            ], limit=1)

            if not picking_type:
                raise ValidationError(
                    _("No outgoing picking type found for the company %s.") % company.name)

            # Find customer location matching company or company-agnostic
            customer_location = self.env['stock.location'].sudo().search([
                ('usage', '=', 'customer'),
                '|', ('company_id', '=', company_id), ('company_id', '=', False)
            ], limit=1)

            dest_location_id = customer_location.id if customer_location else picking_type.default_location_dest_id.id
            if not dest_location_id:
                raise ValidationError(
                    _("No customer destination location found for the company %s.") % company.name)

            picking = self.env['stock.picking'].sudo().with_company(company_id).create({
                'picking_type_id': picking_type.id,
                'location_id': self.quant_id.location_id.id,
                'location_dest_id': dest_location_id,
                'company_id': company_id,
            })
            move = self.env['stock.move'].sudo().with_company(company_id).create({
                'name': self.product_id.name,
                'product_id': self.product_id.id,
                'product_uom': self.product_id.uom_id.id,
                'product_uom_qty': self.quant_id.quantity,
                'picking_id': picking.id,
                'location_id': self.quant_id.location_id.id,
                'location_dest_id': dest_location_id,
                'picking_type_id': picking_type.id,
                'partner_id': picking.partner_id.id,
                'company_id': company_id,
            })
            self.env['stock.move.line'].sudo().with_company(company_id).create({
                'move_id': move.id,
                'picking_id': picking.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'quantity': self.quant_id.quantity,
                'location_id': self.quant_id.location_id.id,
                'location_dest_id': dest_location_id,
                'lot_id': self.quant_id.lot_id.id,
                'company_id': company_id,
            })

            clean_context = dict(self.env.context)
            clean_context['inventory_mode'] = False

            res = {
                'name': _('Delivery Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'view_mode': 'form',
                'target': 'current',
                'context': clean_context,
            }

        elif self.action_type == 'return':
            # Find purchase order & receipt
            incoming_picking = False
            purchase_order = False

            # Try by lot
            if self.quant_id.lot_id:
                move_line = self.env['stock.move.line'].sudo().search([
                    ('lot_id', '=', self.quant_id.lot_id.id),
                    ('state', '=', 'done'),
                    ('picking_id.purchase_id', '!=', False)
                ], limit=1, order='id desc')
                if move_line:
                    incoming_picking = move_line.picking_id
                    purchase_order = incoming_picking.purchase_id

            # Try by product incoming move
            if not incoming_picking:
                move = self.env['stock.move'].sudo().search([
                    ('product_id', '=', self.product_id.id),
                    ('state', '=', 'done'),
                    ('picking_id.purchase_id', '!=', False),
                    ('location_dest_id', '=', self.quant_id.location_id.id)
                ], limit=1, order='id desc')
                if move:
                    incoming_picking = move.picking_id
                    purchase_order = incoming_picking.purchase_id

            # Try by confirmed PO line
            if not incoming_picking:
                po_line = self.env['purchase.order.line'].sudo().search([
                    ('product_id', '=', self.product_id.id),
                    ('order_id.state', 'in', ['purchase', 'done'])
                ], limit=1, order='id desc')
                if po_line:
                    purchase_order = po_line.order_id
                    incoming_pickings = purchase_order.picking_ids.filtered(
                        lambda p: p.state == 'done' and p.picking_type_id.code == 'incoming'
                    )
                    if incoming_pickings:
                        incoming_picking = incoming_pickings[0]

            if not purchase_order:
                raise ValidationError(_("This product has no corresponding purchase order."))

            if not incoming_picking:
                raise ValidationError(
                    _("This product has a corresponding purchase order (%s), but no completed receipt was found to return.") % purchase_order.name)

            # Create Return Picking
            wizard = self.env['stock.return.picking'].sudo().with_context(
                active_id=incoming_picking.id,
                active_model='stock.picking'
            ).create({
                'picking_id': incoming_picking.id,
            })

            product_found = False
            for line in wizard.product_return_moves:
                if line.product_id.id == self.product_id.id:
                    line.quantity = self.quant_id.quantity
                    product_found = True
                else:
                    line.quantity = 0.0

            if not product_found:
                raise ValidationError(
                    _("The product %s was not found in the incoming shipment of the purchase order %s.") % (
                        self.product_id.display_name, purchase_order.name))

            # Create and validate the return picking programmatically
            new_picking_id, pick_type_id = wizard.sudo()._create_returns()
            new_picking = self.env['stock.picking'].sudo().browse(new_picking_id)
            new_picking.move_ids.picked = True
            new_picking.with_context(inventory_mode=False).button_validate()

            clean_context = dict(self.env.context)
            clean_context['inventory_mode'] = False

            res = {
                'name': _('Returned Picking'),
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': new_picking.id,
                'type': 'ir.actions.act_window',
                'context': clean_context,
            }

        # Set the quant's is_handled field to True
        self.quant_id.sudo().with_context(check_company=False).is_handled = True
        return res
