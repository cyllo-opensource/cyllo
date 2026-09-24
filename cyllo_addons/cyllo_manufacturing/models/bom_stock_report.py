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
from odoo import fields, models, tools


class BomStockReport(models.Model):
    _name = 'bom.stock.report'
    _description = 'BOM Stock Report'
    _auto = False
    _order = 'date_start desc'

    name = fields.Char(
        string='Reference',
        readonly=True,
        help='Reference name of the source manufacturing move or order.',
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        readonly=True,
        help='Manufacturing order linked to this component demand line.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        readonly=True,
        help='Component product consumed by the manufacturing order.',
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        readonly=True,
        help='Unit of measure used for the demanded and consumed quantities.',
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Work Center/Workstation',
        readonly=True,
        help='Work center or workstation assigned to the operation.',
    )
    qty_demanded = fields.Float(
        string='To Consume / Demanded',
        readonly=True,
        help='Planned quantity required from stock for this component.',
    )
    qty_consumed = fields.Float(
        string='Consumed Quantity',
        readonly=True,
        help='Quantity already consumed from stock for this component.',
    )
    qty_on_hand = fields.Float(
        string='Quantity On Hand',
        readonly=True,
        help='Current internal stock available for the component.',
    )
    qty_forecasted = fields.Float(
        string='Forecasted Quantity',
        readonly=True,
        help='Projected stock after considering on-hand, incoming, and outgoing quantities.',
    )
    is_deficit = fields.Boolean(
        string='Is Deficit',
        readonly=True,
        help='Checked when on-hand stock is lower than the demanded quantity.',
    )
    date_start = fields.Datetime(
        string='Scheduled Start Date',
        readonly=True,
        help='Planned start date of the work order or manufacturing order.',
    )
    date_finished = fields.Datetime(
        string='Scheduled Finished Date',
        readonly=True,
        help='Planned finish date of the work order or manufacturing order.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='MO State', readonly=True,
        help='Current status of the manufacturing order.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
        help='Company that owns the manufacturing order.',
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sm.id AS id,
                    mp.name AS name,
                    sm.raw_material_production_id AS production_id,
                    sm.product_id AS product_id,
                    sm.product_uom AS product_uom_id,
                    COALESCE(wo.workcenter_id, rwc.workcenter_id) AS workcenter_id,
                    sm.product_uom_qty AS qty_demanded,
                    sm.quantity AS qty_consumed,
                    COALESCE(sq.qty_on_hand, 0.0) AS qty_on_hand,
                    COALESCE(sq.qty_on_hand, 0.0) + COALESCE(sin.qty_incoming, 0.0) - COALESCE(sout.qty_outgoing, 0.0) AS qty_forecasted,
                    (CASE WHEN COALESCE(sq.qty_on_hand, 0.0) < sm.product_uom_qty THEN True ELSE False END) AS is_deficit,
                    COALESCE(wo.date_start, mp.date_start) AS date_start,
                    COALESCE(wo.date_finished, mp.date_finished) AS date_finished,
                    mp.state AS state,
                    mp.company_id AS company_id
                FROM stock_move sm
                JOIN mrp_production mp ON sm.raw_material_production_id = mp.id
                LEFT JOIN mrp_workorder wo ON sm.workorder_id = wo.id
                LEFT JOIN mrp_routing_workcenter rwc ON sm.operation_id = rwc.id
                
                -- Dynamic Quantity on Hand
                LEFT JOIN (
                    SELECT sq.product_id, SUM(sq.quantity) AS qty_on_hand
                    FROM stock_quant sq
                    JOIN stock_location sl ON sq.location_id = sl.id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id
                ) sq ON sm.product_id = sq.product_id

                -- Incoming Moves
                LEFT JOIN (
                    SELECT sm_in.product_id, SUM(sm_in.product_qty) AS qty_incoming
                    FROM stock_move sm_in
                    JOIN stock_location sl_src ON sm_in.location_id = sl_src.id
                    JOIN stock_location sl_dest ON sm_in.location_dest_id = sl_dest.id
                    WHERE sm_in.state IN ('confirmed', 'waiting', 'assigned', 'partially_available')
                      AND sl_src.usage != 'internal'
                      AND sl_dest.usage = 'internal'
                    GROUP BY sm_in.product_id
                ) sin ON sm.product_id = sin.product_id

                -- Outgoing Moves
                LEFT JOIN (
                    SELECT sm_out.product_id, SUM(sm_out.product_qty) AS qty_outgoing
                    FROM stock_move sm_out
                    JOIN stock_location sl_src ON sm_out.location_id = sl_src.id
                    JOIN stock_location sl_dest ON sm_out.location_dest_id = sl_dest.id
                    WHERE sm_out.state IN ('confirmed', 'waiting', 'assigned', 'partially_available')
                      AND sl_src.usage = 'internal'
                      AND sl_dest.usage != 'internal'
                    GROUP BY sm_out.product_id
                ) sout ON sm.product_id = sout.product_id
                
                WHERE sm.raw_material_production_id IS NOT NULL
            )
        """ % self._table)
