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
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestHelpdeskPurchase(TransactionCase):
    """Test suite for the Cyllo Helpdesk Purchase integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a parent partner (commercial partner)
        cls.parent_partner = cls.env['res.partner'].create({
            'name': 'Parent Supplier Company',
            'is_company': True,
        })

        # Create a child partner (supplier contact)
        cls.customer = cls.env['res.partner'].create({
            'name': 'Child Supplier Contact',
            'parent_id': cls.parent_partner.id,
        })

        # Create a helpdesk team
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Vendor Support Team',
        })

        # Create purchase orders for parent and child partner
        cls.po_parent = cls.env['purchase.order'].create({
            'partner_id': cls.parent_partner.id,
        })

        cls.po_child = cls.env['purchase.order'].create({
            'partner_id': cls.customer.id,
        })

    def test_compute_customer_purchase_order_count(self):
        """Test that customer_purchase_order_count includes POs from the whole commercial hierarchy."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Vendor Inquiry Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        ticket._compute_customer_purchase_order_count()
        # Should count both cls.po_parent and cls.po_child (total of 2)
        self.assertEqual(ticket.customer_purchase_order_count, 2,
                         "Purchase order count should sum all POs belonging to the commercial partner hierarchy.")

        # Test behavior when no customer is set
        ticket_no_cust = self.env['helpdesk.ticket'].create({
            'name': 'Anonymous Ticket',
            'team_id': self.team.id,
            'customer_id': False,
        })
        ticket_no_cust._compute_customer_purchase_order_count()
        self.assertEqual(ticket_no_cust.customer_purchase_order_count, 0)

    def test_action_view_customer_purchase_orders(self):
        """Test that action_view_customer_purchase_orders returns an action filtered by commercial partner."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Order Status Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        action = ticket.action_view_customer_purchase_orders()

        self.assertEqual(action.get('view_mode'), 'tree')
        self.assertEqual(action.get('views')[0][1], 'tree')

        expected_domain = [('partner_id', 'child_of', self.customer.commercial_partner_id.id)]
        self.assertEqual(action.get('domain'), expected_domain)
