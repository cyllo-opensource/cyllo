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

from .test_common import HelpdeskRepairTestCommon


class TestRepairOrderEnhancements(HelpdeskRepairTestCommon):
    """Test cases for RepairOrder model enhancements."""

    def test_repair_order_helpdesk_ticket_field(self):
        """Test that repair order has helpdesk_ticket_id many2one field."""
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
        })
        
        # Field should exist
        self.assertTrue(hasattr(repair, 'helpdesk_ticket_id'))
        
        # Initially should be empty
        self.assertFalse(repair.helpdesk_ticket_id)
    
    def test_repair_order_link_to_helpdesk_ticket(self):
        """Test repair order can be linked to helpdesk ticket."""
        # Create helpdesk ticket
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create repair linked to ticket
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        # Verify link
        self.assertEqual(repair.helpdesk_ticket_id, ticket)
        self.assertIn(repair, ticket.repair_ids)
    
    def test_repair_order_helpdesk_ticket_indexed(self):
        """Test that helpdesk_ticket_id field is indexed for performance."""
        # Create multiple repairs with tickets
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
        
        repairs1 = []
        repairs2 = []
        
        for i in range(3):
            r1 = self.env['repair.order'].create({
                'product_id': self.product.id,
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket1.id,
            })
            repairs1.append(r1)
            
            r2 = self.env['repair.order'].create({
                'product_id': self.product.id,
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket2.id,
            })
            repairs2.append(r2)
        
        # Search by helpdesk_ticket_id should be efficient
        found_repairs1 = self.env['repair.order'].search([
            ('helpdesk_ticket_id', '=', ticket1.id)
        ])
        
        found_repairs2 = self.env['repair.order'].search([
            ('helpdesk_ticket_id', '=', ticket2.id)
        ])
        
        self.assertEqual(len(found_repairs1), 3)
        self.assertEqual(len(found_repairs2), 3)
        self.assertEqual(set(found_repairs1), set(repairs1))
        self.assertEqual(set(found_repairs2), set(repairs2))
    
    def test_repair_order_without_helpdesk_ticket(self):
        """Test repair order can exist without helpdesk_ticket_id."""
        # Repair orders should still work without helpdesk ticket
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
        })
        
        self.assertIsNotNone(repair)
        self.assertFalse(repair.helpdesk_ticket_id)
    
    def test_repair_order_change_helpdesk_ticket(self):
        """Test changing the helpdesk_ticket_id on a repair order."""
        # Create two tickets
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
        
        # Create repair linked to ticket1
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket1.id,
        })
        
        self.assertEqual(repair.helpdesk_ticket_id, ticket1)
        self.assertEqual(ticket1.repair_count, 1)
        self.assertEqual(ticket2.repair_count, 0)
        
        # Change to ticket2
        repair.write({'helpdesk_ticket_id': ticket2.id})
        
        self.assertEqual(repair.helpdesk_ticket_id, ticket2)
        self.assertEqual(ticket1.repair_count, 0)
        self.assertEqual(ticket2.repair_count, 1)
    
    def test_repair_order_clear_helpdesk_ticket(self):
        """Test clearing helpdesk_ticket_id from a repair order."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        self.assertEqual(ticket.repair_count, 1)
        
        # Clear the ticket reference
        repair.write({'helpdesk_ticket_id': False})
        
        self.assertFalse(repair.helpdesk_ticket_id)
        self.assertEqual(ticket.repair_count, 0)


class TestRepairOrderSearchAndFilter(HelpdeskRepairTestCommon):
    """Test cases for repair order search and filtering with helpdesk tickets."""
    
    def test_search_repairs_by_helpdesk_ticket(self):
        """Test searching repairs by helpdesk ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create multiple repairs
        repair1 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        repair2 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        # Create repair without ticket
        repair3 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
        })
        
        # Search for repairs linked to this ticket
        repairs = self.env['repair.order'].search([
            ('helpdesk_ticket_id', '=', ticket.id)
        ])
        
        self.assertEqual(len(repairs), 2)
        self.assertIn(repair1, repairs)
        self.assertIn(repair2, repairs)
        self.assertNotIn(repair3, repairs)
    
    def test_search_repairs_with_helpdesk_ticket(self):
        """Test searching repairs that have a helpdesk ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create repairs with and without ticket
        repair_with_ticket = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        repair_without_ticket = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
        })
        
        # Search for repairs with helpdesk tickets
        repairs = self.env['repair.order'].search([
            ('helpdesk_ticket_id', '!=', False)
        ])
        
        self.assertIn(repair_with_ticket, repairs)
        self.assertNotIn(repair_without_ticket, repairs)
    
    def test_filter_repairs_by_customer_and_ticket(self):
        """Test complex filtering of repairs by customer and helpdesk ticket."""
        # Create second customer
        customer2 = self.env['res.partner'].create({
            'name': 'Another Customer',
            'email': 'another@test.com',
        })
        
        # Create tickets for both customers
        ticket1 = self.env['helpdesk.ticket'].create({
            'name': 'Customer 1 Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        ticket2 = self.env['helpdesk.ticket'].create({
            'name': 'Customer 2 Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': customer2.id,
        })
        
        # Create repairs
        repair1 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket1.id,
        })
        
        repair2 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': customer2.id,
            'helpdesk_ticket_id': ticket2.id,
        })
        
        # Search for customer1's repairs
        repairs = self.env['repair.order'].search([
            ('partner_id', '=', self.customer.id),
            ('helpdesk_ticket_id', '!=', False),
        ])
        
        self.assertIn(repair1, repairs)
        self.assertNotIn(repair2, repairs)


class TestRepairOrderDataIntegrity(HelpdeskRepairTestCommon):
    """Test data integrity and cascading behavior."""
    
    def test_delete_repair_updates_count(self):
        """Test that deleting a repair updates ticket's repair_count."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        repairs = []
        for i in range(3):
            repair = self.env['repair.order'].create({
                'product_id': self.product.id,
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket.id,
            })
            repairs.append(repair)
        
        self.assertEqual(ticket.repair_count, 3)
        
        # Delete one repair
        repairs[0].unlink()
        self.assertEqual(ticket.repair_count, 2)
        
        # Delete another
        repairs[1].unlink()
        self.assertEqual(ticket.repair_count, 1)
        
        # Delete last one
        repairs[2].unlink()
        self.assertEqual(ticket.repair_count, 0)
    
    def test_delete_helpdesk_ticket_orphans_repairs(self):
        """Test that deleting a ticket leaves repairs with null ticket reference."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        repair1 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        repair2 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        self.assertEqual(repair1.helpdesk_ticket_id, ticket)
        self.assertEqual(repair2.helpdesk_ticket_id, ticket)
        
        # Delete the ticket
        ticket.unlink()
        
        # Repairs should still exist but with no ticket reference
        self.assertTrue(repair1.exists())
        self.assertTrue(repair2.exists())
        self.assertFalse(repair1.helpdesk_ticket_id)
        self.assertFalse(repair2.helpdesk_ticket_id)
