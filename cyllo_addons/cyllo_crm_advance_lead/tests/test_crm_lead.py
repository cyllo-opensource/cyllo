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
from odoo import fields
from datetime import timedelta


class TestCrmLead(TransactionCase):
    """
    Test suite for CRM Lead customizations related to:
    - Wishlist products
    - Abandoned cart quotations
    - Wishlist → Lead conversion
    """
    @classmethod
    def setUpClass(cls):
        """
        Prepare test data:
        - Products (used in wishlist and referrals)
        - CRM Lead for base testing
        - Sale orders for abandoned cart scenarios
        - Partner, Website, Wishlist entries
        - Configuration parameters for abandoned cart & wishlist jobs
        """
        super().setUpClass()
        cls.product1 = cls.env['product.product'].create({
            'name': 'Wishlist Product A',
            'list_price': 100,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Referral Product B',
            'list_price': 200,
        })
        cls.product3 = cls.env['product.product'].create({
            'name': 'Wishlist Product C',
            'list_price': 300,
        })
        cls.product4 = cls.env['product.product'].create({
            'name': 'Referral Product D',
            'list_price': 400,
        })
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead',
        })
        cls.sale_order1 = cls.env['sale.order'].create({
            'partner_id': cls.env['res.partner'].create(
                {'name': 'Customer A'}).id,
        })
        cls.sale_order2 = cls.env['sale.order'].create({
            'partner_id': cls.env['res.partner'].create(
                {'name': 'Customer B'}).id,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Wishlist Partner'
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Wishlist Product',
        })
        cls.website = cls.env['website'].create({
            'name': 'Test Website',
        })
        cls.wishlist = cls.env['product.wishlist'].create({
            'partner_id': cls.partner.id,
            'product_id': cls.product.id,
            'website_id': cls.website.id,
            'create_date': fields.Datetime.now() - timedelta(days=5),
        })

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'is_abandoned_cart': True,
            'date_order': fields.Datetime.now() - timedelta(days=10),
        })
        config = cls.env['ir.config_parameter'].sudo()
        config.set_param('cyllo_crm_advance_lead.create_lead_abandoned_cart',
                         'True')
        config.set_param('cyllo_crm_advance_lead.abandoned_cart_days', '5')

    def test_prepare_opportunity_quotation_context(self):
        """
         Ensure wishlist products are correctly injected into
        the quotation context for a CRM lead.

        Steps:
        1. Verify empty context when no wishlist products exist.
        2. Add a product to the lead's wishlist.
        3. Verify `default_order_line` contains the product with correct price.
        """
        lead = self.lead
        ctx = lead._prepare_opportunity_quotation_context()
        self.assertNotIn('default_product_id', ctx)
        self.assertEqual(ctx.get('default_order_line'), [])

        lead.wishlist_product_ids = [self.product1.id]
        ctx = lead._prepare_opportunity_quotation_context()
        order_lines = ctx.get('default_order_line')
        self.assertTrue(order_lines)
        vals = order_lines[0][2]
        self.assertEqual(vals['product_id'], self.product1.id)
        self.assertEqual(vals['price_unit'], 100)

    def test_action_view_abandoned_sale_quotation(self):
        """
        Verify the action window returned by viewing abandoned sale quotations.

        Cases:
        - No orders linked → list view with empty domain
        - Single order linked → form view with that order
        - Multiple orders linked → list view with domain on those orders
        """
        self.lead.order_ids = [(6, 0, [])]  # Clear orders
        action = self.lead.action_view_abandoned_sale_quotation()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertEqual(action['domain'], [('id', 'in', [])])
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])
        self.assertNotIn('res_id', action)
        self.lead.order_ids = [(6, 0, [self.sale_order1.id])]
        action = self.lead.action_view_abandoned_sale_quotation()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], self.sale_order1.id)
        self.lead.order_ids = [
            (6, 0, [self.sale_order1.id, self.sale_order2.id])]
        action = self.lead.action_view_abandoned_sale_quotation()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])
        self.assertEqual(action['domain'], [('id', 'in', [self.sale_order1.id,
                                                          self.sale_order2.id])])
        self.assertNotIn('res_id', action)

    def test_action_view_wishlist_products(self):
        """
        Verify the action returned when viewing wishlist products of a lead.

        Cases:
        - No wishlist products → list view with empty domain
        - One wishlist product → form view with that product
        """
        lead = self.lead
        lead.write({'wishlist_product_ids': [(6, 0, [])]})
        action = lead.action_view_wishlist_products()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'product.product')
        self.assertEqual(action['domain'], [('id', 'in', [])])
        self.assertIn('list,form', action['view_mode'])
        lead.write({'wishlist_product_ids': [(6, 0, [self.product1.id])]})
        action = lead.action_view_wishlist_products()
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], self.product1.id)

    def test_create_lead_for_wishlist_products(self):
        """
        Ensure leads are created from wishlist products when
        the scheduled job `_create_lead_for_wishlist_products` is run.

        Steps:
        1. Enable config for wishlist → lead creation.
        2. Run the cron method.
        3. Validate:
           - Lead created
           - Correct partner linked
           - Wishlist products linked to the lead
        """
        config = self.env['ir.config_parameter'].sudo()
        config.set_param('cyllo_crm_advance_lead.create_lead_wishlist', 'True')
        config.set_param('cyllo_crm_advance_lead.wishlist_days', '0')
        self.assertFalse(self.wishlist.lead_id)
        self.env['crm.lead']._create_lead_for_wishlist_products()
        lead = self.wishlist.lead_id
        self.assertTrue(lead)
        self.assertEqual(lead.partner_id, self.partner)
        self.assertIn(self.product, lead.wishlist_product_ids)
        self.assertEqual(lead.wishlist_product_count, 1)
