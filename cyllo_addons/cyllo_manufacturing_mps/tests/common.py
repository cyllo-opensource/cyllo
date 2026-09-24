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

from odoo.tests import common


class MpsCommon(common.TransactionCase):
    """Shared data for Manufacturing MPS tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Schedule = cls.env['mrp.mps.schedule']
        cls.Product = cls.env['product.product']
        cls.Bom = cls.env['mrp.bom']
        cls.Partner = cls.env['res.partner']

        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.manufacture_route = cls.env.ref('mrp.route_warehouse0_manufacture')

        cls.vendor = cls.Partner.create({'name': 'MPS Test Vendor'})
        cls.buy_product = cls.Product.create({
            'name': 'MPS Buy Product',
            'type': 'product',
            'route_ids': [(6, 0, [cls.buy_route.id])],
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
                'price': 10.0,
            })],
        })
        cls.component = cls.Product.create({
            'name': 'MPS Component',
            'type': 'product',
            'route_ids': [(6, 0, [cls.buy_route.id])],
        })
        cls.manufactured_product = cls.Product.create({
            'name': 'MPS Manufactured Product',
            'type': 'product',
            'route_ids': [(6, 0, [cls.manufacture_route.id])],
        })
        cls.bom = cls.Bom.create({
            'product_id': cls.manufactured_product.id,
            'product_tmpl_id': cls.manufactured_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.component.id,
                'product_qty': 2.0,
            })],
        })

    def _create_schedule(self, product, route, **values):
        vals = {
            'product_id': product.id,
            'route_id': route.id,
            'forcast_target_quantity': 20.0,
            'min_to_replenish_qty': 5.0,
            'replenishment_mode': 'manual',
        }
        vals.update(values)
        return self.Schedule.create(vals)

