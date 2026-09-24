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


class TestSaleOrderEnhancements(HelpdeskSaleTestCommon):
    """Test SaleOrder model enhancements."""

    def test_helpdesk_ticket_id_field_exists(self):
        """Test helpdesk_ticket_id many2one field exists."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertTrue(hasattr(sale_order, 'helpdesk_ticket_id'))
        self.assertFalse(sale_order.helpdesk_ticket_id)
    
    def test_link_sale_order_to_helpdesk_ticket(self):
        """Test linking sale order to helpdesk ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertEqual(sale_order.helpdesk_ticket_id, ticket)
        self.assertIn(sale_order, ticket.sale_order_ids)
    
    def test_helpdesk_ticket_id_field_indexed(self):
        """Test helpdesk_ticket_id field is indexed."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create multiple SOs linked to ticket
        sale_orders = []
        for i in range(3):
            so = self.env['sale.order'].create({
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_qty': 1,
                    'price_unit': 100.0,
                })]
            })
            sale_orders.append(so)
        
        # Search by helpdesk_ticket_id should be efficient
        found_orders = self.env['sale.order'].search([
            ('helpdesk_ticket_id', '=', ticket.id)
        ])
        
        self.assertEqual(len(found_orders), 3)
        self.assertEqual(set(found_orders), set(sale_orders))
    
    def test_sale_order_without_helpdesk_ticket(self):
        """Test sale order can exist without helpdesk_ticket_id."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertIsNotNone(sale_order)
        self.assertFalse(sale_order.helpdesk_ticket_id)
    
    def test_change_helpdesk_ticket_reference(self):
        """Test changing helpdesk_ticket_id on a sale order."""
        ticket1 = self.env['helpdesk.ticket'].create({
            'name': 'Ticket 1',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        ticket2 = self.env['helpdesk.ticket'].create({
            'name': 'Ticket 2',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket1.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertEqual(sale_order.helpdesk_ticket_id, ticket1)
        self.assertEqual(ticket1.sale_order_count, 1)
        self.assertEqual(ticket2.sale_order_count, 0)
        
        # Change ticket reference
        sale_order.helpdesk_ticket_id = ticket2.id
        
        self.assertEqual(sale_order.helpdesk_ticket_id, ticket2)
        self.assertEqual(ticket1.sale_order_count, 0)
        self.assertEqual(ticket2.sale_order_count, 1)
    
    def test_clear_helpdesk_ticket_reference(self):
        """Test clearing helpdesk_ticket_id from sale order."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertEqual(ticket.sale_order_count, 1)
        
        # Clear ticket reference
        sale_order.helpdesk_ticket_id = False
        
        self.assertFalse(sale_order.helpdesk_ticket_id)
        self.assertEqual(ticket.sale_order_count, 0)


class TestSaleOrderSearchAndFilter(HelpdeskSaleTestCommon):
    """Test search and filtering operations."""

    def test_search_by_helpdesk_ticket(self):
        """Test searching sales orders by helpdesk ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create SOs linked and not linked to ticket
        so_linked1 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        so_linked2 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        so_unlinked = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        # Search for SOs linked to ticket
        found = self.env['sale.order'].search([
            ('helpdesk_ticket_id', '=', ticket.id)
        ])
        
        self.assertEqual(len(found), 2)
        self.assertIn(so_linked1, found)
        self.assertIn(so_linked2, found)
        self.assertNotIn(so_unlinked, found)
    
    def test_search_with_helpdesk_ticket(self):
        """Test finding SOs that have helpdesk ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        so_with_ticket = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        so_without_ticket = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        # Search for SOs with tickets
        found = self.env['sale.order'].search([
            ('helpdesk_ticket_id', '!=', False)
        ])
        
        self.assertIn(so_with_ticket, found)
        self.assertNotIn(so_without_ticket, found)


class TestSaleOrderDataIntegrity(HelpdeskSaleTestCommon):
    """Test data integrity and cascading behavior."""

    def test_delete_sale_order_updates_count(self):
        """Test deleting SO updates ticket count."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
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
                    'product_qty': 1,
                    'price_unit': 100.0,
                })]
            })
            sale_orders.append(so)
        
        self.assertEqual(ticket.sale_order_count, 3)
        
        # Delete one
        sale_orders[0].unlink()
        self.assertEqual(ticket.sale_order_count, 2)
        
        # Delete another
        sale_orders[1].unlink()
        self.assertEqual(ticket.sale_order_count, 1)
        
        # Delete last
        sale_orders[2].unlink()
        self.assertEqual(ticket.sale_order_count, 0)
    
    def test_delete_ticket_orphans_sales_orders(self):
        """Test deleting ticket leaves SOs with null reference."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        so1 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        so2 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        self.assertEqual(so1.helpdesk_ticket_id, ticket)
        self.assertEqual(so2.helpdesk_ticket_id, ticket)
        
        # Delete ticket
        ticket.unlink()
        
        # SOs should still exist but with no ticket reference
        self.assertTrue(so1.exists())
        self.assertTrue(so2.exists())
        self.assertFalse(so1.helpdesk_ticket_id)
        self.assertFalse(so2.helpdesk_ticket_id)


class TestSaleOrderStateFiltering(HelpdeskSaleTestCommon):
    """Test sale order state filtering in domains."""

    def test_only_confirmed_orders_in_domain(self):
        """Test that only 'sale' and 'done' state orders are available."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create draft SO
        draft_so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        
        # Create confirmed SO
        confirmed_so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        confirmed_so.action_confirm()
        
        # Trigger onchange to get domain
        ticket.customer_id = self.customer.id
        result = ticket._onchange_customer_id_sale()
        
        domain = result.get('domain', {}).get('sale_order_id', [])
        
        # Domain should check for 'sale' or 'done' state
        state_condition = [d for d in domain if isinstance(d, tuple) and d[0] == 'state']
        self.assertTrue(len(state_condition) > 0)
        self.assertIn('sale', str(state_condition))
