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
import logging

from odoo.tests.common import Form, TransactionCase

_LOGGER = logging.getLogger(__name__)


class TestDeliveryCarrier(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Drawer = cls.env['product.product'].create({
            'name': 'Drawer',
            'weight': 0.01,
        })
        cls.Large_table = cls.env['product.product'].create({
            'name': 'Large table',
            'weight': 0.01,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.Partner = cls.env['res.partner'].create({'name': 'Partner'})
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.delivery_carrier_dhl_product = cls.env.ref(
            'cyllo_dhl_connector.product_product_dhl_shipping',
            raise_if_not_found=False)
        cls.dhl_carrier = cls.env['delivery.carrier'].create({
            'name': 'Dhl carrier',
            'delivery_type': 'fixed',
            'product_id': cls.delivery_carrier_dhl_product.id,
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)

    def test_dhl_flow(cls):
        SaleOrder = cls.env['sale.order']
        sol_vals = {'product_id': cls.Drawer.id,
                    'name': "[K1245] Large table",
                    'product_uom': cls.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': cls.Drawer.lst_price}
        so_vals = {'partner_id': cls.Partner.id,
                   'order_line': [(0, None, sol_vals)]}
        sale_order = SaleOrder.create(so_vals)
        cls.assertTrue(sale_order, "Sale Order should be created")
        cls.assertTrue(cls.delivery_carrier_dhl_product,
                       "Delivery Carrier DHL should exist")
        # I add free delivery cost in Sales order
        delivery_wizard = Form(cls.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': cls.dhl_carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        # DHL test server will return 0.0...
        choose_delivery_carrier.button_confirm()
        picking_ship = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_id.name == 'Pick')
        picking_ship.action_confirm()
        picking_ship.move_ids.quantity = 1.0
        # DHL test picking validate
        picking_ship.move_ids.picked = True
        picking_ship.button_validate()

    def test_shipment_sales_order_and_picking(cls):
        """ Verify the validation of a shipment with a designated carrier when
        it is not associated with a sales order. """
        picking = cls.env['stock.picking'].create({
            'partner_id': cls.env['res.partner'].create(
                {'name': 'A partner'}).id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.warehouse.out_type_id.id,
            'carrier_id': cls.dhl_carrier.id
        })
        cls.env['stock.move.line'].create({
            'product_id': cls.Drawer.id,
            'picking_id': picking.id,
            'quantity': 5,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id
        })
        cls.assertEqual(picking.state, 'draft')
        cls.assertFalse(picking.sale_id.id,)
        picking.move_ids.picked = True
        picking.button_validate()
        cls.assertEqual(picking.state, 'done')
