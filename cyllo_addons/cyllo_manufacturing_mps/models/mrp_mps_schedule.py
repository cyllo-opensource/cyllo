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
import json
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpScheduleMps(models.Model):
    _name = 'mrp.mps.schedule'
    _description = 'Master Production Schedule'
    _check_company_auto = True

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    is_mps = fields.Boolean(
        string='Master Production Scheduler',
        default=False,
        help='Enable the master production schedule features for this database.',
    )

    mps_default_timerange = fields.Selection(
        [
            ('year', 'Yearly'),
            ('month', 'Monthly'),
            ('week', 'Weekly'),
            ('day', 'Daily'),
        ],
        string='Default Time Range',
        default='month',
        help='Choose the default time bucket used to display and automate MPS quantities.',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Product covered by this MPS schedule line.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
        help='Company that owns this MPS schedule line.',
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        domain="[('product_id', '=', product_id)]",
        help='Bill of materials used when the product is replenished through manufacturing.',
    )
    route_id = fields.Many2one(
        'stock.route',
        string='Route',
        store=True,
        required=True,
        help='Supply route used to replenish the product, such as Buy or Manufacture.',
    )
    available_route_ids = fields.Many2many('stock.route', compute='_compute_available_route_ids')
    available_bom_ids = fields.Many2many('mrp.bom', compute='_compute_available_bom_ids')
    is_manufacture_route = fields.Boolean(compute='_compute_is_manufacture_route')

    forcast_target_quantity = fields.Float(
        string='Safety Target Quantity',
        help='Target stock level that should be maintained as a safety buffer.',
    )
    min_to_replenish_qty = fields.Float(
        string='Minimum Replenish Quantity',
        help='Minimum quantity that should trigger replenishment when stock falls below this level.',
    )

    replenishment_mode = fields.Selection([
        ('manual', 'Manual'),
        ('automated', 'Automated'),
        ('never', 'Never')
    ], default="manual", required=True,
        help='Manual lets users create orders themselves, automated runs through the scheduler, and never disables replenishment creation.',
    )

    qty_available = fields.Float(
        related='product_id.qty_available',
        help='Current available quantity of the selected product.',
    )

    saved_demand = fields.Text(
        default="{}",
        help='Stored demand values per period in JSON format.',
    )
    saved_replenishment = fields.Text(
        default="{}",
        help='Stored replenishment values per period in JSON format.',
    )
    saved_manual_repl = fields.Text(
        default="{}",
        help='Stored manual replenishment flags per period in JSON format.',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('product_id')
    def _compute_available_route_ids(self):
        """Find available routes for product.

        Every route configured on the product (or on its category) is
        proposed, whatever its name: Buy, Manufacture, inter warehouse
        resupply, dropship, or any custom route.
        """
        for schedule in self:
            product = schedule.product_id
            routes = product.route_ids | product.categ_id.total_route_ids
            schedule.available_route_ids = routes.filtered(
                lambda r: not r.company_id or r.company_id == schedule.company_id
            )

    @api.depends('product_id')
    def _compute_available_bom_ids(self):
        """Find available bom for product"""
        for schedule in self:
            schedule.available_bom_ids = schedule.product_id.bom_ids

    @api.depends('route_id')
    def _compute_is_manufacture_route(self):
        """A route produces the product when one of its rules manufactures it,
        instead of relying on the (translatable, renamable) route name."""
        for schedule in self:
            schedule.is_manufacture_route = any(
                rule.action == 'manufacture' for rule in schedule.route_id.rule_ids
            )

    # -------------------------------------------------------------------------
    # CORE METHODS
    # -------------------------------------------------------------------------
    @api.model
    def get_product_data(self):
        """Fetch product data from backend for rendering MPS"""
        schedules = self.search([])
        schedule_map = {rec.product_id.id: rec.id for rec in schedules}

        result = []

        for schedule in schedules:
            product = schedule.product_id
            bom_components = self._get_bom_components(schedule, schedule_map)
            starting_stock = (product.qty_available or 0.0) + (product.incoming_qty or 0.0)

            result.append({
                "id": schedule.id,
                "name": product.display_name,
                "initialStock": starting_stock,
                "min_qty": schedule.min_to_replenish_qty,
                "target_qty": schedule.forcast_target_quantity,
                "replenishment_mode": schedule.replenishment_mode,
                "forecasted_qty": product.virtual_available or 0,
                "outgoing_qty": product.outgoing_qty or 0,
                "bom_components": bom_components,
                "saved_demand": self._safe_json_load(schedule.saved_demand),
                "saved_replenishment": self._safe_json_load(schedule.saved_replenishment),
                "saved_manual_repl": self._safe_json_load(schedule.saved_manual_repl),
            })

        return result

    def _get_bom_components(self, schedule, schedule_map):
        """Get bom component if the selected route is manufacture"""
        if not schedule.is_manufacture_route or not schedule.bom_id:
            return []

        return [
            {
                "schedule_id": schedule_map.get(line.product_id.id),
                "qty": line.product_qty
            }
            for line in schedule.bom_id.bom_line_ids
            if schedule_map.get(line.product_id.id)
        ]

    def _safe_json_load(self, value):
        try:
            return json.loads(value or "{}")
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # UPDATE METHODS
    # -------------------------------------------------------------------------
    @api.model
    def update_period_data(self, record_id, demand, replenishment, manual_repl):
        """Save values from the frontend including user changed values to record using JSON"""
        schedule = self.browse(int(record_id))
        if schedule.exists():
            schedule.write({
                'saved_demand': json.dumps(demand),
                'saved_replenishment': json.dumps(replenishment),
                'saved_manual_repl': json.dumps(manual_repl),
            })
        return True

    # -------------------------------------------------------------------------
    # ORDER CREATION
    # -------------------------------------------------------------------------
    @api.model
    def create_purchase_manufacture_orders(self, quantities_by_schedule_id):
        """Replenish the given schedules through their configured route.

        The quantities are pushed to the standard procurement engine, exactly
        like the Cyllo 17 MPS "Replenish" button does, instead of building the
        PO/MO by hand. The stock rules of the selected route then decide what
        document has to be created, so any route works here: Buy, Manufacture,
        inter warehouse resupply, dropship or any custom route.
        """
        valid_schedule_quantities = {
            int(schedule_id): quantity
            for schedule_id, quantity in quantities_by_schedule_id.items()
            if quantity > 0
        }

        if not valid_schedule_quantities:
            return False

        procurement_group = self.env['procurement.group']
        procurements = []

        for schedule_record in self.browse(valid_schedule_quantities.keys()):
            required_quantity = valid_schedule_quantities[schedule_record.id]
            product_record = schedule_record.product_id
            route_record = schedule_record.route_id

            if not product_record or not route_record:
                raise UserError(_(
                    "Missing route/product for '%s'.",
                    product_record.display_name or schedule_record.display_name,
                ))

            if schedule_record.is_manufacture_route and not schedule_record.bom_id \
                    and not product_record.variant_bom_ids and not product_record.bom_ids:
                raise UserError(_(
                    "Missing BOM for '%s'.", product_record.display_name))

            warehouse = schedule_record._get_warehouse()
            if not warehouse:
                raise UserError(_(
                    "No warehouse found for company '%s'.",
                    schedule_record.company_id.display_name,
                ))

            procurements.append(procurement_group.Procurement(
                product_record,
                required_quantity,
                product_record.uom_id,
                warehouse.lot_stock_id,
                product_record.display_name,
                'MPS',
                schedule_record.company_id,
                schedule_record._get_procurement_values(warehouse),
            ))

        if procurements:
            procurement_group.with_context(skip_lead_time=True).run(procurements)

        return True

    def _get_warehouse(self):
        """Warehouse the replenishment is done for."""
        self.ensure_one()
        return self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1
        )

    def _get_procurement_values(self, warehouse):
        """Values passed to the procurement run.

        ``route_ids`` forces the route selected on the MPS line, so the rule
        of that route wins over the other routes of the product.
        """
        self.ensure_one()
        values = {
            'company_id': self.company_id,
            'warehouse_id': warehouse,
            'route_ids': self.route_id,
            'date_planned': fields.Datetime.now(),
        }
        if self.is_manufacture_route and self.bom_id:
            values['bom_id'] = self.bom_id
        return values

    # -------------------------------------------------------------------------
    # CONFIG & CRON
    # -------------------------------------------------------------------------
    @api.model
    def get_mps_config(self):
        period = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_manufacturing_mps.default_timerange', 'month'
        )
        return {'period': period}

    @api.model
    def _cron_automate_mps_orders(self):
        period = self.get_mps_config()['period']
        today = date.today()

        label_map = {
            'month': today.strftime('%b %Y'),
            'week': f"W{today.isocalendar()[1]} {today.year}",
            'day': f"{today.month}/{today.day}/{today.year}",
            'year': str(today.year),
        }

        current_label = label_map.get(period, "")
        schedules = self.search([('replenishment_mode', '=', 'automated')])
        products_to_order = {
            str(rec.id): float(self._safe_json_load(rec.saved_replenishment).get(current_label, 0))
            for rec in schedules
            if float(self._safe_json_load(rec.saved_replenishment).get(current_label, 0)) > 0
        }

        if products_to_order:
            self.create_purchase_manufacture_orders(products_to_order)
