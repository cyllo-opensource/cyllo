# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#############################################################################
from odoo.tests.common import TransactionCase


class ShopfloorCommon(TransactionCase):
    """Create a small BoM and routing used by the Shopfloor test cases."""

    @classmethod
    def _create_product(cls, name, tracking='none'):
        ProductTemplate = cls.env['product.template']
        values = {
            'name': name,
            'detailed_type': 'product',
            'tracking': tracking,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        }

        # Databases can retain required columns after their defining addon is
        # removed. Supply temporary defaults when those fields are not loaded.
        stale_column_defaults = {
            'product_template': {
                'sale_line_warn': "'no-message'",
                'base_unit_count': '1.0',
            },
            'product_product': {
                'base_unit_count': '1.0',
            },
        }
        temporary_defaults = []
        model_by_table = {
            'product_template': ProductTemplate,
            'product_product': cls.env['product.product'],
        }
        for table, defaults in stale_column_defaults.items():
            cls.env.cr.execute("""
                SELECT column_name, column_default
                  FROM information_schema.columns
                 WHERE table_schema = current_schema()
                   AND table_name = %s
                   AND is_nullable = 'NO'
                   AND column_name = ANY(%s)
            """, [table, list(defaults)])
            for column_name, column_default in cls.env.cr.fetchall():
                model = model_by_table[table]
                if column_name in model._fields:
                    if table == 'product_template' and column_name == 'sale_line_warn':
                        values[column_name] = 'no-message'
                    continue
                if column_default is None:
                    cls.env.cr.execute(
                        'ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s'
                        % (table, column_name, defaults[column_name])
                    )
                    temporary_defaults.append((table, column_name))
        try:
            with cls.env.cr.savepoint():
                template = ProductTemplate.create(values)
        finally:
            for table, column_name in temporary_defaults:
                cls.env.cr.execute(
                    'ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT'
                    % (table, column_name)
                )
        return template.product_variant_id

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.production_location = cls.env['stock.location'].search(
            [('usage', '=', 'production')], limit=1
        )
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

        cls.finished_product = cls._create_product('Test Finished Product')
        cls.finished_product_lot = cls._create_product(
            'Test Finished Product (Lot Tracked)', tracking='lot'
        )
        cls.component_a = cls._create_product('Component A')
        cls.component_b = cls._create_product('Component B')

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
        mo = self.env['mrp.production'].create({
            'product_id': (product or self.finished_product).id,
            'product_qty': qty,
            'bom_id': (bom or self.bom).id,
        })
        if confirm:
            mo.action_confirm()
        return mo
