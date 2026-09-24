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
from odoo.tests.common import TransactionCase


class ShopfloorCommon(TransactionCase):
    """Shared fixtures for all cyllo_shopfloor test cases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # UoM
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        # Locations
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.production_location = cls.env['stock.location'].search(
            [('usage', '=', 'production')], limit=1
        )

        # Workcenters
        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line A',
            'time_start': 10,
            'time_stop': 5,
        })
        cls.workcenter_2 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line B',
            'time_start': 5,
            'time_stop': 5,
        })

        # Products
        cls.finished_product = cls.env['product.product'].create({
            'name': 'Test Finished Product',
            'type': 'product',
            'tracking': 'none',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })
        cls.finished_product_lot = cls.env['product.product'].create({
            'name': 'Test Finished Product (Lot Tracked)',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })
        cls.component_a = cls.env['product.product'].create({
            'name': 'Component A',
            'type': 'product',
            'tracking': 'none',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })
        cls.component_b = cls.env['product.product'].create({
            'name': 'Component B',
            'type': 'product',
            'tracking': 'none',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })

        # Bill of Materials
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.component_a.id,
                    'product_qty': 2.0,
                }),
                (0, 0, {
                    'product_id': cls.component_b.id,
                    'product_qty': 3.0,
                }),
            ],
            'operation_ids': [
                (0, 0, {
                    'name': 'Cutting',
                    'workcenter_id': cls.workcenter_1.id,
                    'time_cycle_manual': 30.0,
                }),
                (0, 0, {
                    'name': 'Welding',
                    'workcenter_id': cls.workcenter_2.id,
                    'time_cycle_manual': 60.0,
                }),
            ],
        })

    def _make_mo(self, product=None, qty=1.0, bom=None, confirm=True):
        """Helper: create (and optionally confirm) an MO."""
        mo = self.env['mrp.production'].create({
            'product_id': (product or self.finished_product).id,
            'product_qty': qty,
            'bom_id': (bom or self.bom).id,
        })
        if confirm:
            mo.action_confirm()
        return mo
