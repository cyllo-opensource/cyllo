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
from odoo import models, fields


class EditRepairLineWizard(models.TransientModel):
    """Wizard to add, remove, or recycle products in a repair order line."""
    _name = 'edit.repair.line.wizard'
    _description = 'Edit Repair Line Wizard'

    repair_id = fields.Many2one(
        comodel_name='repair.order',
        required=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]"
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        related='product_id.uom_id'
    )
    repair_line_type = fields.Selection(
        selection=[
            ('add', 'Add'),
            ('remove', 'Remove'),
            ('recycle', 'Recycle')
        ],
        required=True,
        default='add'
    )

    def action_edit_repair_line(self):
        """Creates or updates a stock move for the repair order based on the selected line type."""
        self.ensure_one()
        existing_move = self.repair_id.move_ids.filtered(
            lambda m: m.product_id == self.product_id and \
                      m.repair_line_type == self.repair_line_type and \
                      m.state not in ('done', 'cancel')
        )

        if existing_move:
            existing_move.product_uom_qty += self.quantity
            existing_move.quantity += self.quantity
        else:
            self.env['stock.move'].create({
                'name': self.repair_id.name,
                'repair_id': self.repair_id.id,
                'product_id': self.product_id.id,
                'product_uom_qty': self.quantity,
                'product_uom': self.product_id.uom_id.id,
                'location_id': self.repair_id.location_id.id,
                'location_dest_id': self.repair_id.location_dest_id.id,
                'company_id': self.repair_id.company_id.id,
                'repair_line_type': self.repair_line_type,
            })

        return {'type': 'ir.actions.act_window_close'}
