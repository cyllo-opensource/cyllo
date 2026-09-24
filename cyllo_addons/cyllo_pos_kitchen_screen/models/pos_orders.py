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
from odoo.exceptions import AccessError


class PosOrder(models.Model):
    """Inheriting the pos order model """
    _inherit = "pos.order"

    order_status = fields.Selection(string="Order Status",
                                    selection=[("draft", "Draft"),
                                               ("waiting", "Cooking"),
                                               ("ready", "Ready"),
                                               ("cancel", "Cancel")],
                                    default="draft",
                                    help='To know the status of order')
    kitchen_stage_id = fields.Many2one(
        "kitchen.screen.stage",
        string="Kitchen Stage",
        index=True,
        ondelete="set null",
        help="Current stage of this order on the kitchen screen (dynamic stages).",
    )
    order_ref = fields.Char(string="Order Reference",
                            help='Reference of the order')
    is_cooking = fields.Boolean(string="Is Cooking",
                                help='To identify the order is  kitchen orders')
    hour = fields.Char(string="Order Time", compute="_compute_kitchen_order_time",
                       help='Hour component of the order time, derived from date_order.')
    minutes = fields.Char(string='Order Time (Minutes)', compute="_compute_kitchen_order_time",
                          help='Minute component of the order time, derived from date_order.')
    floor = fields.Char(string='Floor', compute="_compute_kitchen_order_floor",
                        help='Floor of the table this order was placed on.')

    @api.depends('date_order')
    def _compute_kitchen_order_time(self):
        """Derive the displayed order time from date_order (in the user's
        timezone) instead of relying on a value the client may or may not
        have sent - this kept showing 'false' whenever an order reached the
        Kitchen Screen through a flow other than the explicit "Send to
        Kitchen" button (e.g. via payment validation), since those flows
        never populated these fields."""
        for order in self:
            local_dt = (
                fields.Datetime.context_timestamp(order, order.date_order)
                if order.date_order else False
            )
            order.hour = "%02d" % local_dt.hour if local_dt else ""
            order.minutes = "%02d" % local_dt.minute if local_dt else ""

    @api.depends('table_id', 'table_id.floor_id', 'table_id.floor_id.name')
    def _compute_kitchen_order_floor(self):
        """Derive the floor from the order's table instead of relying on a
        client-supplied value (same reasoning as _compute_kitchen_order_time)."""
        for order in self:
            order.floor = order.table_id.floor_id.name or ""

    def _check_kitchen_cook_access(self):
        """Raise AccessError if the current user is not a Kitchen Cook."""
        if not self.env.user.has_group(
                'cyllo_pos_kitchen_screen.group_cyllo_pos_kitchen_screen'):
            raise AccessError(
                _("You do not have permission to change kitchen order "
                  "states. Only Kitchen Cook users can perform this action.")
            )

    def write(self, vals):
        """Super the write function for adding order status in vals"""
        message = {
            'res_model': self._name,
            'message': 'pos_order_created'
        }
        self.env["bus.bus"]._sendone('pos_order_created',
                                     "notification",
                                     message)
        for order in self:
            # Keep legacy behavior unless explicitly overridden by the kitchen UI.
            if not self.env.context.get("kitchen_force_status"):
                if order.order_status == "waiting" and vals.get("order_status") != "ready":
                    vals["order_status"] = order.order_status
            if vals.get("state") and vals[
                "state"] == "paid" and order.name == "/":
                vals["name"] = self._compute_order_name()
        return super(PosOrder, self).write(vals)

    def _refund(self):
        return super(PosOrder, self.with_context(
            skip_pos_reference_dedup=True))._refund()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create function for the validation of the order"""
        message = {
            'res_model': self._name,
            'message': 'pos_order_created'
        }
        self.env["bus.bus"]._sendone('pos_order_created',
                                     "notification",
                                     message)
        results = self.browse()
        skip_dedup = self.env.context.get('skip_pos_reference_dedup')
        for vals in vals_list:
            pos_orders = self.search(
                [("pos_reference", "=", vals.get("pos_reference"))]
            ) if vals.get("pos_reference") and not skip_dedup else self.browse()
            if pos_orders:
                for rec in pos_orders.lines:
                    for lin in (vals.get("lines") or []):
                        if lin[2].get("product_id") == rec.product_id.id:
                            lin[2]["order_status"] = rec.order_status
                vals["order_status"] = pos_orders.order_status
                pos_orders.write(vals)
                results |= pos_orders
            else:
                if vals.get('order_id') and not vals.get('name'):
                    # set name based on the sequence specified on the config
                    config = self.env['pos.order'].browse(
                        vals['order_id']).session_id.config_id
                    if config.sequence_line_id:
                        vals['name'] = config.sequence_line_id._next()
                if not vals.get('name'):
                    # fallback on any pos.order sequence
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'pos.order.line')
                results |= super(PosOrder, self).create([vals])
        return results

    def get_details(self, shop_id, order=None):
        """For getting the kitchen orders for the cook"""
        dic = order
        if order:
            orders = self.search(
                [("pos_reference", "=", order[0]['pos_reference'])])
            if not orders:
                self.create(dic)
            else:
                orders.lines = False
                orders.lines = dic[0]['lines']
        kitchen_screen = self.env["kitchen.screen"].sudo().search(
            [("pos_config_id", "=", shop_id)])
        if kitchen_screen.pos_categ_ids:
            pos_orders = self.env["pos.order.line"].search(
                [("is_cooking", "=", True),
                 ("product_id.pos_categ_ids", "in",
                  kitchen_screen.pos_categ_ids.ids)])
            pos = self.env["pos.order"].search(
                [("lines", "in", pos_orders.ids)],
                order="date_order")
            pos_lines = pos.lines.search(
                [("product_id.pos_categ_ids", "in",
                  kitchen_screen.pos_categ_ids.ids)])
        else:
            pos_orders = self.env["pos.order.line"].search(
                [("is_cooking", "=", True),
                 ("order_id.config_id", "=", shop_id)])
            pos = self.env["pos.order"].search(
                [("id", "in", pos_orders.mapped('order_id').ids)],
                order="date_order")
            pos_lines = pos.lines
            
        # Ensure 'All' stage exists for existing kitchen screens
        all_stage = kitchen_screen.stage_ids.filtered(lambda s: s.name == 'All' and not s.is_done and not s.is_cancelled)
        
        if kitchen_screen and not all_stage:
            self.env['kitchen.screen.stage'].sudo().create({
                'name': 'All',
                'is_done': False,
                'is_cancelled': False,
                'sequence': 1,
                'kitchen_screen_id': kitchen_screen.id
            })
            # Refresh stage recordset
            kitchen_screen.invalidate_recordset(['stage_ids'])

        # Backfill dynamic kitchen stage for existing kitchen orders (legacy installs).
        default_stage = (
            kitchen_screen.stage_ids.filtered(lambda s: s.name != "All" and not s.is_done and not s.is_cancelled)
            .sorted(lambda s: (s.sequence, s.id))[:1]
        )
        if default_stage:
            legacy_orders = pos.filtered(lambda o: o.is_cooking and not o.kitchen_stage_id)
            if legacy_orders:
                legacy_orders.with_context(kitchen_force_status=True).write(
                    {"kitchen_stage_id": default_stage.id, "order_status": "waiting"}
                )

        values = {
            "orders": pos.read(),
            "order_lines": pos_lines.read(),
            "stages": kitchen_screen.stage_ids.read(),
            "is_kitchen_cook": self.env.user.has_group(
                'cyllo_pos_kitchen_screen.group_cyllo_pos_kitchen_screen'
            ),
            "shop_name": kitchen_screen.pos_config_id.name or '',
        }
        return values

    def action_pos_order_paid(self):
        """Supering the action_pos_order_paid function for setting its kitchen
        order and setting the order reference"""
        res = super().action_pos_order_paid()
        for order in self:
            kitchen_screen = self.env["kitchen.screen"].search(
                [("pos_config_id", "=", order.config_id.id)], limit=1
            )
            if not kitchen_screen:
                continue

            # Already sent to the kitchen (and possibly already progressed,
            # e.g. moved to "Completed"): do not touch its kitchen state.
            if order.is_cooking or order.kitchen_stage_id:
                continue

            order.lines.write({"is_cooking": True})
            order.is_cooking = True
            order.order_ref = order.name
            default_stage = (
                kitchen_screen.stage_ids.filtered(
                    lambda s: s.name != "All" and not s.is_done and not s.is_cancelled
                )
                .sorted(lambda s: (s.sequence, s.id))[:1]
            )
            if default_stage:
                order.with_context(kitchen_force_status=True).write(
                    {
                        "kitchen_stage_id": default_stage.id,
                        # Keep legacy status usable for UI coloring/line interaction.
                        "order_status": "waiting",
                    }
                )
        return res

    @api.onchange("order_status")
    def _onchange_order_status(self):
        """To set is_cooking false"""
        if self.order_status == "ready":
            self.is_cooking = False

    def order_progress_draft(self):
        """Calling function from js to change the order status"""
        self._check_kitchen_cook_access()
        self.order_status = "waiting"
        for line in self.lines:
            if line.order_status != "ready":
                line.order_status = "waiting"

    def order_progress_cancel(self):
        """Calling function from js to change the order status"""
        self._check_kitchen_cook_access()
        self.order_status = "cancel"
        for line in self.lines:
            if line.order_status != "ready":
                line.order_status = "cancel"

    def order_progress_change(self):
        """Calling function from js to change the order status"""
        self._check_kitchen_cook_access()
        kitchen_screen = self.env["kitchen.screen"].search(
            [("pos_config_id", "=", self.config_id.id)])
        stage = []
        if kitchen_screen.pos_categ_ids:
            for line in self.lines:
                for categ in line.product_id.pos_categ_ids:
                    if categ.id in kitchen_screen.pos_categ_ids.ids:
                        stage.append(line.order_status)
        else:
            stage = self.lines.mapped('order_status')

        if "waiting" in stage or "draft" in stage:
            self.order_status = "ready"
        else:
            self.order_status = "ready"

    def set_kitchen_order_status(self, status):
        """Force-set order + lines status from the kitchen UI (supports drag back)."""
        self._check_kitchen_cook_access()
        allowed = {"draft", "waiting", "ready", "cancel"}
        if status not in allowed:
            return False
        for order in self.with_context(kitchen_force_status=True):
            order.order_status = status
            # Keep order lines aligned with the order stage for clear workflow tracking.
            if status == "ready":
                order.lines.with_context(kitchen_force_status=True).write({"order_status": "ready"})
            else:
                order.lines.with_context(kitchen_force_status=True).write({"order_status": status})
        return True

    def set_kitchen_stage(self, stage_id):
        """Set dynamic kitchen stage for orders from the kitchen UI."""
        self._check_kitchen_cook_access()
        stage = self.env["kitchen.screen.stage"].sudo().browse(int(stage_id)) if stage_id else False
        res = {}
        for order in self:
            # Validate stage is part of the kitchen screen for this POS config.
            if stage:
                kitchen_screen = self.env["kitchen.screen"].sudo().search(
                    [("pos_config_id", "=", order.config_id.id)], limit=1
                )
                if not kitchen_screen or stage.kitchen_screen_id.id != kitchen_screen.id:
                    continue

            # Keep legacy status meaningful:
            # active stages => waiting, done => ready, cancelled => cancel.
            if stage and stage.is_done:
                new_status = "ready"
            elif stage and stage.is_cancelled:
                new_status = "cancel"
            else:
                new_status = "waiting"

            order.with_context(kitchen_force_status=True).write(
                {
                    "kitchen_stage_id": stage.id if stage else False,
                    "order_status": new_status,
                }
            )
            # Keep order lines aligned for clarity.
            if new_status in ("ready", "cancel", "waiting"):
                order.lines.with_context(kitchen_force_status=True).write({"order_status": new_status})

            res[order.id] = {
                "order_status": order.order_status,
                "kitchen_stage_id": [order.kitchen_stage_id.id, order.kitchen_stage_id.name]
                if order.kitchen_stage_id
                else False,
            }
        return res

    def check_order(self, order_name):
        """Calling function from js to know status of the order"""
        pos_order = self.env['pos.order'].sudo().search(
            [('pos_reference', '=', str(order_name))])
        kitchen_order = self.env['kitchen.screen'].sudo().search(
            [('pos_config_id', '=', pos_order.config_id.id)])
        if kitchen_order and kitchen_order.pos_categ_ids:
            for category in pos_order.lines.mapped('product_id').mapped(
                    'pos_categ_ids').mapped('id'):
                if category not in kitchen_order.pos_categ_ids.mapped('id'):
                    return {
                        'category': self.env['pos.category'].browse(
                            category).name}
        if kitchen_order and pos_order:
            if pos_order.order_status != 'ready':
                return True
            else:
                return False
        else:
            return False

    def remove_from_kitchen(self):
        """Method to remove order from kitchen screen"""
        self._check_kitchen_cook_access()
        for order in self:
            order.is_cooking = False
            order.kitchen_stage_id = False
            for line in order.lines:
                line.is_cooking = False

    def check_order_status(self, order_name):
        """To check order status"""
        pos_order = self.env['pos.order'].sudo().search(
            [('pos_reference', '=', str(order_name))])
        kitchen_order = self.env['kitchen.screen'].sudo().search(
            [('pos_config_id', '=', pos_order.config_id.id)])
        if kitchen_order and kitchen_order.pos_categ_ids:
            for category in pos_order.lines.mapped('product_id').mapped(
                    'pos_categ_ids').mapped('id'):
                if category not in kitchen_order.pos_categ_ids.mapped('id'):
                    return 'no category'
        if kitchen_order:
            if pos_order.order_status == 'ready':
                return False
            else:
                return True
        else:
            return True


class PosOrderLine(models.Model):
    """Inheriting the pos order line"""
    _inherit = "pos.order.line"

    order_status = fields.Selection(
        selection=[('draft', 'Draft'), ('waiting', 'Cooking'),
                   ('ready', 'Ready'), ('cancel', 'Cancel')], default='draft',
        help='The status of orderliness')
    order_ref = fields.Char(related='order_id.order_ref',
                            string='Order Reference',
                            help='Order reference of order')
    is_cooking = fields.Boolean(string="Cooking", default=False,
                                help='To identify the order is  '
                                     'kitchen orders')
    customer_id = fields.Many2one('res.partner', string="Customer",
                                  related='order_id.partner_id',
                                  help='Id of the customer')

    def get_product_details(self, ids):
        """To get the product details"""
        lines = self.env['pos.order'].browse(ids)
        res = []
        for rec in lines:
            res.append({
                'product_id': rec.product_id.id,
                'name': rec.product_id.name,
                'qty': rec.qty
            })
        return res

    def order_progress_change(self):
        """Calling function from js to change the order_line status"""
        if not self.env.user.has_group(
                'cyllo_pos_kitchen_screen.group_cyllo_pos_kitchen_screen'):
            raise AccessError(
                _("You do not have permission to change kitchen order "
                  "states. Only Kitchen Cook users can perform this action.")
            )
        if self.order_status == 'ready':
            self.order_status = 'waiting'
        else:
            self.order_status = 'ready'
