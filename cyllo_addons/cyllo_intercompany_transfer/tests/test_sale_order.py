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
from odoo.tests import common

class TestSaleOrder(common.TransactionCase):
    def setUp(self):
        super(TestSaleOrder, self).setUp()
        self.company_a = self.env.user.company_id
        self.company_b = self.env['res.company'].create({
            'name': 'Company B',
        })
        self.partner_b = self.company_b.partner_id
        
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })
        

        self.env['ir.config_parameter'].sudo().set_param('cyllo_intercompany_transfer.create_purchase_orders', True)

    def test_intercompany_sale(self):
        """Test intercompany SO confirmation"""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_b.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5,
                'price_unit': 200,
            })]
        })
        
        so.action_confirm()
        
        self.assertTrue(so.intercompany_purchase_order_id)
        self.assertEqual(so.intercompany_purchase_order_id.company_id.id, self.company_b.id)
        self.assertEqual(so.intercompany_purchase_order_id.intercompany_sale_order_id.id, so.id)
