# -*- coding: utf-8 -*-
#############################################################################
#
#   Cyllo Pvt. Ltd.
#
#   Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#   Author: Cyllo(<https://www.cyllo.com>)
#
#   You can modify it under the terms of the GNU LESSER
#   GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#   You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#   (LGPL v3) along with this program.
#   If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, api, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    employee_ids = fields.Many2many("hr.employee", string="Operators", readonly=True,
                        help='Employees who worked on this Manufacturing Order through Shop Floor.')

    is_automated = fields.Boolean(
        string="Automated Operations",
        compute='_compute_is_automated',
        store=True,
        readonly=False,
        help="If enabled, work orders will automatically finish when their allocated time ends."
    )

    @api.depends('bom_id')
    def _compute_is_automated(self):
        """ Pull the default automated state from the BOM, but allow manual overrides per MO. """
        for mo in self:
            if mo.bom_id:
                mo.is_automated = mo.bom_id.is_automated
            else:
                mo.is_automated = mo.is_automated or False

    def action_shopfloor_close_mo(self):
        """
        Automatically completes pending production data (tracking, quantities,
        and consumption) and closes the MO from the shopfloor.
        """
        self.ensure_one()
        if self.product_id.tracking in ['lot', 'serial'] and not self.lot_producing_id:
            self.action_generate_serial()

        if self.qty_producing == 0:
            self.qty_producing = self.product_qty

        pending_moves = self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))

        for raw_move in pending_moves:
            if raw_move.product_id.tracking == 'none':
                quantity_field = 'quantity' if hasattr(raw_move, 'quantity') else 'quantity_done'
                consumed_qty = getattr(raw_move, quantity_field)

                if consumed_qty < raw_move.product_uom_qty:
                    setattr(raw_move, quantity_field, raw_move.product_uom_qty)

        if 'picked' in self.move_raw_ids._fields:
            self.move_raw_ids.write({'picked': True})

        return self.button_mark_done()

    @api.model
    def get_shopfloor_missing_components(self, production_ids):
        """Calculate missing product and its required quantity for shop floor"""
        productions = self.browse(production_ids)
        res = {}

        for mo in productions:
            missing = []
            pending_moves = mo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))

            for move in pending_moves:
                qty_done = getattr(move, 'quantity', getattr(move, 'quantity_done', 0))
                needed = move.product_uom_qty - qty_done

                if needed > 0:
                    name = move.product_id.display_name
                    if '[' in name and ']' in name:
                        name = name.split(']', 1)[-1].strip()

                    missing.append({
                        'product_name': name,
                        'needed_qty': round(needed, 2),
                        'uom': move.product_uom.name
                    })
            res[mo.id] = missing
        return res

    def action_open_cyllo_shopfloor(self):
        """ Opens the custom Cyllo Shopfloor client action from the MO smart button. """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'shopfloor_screen',
            'name': 'Shopfloor',
            'context': {'default_production_id': self.id},
        }
