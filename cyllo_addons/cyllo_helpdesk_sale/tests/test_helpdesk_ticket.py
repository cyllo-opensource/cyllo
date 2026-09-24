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

from .test_common import HelpdeskSaleTestCommon


class TestHelpDeskTicketSaleFields(HelpdeskSaleTestCommon):
    """Test field definitions for helpdesk ticket sale integration."""

    def test_sale_order_id_many2one_field(self):
        """Test sale_order_id many2one field exists."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertTrue(hasattr(ticket, 'sale_order_id'))
        self.assertFalse(ticket.sale_order_id)
    
    def test_sale_order_line_id_many2one_field(self):
        """Test sale_order_line_id many2one field exists."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertTrue(hasattr(ticket, 'sale_order_line_id'))
        self.assertFalse(ticket.sale_order_line_id)
    
    def test_sale_order_ids_one2many_field(self):
        """Test sale_order_ids one2many field exists."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertTrue(hasattr(ticket, 'sale_order_ids'))
        self.assertEqual(len(ticket.sale_order_ids), 0)
    
    def test_sale_order_count_computed_field(self):
        """Test sale_order_count computed field."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertEqual(ticket.sale_order_count, 0)
    
    def test_customer_sale_order_count_computed_field(self):
        """Test customer_sale_order_count computed field."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertEqual(ticket.customer_sale_order_count, 0)


class TestHelpDeskTicketSaleOrders(HelpdeskSaleTestCommon):
    """Test sale order linking and count computation."""

    def test_link_ticket_to_sale_order(self):
        """Test linking helpdesk ticket to a sale order."""
        # Create sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        # Create and confirm sale order
        sale_order.action_confirm()
        
        # Create ticket and link to sale order
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
            'sale_order_id': sale_order.id,
        })
        
        self.assertEqual(ticket.sale_order_id, sale_order)
    
    def test_sale_order_count_increments(self):
        """Test sale_order_count increments when SO linked."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        self.assertEqual(ticket.sale_order_count, 0)
        
        # Create and link first sale order
        sale_order1 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order1.action_confirm()
        
        self.assertEqual(ticket.sale_order_count, 1)
        
        # Create and link second sale order
        sale_order2 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product2.id,
                'product_qty': 2,
                'price_unit': 50.0,
            })]
        })
        sale_order2.action_confirm()
        
        self.assertEqual(ticket.sale_order_count, 2)
    
    def test_customer_sale_order_count_with_commercial_partner(self):
        """Test customer_sale_order_count counts all customer orders."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create sale orders for main customer and child partner
        sale_order1 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order1.action_confirm()
        
        sale_order2 = self.env['sale.order'].create({
            'partner_id': self.child_partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order2.action_confirm()
        
        # Both should be counted under commercial partner
        self.assertEqual(ticket.customer_sale_order_count, 2)


class TestHelpDeskTicketSaleActions(HelpdeskSaleTestCommon):
    """Test action methods for sale order management."""

    def test_action_create_sale_order(self):
        """Test action_create_sale_order returns proper context."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        action = ticket.action_create_sale_order()
        
        self.assertIsInstance(action, dict)
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')
        
        context = action.get('context', {})
        self.assertEqual(context['default_partner_id'], self.customer.id)
        self.assertEqual(context['default_helpdesk_ticket_id'], ticket.id)
    
    def test_action_view_sale_orders_filter(self):
        """Test action_view_sale_orders returns correct domain."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        action = ticket.action_view_sale_orders()
        
        self.assertIsInstance(action, dict)
        domain = action.get('domain', [])
        self.assertEqual(domain, [('helpdesk_ticket_id', '=', ticket.id)])
    
    def test_action_view_customer_sale_orders(self):
        """Test action_view_customer_sale_orders shows customer's orders."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        action = ticket.action_view_customer_sale_orders()
        
        domain = action.get('domain', [])
        # Should filter by commercial partner
        self.assertIn('child_of', str(domain))
        
        # Should be in read-only mode
        context = action.get('context', {})
        self.assertFalse(context.get('create', True))
        self.assertFalse(context.get('edit', True))


