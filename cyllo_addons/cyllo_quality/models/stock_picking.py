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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_quality_check = fields.Boolean(compute='_compute_quality_checks', store=True, copy=False)
    is_quality_check_created = fields.Boolean(default=False, copy=False)
    quality_control_point_ids = fields.Many2many('quality.control.point', copy=False)
    quality_check_ids = fields.Many2many('quality.check', copy=False)
    qc_count = fields.Integer(compute='_compute_quality_checks', copy=False)
    qc_checked_count = fields.Integer(compute='_compute_quality_checks', copy=False)

    @api.depends('quality_check_ids', 'quality_check_ids.quality_check_line_ids.is_checked', 'quality_control_point_ids')
    def _compute_quality_checks(self):
        all_category = self.env.ref('product.product_category_all', raise_if_not_found=False)
        all_cat_id = all_category.id if all_category else False
        for picking in self:
            if picking.quality_check_ids:
                all_lines = picking.quality_check_ids.quality_check_line_ids
                picking.qc_count = len(all_lines)
                picking.qc_checked_count = len(all_lines.filtered('is_checked'))
            else:
                count = 0
                for qcp in picking.quality_control_point_ids:
                    num_actions = len(qcp.quality_inspection_ids)
                    if qcp.control_type == 'operation':
                        count += num_actions
                    else:
                        matching_moves = picking.move_ids_without_package.filtered(
                            lambda m: qcp.is_matching_product(m.product_id, all_cat_id)
                        )
                        count += len(matching_moves.mapped('product_id')) * num_actions
                picking.qc_count = count
                picking.qc_checked_count = 0

            if picking.quality_control_point_ids:
                picking.is_quality_check = (picking.qc_count == 0 or picking.qc_count != picking.qc_checked_count)
            else:
                picking.is_quality_check = False

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        all_category = self.env.ref('product.product_category_all', raise_if_not_found=False)
        all_cat_id = all_category.id if all_category else False
        for picking in self:
            quality_points = self.env['quality.control.point'].search(
                [('operation_type_ids', 'in', picking.picking_type_id.id)])
            quality_control_points = []
            move_products = picking.move_ids_without_package.mapped('product_id')
            for point in quality_points:
                if not point.product_category_ids and not point.product_ids:
                    quality_control_points.append(point.id)
                elif any(point.is_matching_product(prod, all_cat_id) for prod in move_products):
                    quality_control_points.append(point.id)

            if quality_control_points:
                picking.quality_control_point_ids = [fields.Command.set(quality_control_points)]
                picking.action_quality_check()
        return res

    def create_quality_checks(self, move, qcp):
        if move:
            move_qty = move.quantity or move.product_uom_qty
            if qcp.control_type == 'quantity':
                qty = (move_qty * qcp.control_quantity) / 100
            else:
                qty = move_qty
        else:
            qty = 0
        quality_check = self.env['quality.check'].create({
            'name': self.name,
            'quality_control_id': qcp.id,
            'product_id': move.product_id.id if move else False,
            'picking_id': self.id,
            'control_type': qcp.control_type,
            'quantity': qty,
            'uom_id': move.product_uom.id if move else False,
        })
        return quality_check

    def action_quality_check(self):
        if not self.is_quality_check_created:
            all_category = self.env.ref('product.product_category_all', raise_if_not_found=False)
            all_cat_id = all_category.id if all_category else False
            qc_ids = []
            for qcp in self.quality_control_point_ids:
                if qcp.control_type == 'operation':
                    quality_check = self.create_quality_checks(False, qcp)
                    qc_ids.append(quality_check.id)
                elif qcp.control_type in ('product', 'quantity'):
                    for move in self.move_ids_without_package:
                        if qcp.is_matching_product(move.product_id, all_cat_id):
                            move_qty = move.quantity or move.product_uom_qty
                            if move_qty <= 0:
                                raise UserError(
                                    _("You cannot perform a quality check if the quantity is zero. Please set the product quantity first."))
                            quality_check = self.create_quality_checks(move, qcp)
                            qc_ids.append(quality_check.id)
            self.quality_check_ids = [fields.Command.set(qc_ids)]
            self.is_quality_check_created = True

    def action_view_quality_check(self):
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form',
            'res_model': 'quality.check',
            'domain': [('id', 'in', self.quality_check_ids.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def button_validate(self):
        if self.quality_control_point_ids and (not self.quality_check_ids or self.qc_checked_count != self.qc_count):
            raise UserError(_("You need to complete the quality check."))
        return super().button_validate()

