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

from odoo.tests import TransactionCase


class HelpdeskRepairTestCommon(TransactionCase):
    """Common test setup for Helpdesk Repair module tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for all test cases."""
        super().setUpClass()
        
        # Create test partner/customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'phone': '1234567890',
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product for Repair',
            'type': 'product',
            'list_price': 100.0,
        })
        
        # Create helpdesk team if needed
        cls.helpdesk_team = cls.env['helpdesk.team'].search([], limit=1)
        if not cls.helpdesk_team:
            cls.helpdesk_team = cls.env['helpdesk.team'].create({
                'name': 'Test Helpdesk Team',
            })
        
        # Create a sales order (for use in repair context)
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100.0,
                })
            ],
        })
        
    def setUp(self):
        """Set up for each test method."""
        super().setUp()
        self.helpdesk_ticket = None
        self.repair_order = None
