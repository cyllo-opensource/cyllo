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

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MpsCommon


@tagged('post_install', '-at_install')
class TestMrpMpsSchedule(MpsCommon):
    """Tests for MPS schedule backend behavior."""

    def test_01_update_period_data_persists_json_values(self):
        schedule = self._create_schedule(self.buy_product, self.buy_route)

        self.Schedule.update_period_data(
            schedule.id,
            {'Jul 2026': 7.0},
            {'Jul 2026': 4.0},
            {'Jul 2026': True},
        )

        self.assertEqual(json.loads(schedule.saved_demand), {'Jul 2026': 7.0})
        self.assertEqual(json.loads(schedule.saved_replenishment), {'Jul 2026': 4.0})
        self.assertEqual(json.loads(schedule.saved_manual_repl), {'Jul 2026': True})

    def test_02_get_product_data_includes_bom_component_schedule(self):
        component_schedule = self._create_schedule(
            self.component,
            self.buy_route,
            replenishment_mode='never',
        )
        manufactured_schedule = self._create_schedule(
            self.manufactured_product,
            self.manufacture_route,
            bom_id=self.bom.id,
            saved_demand='not valid json',
        )

        product_data = self.Schedule.get_product_data()
        manufactured_data = next(
            item for item in product_data if item['id'] == manufactured_schedule.id
        )

        self.assertEqual(manufactured_data['name'], self.manufactured_product.display_name)
        self.assertEqual(manufactured_data['saved_demand'], {})
        self.assertEqual(manufactured_data['min_qty'], 5.0)
        self.assertEqual(manufactured_data['target_qty'], 20.0)
        self.assertEqual(manufactured_data['bom_components'], [{
            'schedule_id': component_schedule.id,
            'qty': 2.0,
        }])

    def test_03_create_purchase_order_for_buy_route(self):
        schedule = self._create_schedule(self.buy_product, self.buy_route)
        before_orders = self.env['purchase.order'].search_count([
            ('partner_id', '=', self.vendor.id),
        ])

        result = self.Schedule.create_purchase_manufacture_orders({
            str(schedule.id): 3.0,
            '0': 0.0,
        })

        order = self.env['purchase.order'].search(
            [('partner_id', '=', self.vendor.id)],
            order='id desc',
            limit=1,
        )
        self.assertTrue(result)
        self.assertEqual(
            self.env['purchase.order'].search_count([('partner_id', '=', self.vendor.id)]),
            before_orders + 1,
        )
        self.assertEqual(order.order_line.product_id, self.buy_product)
        self.assertEqual(order.order_line.product_qty, 3.0)

    def test_04_create_manufacturing_order_for_manufacture_route(self):
        schedule = self._create_schedule(
            self.manufactured_product,
            self.manufacture_route,
            bom_id=self.bom.id,
        )

        self.Schedule.create_purchase_manufacture_orders({str(schedule.id): 6.0})

        production = self.env['mrp.production'].search(
            [('product_id', '=', self.manufactured_product.id)],
            order='id desc',
            limit=1,
        )
        self.assertTrue(production)
        self.assertEqual(production.product_qty, 6.0)
        self.assertEqual(production.bom_id, self.bom)

    def test_05_create_orders_raises_for_missing_vendor_or_bom(self):
        product_without_vendor = self.Product.create({
            'name': 'MPS No Vendor Product',
            'type': 'product',
            'route_ids': [(6, 0, [self.buy_route.id])],
        })
        buy_schedule = self._create_schedule(product_without_vendor, self.buy_route)
        manufacture_schedule = self._create_schedule(
            self.manufactured_product,
            self.manufacture_route,
        )

        with self.assertRaises(UserError):
            self.Schedule.create_purchase_manufacture_orders({str(buy_schedule.id): 1.0})

        with self.assertRaises(UserError):
            self.Schedule.create_purchase_manufacture_orders({str(manufacture_schedule.id): 1.0})

    def test_06_cron_creates_orders_for_current_period_only(self):
        current_label = date.today().strftime('%b %Y')
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_manufacturing_mps.default_timerange',
            'month',
        )
        automated_schedule = self._create_schedule(
            self.buy_product,
            self.buy_route,
            replenishment_mode='automated',
            saved_replenishment=json.dumps({current_label: 2.0, 'Other': 9.0}),
        )
        self._create_schedule(
            self.buy_product,
            self.buy_route,
            replenishment_mode='manual',
            saved_replenishment=json.dumps({current_label: 8.0}),
        )

        self.Schedule._cron_automate_mps_orders()

        order_line = self.env['purchase.order.line'].search(
            [
                ('product_id', '=', automated_schedule.product_id.id),
                ('product_qty', '=', 2.0),
            ],
            limit=1,
        )
        self.assertTrue(order_line)

