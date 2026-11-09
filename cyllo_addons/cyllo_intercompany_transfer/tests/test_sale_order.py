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
class TestSaleOrder(IntercompanyCommon):

    def test_confirm_creates_intercompany_purchase_order(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.partner_b, qty=5, price=200)
        so.action_confirm()

        po = so.intercompany_purchase_order_id
        self.assertTrue(po)
        self.assertEqual(po.company_id, self.company_b)
        self.assertEqual(po.partner_id, self.partner_a)
        self.assertEqual(po.origin, so.name)
        self.assertTrue(po.intercompany_generated)
        self.assertEqual(po.intercompany_sale_order_id, so)

    def test_purchase_order_lines_mirror_sale_lines(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.partner_b, qty=7, price=123.0)
        so.action_confirm()
        line = so.intercompany_purchase_order_id.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_id, self.storable)
        self.assertEqual(line.product_qty, 7)
        self.assertEqual(line.price_unit, 123.0)

    def test_setting_disabled_creates_nothing(self):
        self._set_params(create_purchase_orders=False)
        so = self._create_so(self.partner_b)
        so.action_confirm()
        self.assertFalse(so.intercompany_purchase_order_id)

    def test_non_intercompany_customer_creates_nothing(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.external_partner)
        so.action_confirm()
        self.assertFalse(so.intercompany_purchase_order_id)

    def test_generated_sale_order_is_skipped(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.partner_b)
        so.intercompany_generated = True
        so.action_confirm()
        self.assertFalse(so.intercompany_purchase_order_id)

    def test_no_duplicate_purchase_order(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.partner_b)
        so.action_confirm()
        po = so.intercompany_purchase_order_id
        so.state = 'draft'
        so.action_confirm()
        self.assertEqual(so.intercompany_purchase_order_id, po)
        count = self.env['purchase.order'].sudo().search_count([
            ('origin', '=', so.name), ('company_id', '=', self.company_b.id)])
        self.assertEqual(count, 1)

    def test_create_returns_false_without_company_partner(self):
        so = self._create_so(self.external_partner)
        self.assertFalse(so._create_intercompany_purchase_order())

    def test_links_not_copied(self):
        self._set_params(create_purchase_orders=True)
        so = self._create_so(self.partner_b)
        so.action_confirm()
        copy = so.copy()
        self.assertFalse(copy.intercompany_purchase_order_id)
        self.assertFalse(copy.intercompany_generated)
