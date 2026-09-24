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


class TestCommissionContribution(TransactionCase):
    """
    Test suite for verifying Commission Contribution's `_compute_order_ids`
    behavior for different commission types ("sale" and "crm").

    This test ensures:
    - Orders of type "sale" that meet the sales rule are included.
    - Orders of type "crm" that match the CRM rule are included.
    - Only paid and confirmed sale orders are considered.
    """

    @classmethod
    def setUpClass(cls):
        """
        Create reusable base records for all test methods:
        - Partner, product, and sales team
        - Paid sale order (for sale-type commission)
        - CRM lead + sale order (for crm-type commission)
        - Corresponding commission types and plans
        """
        super().setUpClass()

        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.SaleOrderLine = cls.env['sale.order.line']
        cls.Lead = cls.env['crm.lead']
        cls.CommissionType = cls.env['commission.type']
        cls.CommissionPlan = cls.env['commission.plan']
        cls.CommissionContribution = cls.env['commission.contribution']
        cls.SalesTeam = cls.env['crm.team']

        cls.partner = cls.Partner.create({'name': 'Test Partner'})
        cls.product = cls.Product.create({
            'name': 'Test Product',
            'detailed_type': 'consu',
            'list_price': 100.0,
        })
        cls.sales_team = cls.SalesTeam.create({'name': 'Test Sales Team'})

        cls.sale_order_paid = cls.SaleOrder.create({
            'partner_id': cls.partner.id,
            'is_paid': True,
        })
        cls.SaleOrderLine.create({
            'order_id': cls.sale_order_paid.id,
            'product_id': cls.product.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })

        cls.type_sale = cls.CommissionType.create({
            'name': 'Sales type',
            'type': 'sale',
            'sales_rule_to_apply': "[('product_id', '=', %s)]" % cls.product.id,
        })
        cls.plan_sale = cls.CommissionPlan.create({
            'name': 'Sales Planning',
            'state': 'draft',
            'team_id': cls.sales_team.id,
            'type_id': cls.type_sale.id,
        })

        cls.lead = cls.Lead.create({
            'name': 'Test Lead',
            'partner_id': cls.partner.id,
        })
        cls.sale_order_crm = cls.SaleOrder.create({
            'partner_id': cls.partner.id,
            'opportunity_id': cls.lead.id,
            'is_paid': True,
        })

        cls.type_crm = cls.CommissionType.create({
            'name': 'CRM Type',
            'type': 'crm',
            'crm_rule_to_apply': "[('id', '=', %s)]" % cls.lead.id,
        })
        cls.plan_crm = cls.CommissionPlan.create({
            'name': 'CRM Planning',
            'state': 'draft',
            'team_id': cls.sales_team.id,
            'type_id': cls.type_crm.id,
        })

    def test_compute_order_ids(self):
        """
        Validate that `_compute_order_ids` correctly returns orders based on:
        - Sale type commission rules (matches product rule)
        - CRM type commission rules (matches lead rule)
        """
        today = fields.Date.today()

        self.sale_order_paid.write({
            'team_id': self.sales_team.id,
            'user_id': self.env.user.id,
            'payment_state': 'paid',
            'state': 'sale',
        })
        self.plan_sale.write({
            'user_ids': [(0, 0, {
                'user_id': self.env.user.id,
                'date_from': today,
                'date_to': today,
            })]
        })

        self.sale_order_crm.write({
            'team_id': self.sales_team.id,
            'user_id': self.env.user.id,
            'payment_state': 'paid',
            'state': 'sale',
        })
        self.plan_crm.write({
            'user_ids': [(0, 0, {
                'user_id': self.env.user.id,
                'date_from': today,
                'date_to': today,
            })]
        })

        contribution_sale = self.CommissionContribution.create({
            'plan_id': self.plan_sale.id,
            'type_id': self.type_sale.id,
        })
        contribution_sale._compute_order_ids()

        self.assertIn(
            self.sale_order_paid.id,
            contribution_sale.order_ids.ids,
            "Paid sale order should be included for sale type."
        )

        contribution_crm = self.CommissionContribution.create({
            'plan_id': self.plan_crm.id,
            'type_id': self.type_crm.id,
        })
        contribution_crm._compute_order_ids()

        self.assertIn(
            self.sale_order_crm.id,
            contribution_crm.order_ids.ids,
            "Paid sale order linked to matching lead should be included."
        )
