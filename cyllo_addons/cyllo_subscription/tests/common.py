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
from odoo import fields
from odoo.tests import common

class TestCylloSubscription(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'John',
            'street': 'street1',
            'street2': 'street2',
            'email': 'John@gmail.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': True
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'SP1',
            'is_subscription': False
        })
        cls.subscription_product1 = cls.env['product.product'].create({
            'name': 'Subscription Product1',
            'is_subscription': True,
        })
        cls.subscription_product2 = cls.env['product.product'].create({
            'name': 'Subscription Product2',
            'is_subscription': True,
        })
        cls.non_subscription_product = cls.env['product.product'].create({
            'name': 'Non-Subscription Product',
            'is_subscription': False,
        })
        cls.time_based = cls.env['time.based.price'].create({
            'name': 'Mon',
            'subscription_unit': 'months',
            'currency_id': 1,
            'duration': 24
        })
        cls.sale_order_template = cls.env['sale.order.template'].create({
            'name': 'Template1',
            'is_subscription': True,
            'invoice_creation': 'confirmed',
            'sale_order_template_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.sale_order = cls.env['sale.order'].create({
            'name': 'S00001',
            'partner_id': cls.partner.id,
            'order_line': [
                (fields.Command.create({'product_id': cls.product.id}))
            ]
        })
        cls.sale_order2 = cls.env['sale.order'].create({
            'name': 'S00002',
            'partner_id': cls.partner.id,
            'order_line': [
                (fields.Command.create({'product_id': cls.product.id}))
            ]
        })
        cls.sale_order3 = cls.env['sale.order'].create({
            'name': 'S00002',
            'partner_id': cls.partner.id,
        })
        cls.sale_order4 = cls.env['sale.order'].create({
            'name': 'S00002',
            'partner_id': cls.partner.id,
            'order_line': [fields.Command.create({
                                'product_id': cls.subscription_product1.id,
                                'product_uom_qty': 1,
                                'price_unit': 50.0,
                                'time_based_price_id': cls.time_based.id,
                                'trial_end': '2025-11-30',
                            }), fields.Command.create({
                                'product_id': cls.non_subscription_product.id,
                                'product_uom_qty': 1,
                                'price_unit': 50.0,
                                'time_based_price_id': cls.time_based.id,
                                'trial_end': '2025-11-30',
                            })],
            })
        cls.sale_order5 = cls.env['sale.order'].create({
            'name': 'S000010',
            'partner_id': cls.partner.id,
            'order_line': [fields.Command.create({
                'product_id': cls.subscription_product1.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
                'time_based_price_id': cls.time_based.id,
                'trial_end': '2025-11-30',
            })],
        })
        cls.subscription_order1 = cls.env['subscription.order'].create({
            'name': 'SO001',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order.id,
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.subscription_order2 = cls.env['subscription.order'].create({
            'name': 'SO002',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order2.id,
            'state': 'sale',
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.subscription_order3 = cls.env['subscription.order'].create({
            'name': 'SO003',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order2.id,
            'state': 'posted',
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.subscription_order4 = cls.env['subscription.order'].create({
            'name': 'SO004',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order2.id,
            'state': 'draft',
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.subscription_order5 = cls.env['subscription.order'].create({
            'name': 'SO0011',
            'partner_id': cls.partner.id,
            'time_based_price_id': cls.time_based.id,
            'sale_order_template_id': cls.sale_order_template.id,
            'renewal_date': '2023-11-16',
            'sale_order_id': cls.sale_order5.id,
            'state': 'draft',
            'subscription_order_line_ids': [
                (fields.Command.create({'product_id': cls.product.id}))]
        })
        cls.account_move = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'payment_reference': cls.subscription_order1.name,
            'invoice_origin': cls.subscription_order1.name,
            'invoice_date_due': '2023-12-15',
            'date': '2023-12-15',
            'is_subscription': True,
            'state': 'draft',
            'subscription_order_id': cls.subscription_order1.id,
            'invoice_line_ids': [
                (fields.Command.create({
                    'product_id': cls.product.id,
                }))]})
        cls.account_move2 = cls.env['account.move'].create({
            'partner_id': cls.partner.id,
            'move_type': 'out_invoice',
            'payment_reference': cls.subscription_order4.name,
            'invoice_origin': cls.subscription_order4.name,
            'invoice_date_due': '2023-12-15',
            'date': '2023-12-15',
            'is_subscription': True,
            'state': 'draft',
            'subscription_order_id': cls.subscription_order4.id,
            'invoice_line_ids': [
                (fields.Command.create({
                    'product_id': cls.product.id,
                }))]})
        cls.sale_order2 = cls.env['sale.order'].create({
            'name': 'S00002',
            'partner_id': cls.partner.id,
            'order_line': [
                (fields.Command.create({'product_id': cls.product2.id}))
            ]
        })
        cls.subscription_order_alert = cls.env['subscription.order.alert'].create({
            'name': 'Sub alert',
            'action': 'set_to_renew'
        })
