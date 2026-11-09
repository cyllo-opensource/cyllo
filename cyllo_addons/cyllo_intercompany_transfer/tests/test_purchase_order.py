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

from odoo.tests import tagged

from .common import IntercompanyCommon


@tagged('post_install', '-at_install')
class TestPurchaseOrder(IntercompanyCommon):

    def test_is_intercompany_purchase(self):
        self.assertTrue(self._create_po(self.partner_b)._is_intercompany_purchase())
        self.assertFalse(
            self._create_po(self.external_partner)._is_intercompany_purchase())

    def test_confirm_creates_intercompany_sale_order(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.partner_b, qty=10, price=100)
        po.button_confirm()

        so = po.intercompany_sale_order_id
        self.assertTrue(so)
        self.assertEqual(so.company_id, self.company_b)
        self.assertEqual(so.partner_id, self.partner_a)
        self.assertEqual(so.origin, po.name)
        self.assertTrue(so.intercompany_generated)
        self.assertEqual(so.intercompany_purchase_order_id, po)

    def test_sale_order_lines_mirror_purchase_lines(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.partner_b, qty=4, price=55.0)
        po.button_confirm()
        line = po.intercompany_sale_order_id.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_id, self.storable)
        self.assertEqual(line.product_uom_qty, 4)
        self.assertEqual(line.price_unit, 55.0)

    def test_receipt_is_put_on_hold(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.partner_b, qty=10)
        po.button_confirm()
        receipt = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming')
        self.assertTrue(receipt)
        self.assertTrue(receipt.intercompany_waiting)
        move = receipt.move_ids
        self.assertEqual(move.state, 'confirmed')
        self.assertEqual(move.intercompany_original_qty, 10)
        self.assertEqual(move.quantity, 0.0)

    def test_setting_disabled_creates_nothing(self):
        self._set_params(create_sale_orders=False)
        po = self._create_po(self.partner_b)
        po.button_confirm()
        self.assertFalse(po.intercompany_sale_order_id)
        receipt = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming')
        self.assertFalse(receipt.intercompany_waiting)

    def test_non_intercompany_vendor_creates_nothing(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.external_partner)
        po.button_confirm()
        self.assertFalse(po.intercompany_sale_order_id)
        receipt = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming')
        self.assertFalse(receipt.intercompany_waiting)

    def test_generated_purchase_order_creates_no_sale_order(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.partner_b)
        po.intercompany_generated = True
        po.button_confirm()
        self.assertFalse(po.intercompany_sale_order_id)

    def test_no_duplicate_sale_order(self):
        self._set_params(create_sale_orders=True)
        po = self._create_po(self.partner_b)
        po.button_confirm()
        so = po.intercompany_sale_order_id
        po.button_confirm()
        self.assertEqual(po.intercompany_sale_order_id, so)

    def test_create_returns_false_without_company_partner(self):
        po = self._create_po(self.external_partner)
        self.assertFalse(po._create_intercompany_sale_order())