class TestHelpDeskTicketSaleOnchange(HelpdeskSaleTestCommon):
    """Test onchange behavior for customer_id field."""

    def test_onchange_customer_clears_sale_order(self):
        """Test changing customer clears sale_order_id."""
        # Create initial ticket with customer
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create and set a sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order.action_confirm()
        ticket.sale_order_id = sale_order.id
        
        # Create different customer
        other_customer = self.env['res.partner'].create({
            'name': 'Other Customer',
            'email': 'other@test.com',
        })
        
        # Change customer - should clear sale order
        ticket.customer_id = other_customer.id
        ticket._onchange_customer_id_sale()
        
        # sale_order_id should be cleared when customer changes
        self.assertFalse(ticket.sale_order_id)
    
    def test_onchange_customer_clears_order_line(self):
        """Test changing customer clears sale_order_line_id."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create sale order with lines
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order.action_confirm()
        
        ticket.sale_order_id = sale_order.id
        ticket.sale_order_line_id = sale_order.order_line[0].id
        
        # Create different customer
        other_customer = self.env['res.partner'].create({
            'name': 'Other Customer',
            'email': 'other@test.com',
        })
        
        # Change customer
        ticket.customer_id = other_customer.id
        ticket._onchange_customer_id_sale()
        
        # Both should be cleared
        self.assertFalse(ticket.sale_order_id)
        self.assertFalse(ticket.sale_order_line_id)
    
    def test_onchange_customer_filters_sale_orders(self):
        """Test onchange returns domain filtering orders by customer."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        result = ticket._onchange_customer_id_sale()
        
        # Should have domain with customer filter
        self.assertIn('domain', result)
        domain = result['domain'].get('sale_order_id', [])
        
        # Domain should include partner filter and state filter
        self.assertTrue(len(domain) > 0)
    
    def test_onchange_no_customer_clears_fields(self):
        """Test clearing customer clears all sale fields."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Set sale order and line
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order.action_confirm()
        ticket.sale_order_id = sale_order.id
        ticket.sale_order_line_id = sale_order.order_line[0].id
        
        # Clear customer
        ticket.customer_id = False
        ticket._onchange_customer_id_sale()
        
        self.assertFalse(ticket.sale_order_id)
        self.assertFalse(ticket.sale_order_line_id)


class TestHelpDeskTicketSaleIntegration(HelpdeskSaleTestCommon):
    """Integration tests for helpdesk-sale workflows."""
    
    def test_create_sale_order_from_ticket(self):
        """Test full workflow: ticket -> create SO -> manage SO."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Customer Issue',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Get action for creating SO
        action = ticket.action_create_sale_order()
        context = action['context']
        
        # Create SO with context
        sale_order = self.env['sale.order'].create({
            'partner_id': context['default_partner_id'],
            'helpdesk_ticket_id': context['default_helpdesk_ticket_id'],
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        sale_order.action_confirm()
        
        # Verify ticket sees the SO
        self.assertEqual(ticket.sale_order_count, 1)
        self.assertIn(sale_order, ticket.sale_order_ids)
    
    def test_multiple_sales_orders_per_ticket(self):
        """Test ticket can have multiple sales orders."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Issue',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        sale_orders = []
        for i in range(3):
            so = self.env['sale.order'].create({
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_qty': i + 1,
                    'price_unit': 100.0,
                })]
            })
            so.action_confirm()
            sale_orders.append(so)
        
        self.assertEqual(ticket.sale_order_count, 3)
        self.assertEqual(set(ticket.sale_order_ids), set(sale_orders))
    
    def test_sale_order_line_domain_filtering(self):
        """Test sale_order_line_id domain filters by sale_order_id."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create SO with multiple lines
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_qty': 1,
                    'price_unit': 100.0,
                }),
                (0, 0, {
                    'product_id': self.product2.id,
                    'product_qty': 2,
                    'price_unit': 50.0,
                })
            ]
        })
        sale_order.action_confirm()
        
        # Link SO to ticket
        ticket.sale_order_id = sale_order.id
        
        # Verify sale_order_line can be selected from this SO
        lines = sale_order.order_line
        self.assertEqual(len(lines), 2)
        
        ticket.sale_order_line_id = lines[0].id
        self.assertEqual(ticket.sale_order_line_id, lines[0])
