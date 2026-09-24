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


class TestProjectProductBase(TransactionCase):
    """Shared fixtures for cyllo_project_product tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@example.com',
        })

        # Products
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
            'list_price': 100.0,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'consu',
            'list_price': 200.0,
        })

        # Project with products enabled
        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
            'partner_id': cls.partner.id,
            'allow_task_products': True,
            'allow_extra_quotations': True,
        })

        # Project without products enabled
        cls.project_plain = cls.env['project.project'].create({
            'name': 'Plain Project',
            'partner_id': cls.partner.id,
            'allow_task_products': False,
            'allow_extra_quotations': False,
        })

        # Sale order linked to project
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

        # Task inside the products-enabled project
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task',
            'project_id': cls.project.id,
            'partner_id': cls.partner.id,
            'related_sale_order_id': cls.sale_order.id,
        })

        # Task without a partner or sale order
        cls.task_bare = cls.env['project.task'].create({
            'name': 'Bare Task',
            'project_id': cls.project.id,
        })
