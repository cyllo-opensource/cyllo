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
from odoo.tests.common import HttpCase, tagged
import re

@tagged('post_install', '-at_install')
class TestProductReferral(HttpCase):
    """
    Test suite for the Product Referral controller in the
    `cyllo_crm_advance_lead` module.

    These tests ensure that:
    - The referral form (`/referral`) loads correctly with or without an order_id.
    - Submitting the referral form (`/referral/submit`) creates a CRM lead
      linked to the published products in the referenced sale order.
    """
    @classmethod
    def setUpClass(cls):
        """
        Test setup:
        - Create a partner to link with a sale order.
        - Create a sale order for the partner.
        - Create a published product.
        - Add the product to the sale order via a sale order line.
        """
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@test.com'
        })
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Referral Test Product',
            'list_price': 100,
            'is_published': True,
        })
        cls.env['sale.order.line'].create({
            'order_id': cls.order.id,
            'product_id': cls.product.id,
            'product_uom_qty': 1,
            'price_unit': cls.product.list_price,
        })

    def test_product_referral(self):
        """
        Test the `/referral` route:
        - When called with a valid order_id, the form should render
          and contain that order_id.
        - When called without an order_id, the form should still render
          but not include any order_id in the content.
        """
        url = f"/referral?order_id={self.order.id}"
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.order.id).encode(), response.content)
        response = self.url_open("/referral")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'order_id', response.content)

    def test_create_referral_lead(self):
        """
        Test the `/referral/submit` route:
        - Submits the referral form with a CSRF token and friend details.
        - Checks that the response returns 200 with a "Thank You" message.
        - Verifies that a CRM lead is created with the submitted friend's
          details and the correct referral product count.
        """
        url = f"/referral?order_id={self.order.id}"
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)

        match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        self.assertTrue(match, "CSRF token not found in referral form")
        csrf_token = match.group(1)

        post_data = {
            'sale_order': str(self.order.id),
            'friend_name': 'John Doe',
            'friend_email': 'john@example.com',
            'friend_phone': '9999999999',
            'csrf_token': csrf_token,
        }
        response = self.url_open(url="/referral/submit", data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Thank You', response.content)

        lead = self.env['crm.lead'].sudo().search(
            [('email_from', '=', 'john@example.com')], limit=1)
        self.assertTrue(lead, "Referral lead was not created")
        self.assertEqual(lead.contact_name, 'John Doe')
        self.assertEqual(lead.referral_product_count, 1)
