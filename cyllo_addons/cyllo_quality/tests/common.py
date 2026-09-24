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
from odoo.tests.common import TransactionCase


class QualityCommon(TransactionCase):
    """Shared fixtures for all cyllo_quality tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Inspection lookup data ────────────────────────────────────────
        cls.inspection_type_pass_fail = cls.env['inspection.type'].search(
            [('name', '=', 'Pass/Fail')], limit=1
        )
        cls.inspection_type_measure = cls.env.ref(
            'cyllo_quality.inspection_type_measure'
        )
        cls.inspection_type_instructions = cls.env['inspection.type'].search(
            [('name', '=', 'Instructions')], limit=1
        )
        cls.inspection_type_picture = cls.env['inspection.type'].search(
            [('name', '=', 'Take a picture')], limit=1
        )

        cls.inspection_action = cls.env['inspection.action'].search(
            [], limit=1
        )
        if not cls.inspection_action:
            cls.inspection_action = cls.env['inspection.action'].create(
                {'name': 'Visual Check'}
            )

        # ── UoM ───────────────────────────────────────────────────────────
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # ── Product category & product ────────────────────────────────────
        cls.product_category = cls.env['product.category'].create(
            {'name': 'Test Quality Category'}
        )
        cls.product = cls.env['product.product'].create({
            'name': 'Test Quality Product',
            'categ_id': cls.product_category.id,
            'type': 'consu',
        })

        # ── Warehouse / picking type ──────────────────────────────────────
        cls.warehouse = cls.env.ref('stock.warehouse0')
        cls.picking_type_in = cls.warehouse.in_type_id
        cls.picking_type_out = cls.warehouse.out_type_id

        # ── Locations ────────────────────────────────────────────────────
        cls.location_src = cls.env.ref('stock.stock_location_suppliers')
        cls.location_dest = cls.env.ref('stock.stock_location_stock')
        cls.failure_location = cls.env['stock.location'].create({
            'name': 'Failure Location',
            'usage': 'internal',
            'location_id': cls.warehouse.lot_stock_id.location_id.id,
        })

        # ── HR employee (for quality team) ────────────────────────────────
        cls.employee = cls.env['hr.employee'].create(
            {'name': 'Quality Inspector'}
        )

        # ── Quality team ──────────────────────────────────────────────────
        cls.quality_team = cls.env['quality.team'].create({
            'name': 'Test Quality Team',
            'leader_id': cls.employee.id,
            'is_mail': False,
        })

        # ── Alert stage (quarantine seeded by data file) ──────────────────
        cls.alert_stage_quarantine = cls.env.ref(
            'cyllo_quality.quality_alert_stage_quarantine'
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_qcp(self, extra_inspections=None, **kwargs):
        """Create a minimal valid QualityControlPoint.

        ``extra_inspections`` is a list of dicts that override the default
        single Pass/Fail inspection; each dict is merged with sensible defaults.
        """
        inspections = extra_inspections or [{
            'inspection_action_id': self.inspection_action.id,
            'inspection_type_id': self.inspection_type_pass_fail.id,
        }]
        vals = {
            'operation_type_ids': [self.picking_type_in.id],
            'quality_team_id': self.quality_team.id,
            'control_type': 'operation',
            'control_by': 'all',
            'quality_inspection_ids': [
                (0, 0, {
                    'inspection_action_id': self.inspection_action.id,
                    'inspection_type_id': self.inspection_type_pass_fail.id,
                    **insp,
                })
                for insp in inspections
            ],
        }
        vals.update(kwargs)
        return self.env['quality.control.point'].create(vals)

    def _make_picking(self, picking_type=None, product=None, qty=5.0):
        """Create and confirm a stock.picking with one move."""
        picking_type = picking_type or self.picking_type_in
        product = product or self.product
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
            'move_ids': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': self.uom_unit.id,
                'location_id': self.location_src.id,
                'location_dest_id': self.location_dest.id,
            })],
        })
        return picking
