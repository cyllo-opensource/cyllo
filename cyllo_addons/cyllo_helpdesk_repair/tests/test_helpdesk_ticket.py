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


class TestHelpDeskTicketRepair(HelpdeskRepairTestCommon):
    """Test cases for HelpDeskTicket model enhancements."""

    def test_helpdesk_ticket_repair_ids_field(self):
        """Test that helpdesk ticket has repair_ids one2many field."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Field should exist and be empty initially
        self.assertEqual(len(ticket.repair_ids), 0)
        self.assertTrue(hasattr(ticket, 'repair_ids'))
    
    def test_helpdesk_ticket_repair_count_compute(self):
        """Test that repair_count is correctly computed."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Initially should be 0
        self.assertEqual(ticket.repair_count, 0)
        
        # Create repair order linked to ticket
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        # Count should update
        self.assertEqual(ticket.repair_count, 1)
        
        # Create another repair
        repair2 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        # Count should be 2
        self.assertEqual(ticket.repair_count, 2)
        
        # Delete one repair
        repair.unlink()
        
        # Count should be 1
        self.assertEqual(ticket.repair_count, 1)
    
    def test_action_create_repair_context_without_customer(self):
        """Test action_create_repair returns proper action without customer."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket No Customer',
            'team_id': self.helpdesk_team.id,
        })
        
        # Should raise error when ensure_one is called with no customer context
        # (UI handles visibility, but this tests the action itself)
        action = ticket.action_create_repair()
        
        # Action should return a dict with view configuration
        self.assertIsInstance(action, dict)
        self.assertIn('res_model', action)
        self.assertEqual(action['res_model'], 'repair.order')
    
    def test_action_create_repair_context_with_customer(self):
        """Test action_create_repair sets correct context with customer."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        action = ticket.action_create_repair()
        
        # Verify action structure
        self.assertEqual(action['res_model'], 'repair.order')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')
        
        # Verify context is set with customer and ticket info
        context = action.get('context', {})
        self.assertEqual(context['default_partner_id'], self.customer.id)
        self.assertEqual(context['default_helpdesk_ticket_id'], ticket.id)
    
    def test_action_create_repair_context_with_sale_order(self):
        """Test action_create_repair includes sale order in context."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket with SO',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
            'sale_order_id': self.sale_order.id,
        })
        
        action = ticket.action_create_repair()
        context = action.get('context', {})
        
        # Sale order should be included in context
        self.assertEqual(context['default_sale_order_id'], self.sale_order.id)
    
    def test_action_create_repair_context_with_warranty_status(self):
        """Test action_create_repair includes warranty status if available."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket Warranty',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Set warranty_status if the field exists on helpdesk.ticket
        if hasattr(ticket, 'warranty_status'):
            ticket.warranty_status = 'under_warranty'
        
        action = ticket.action_create_repair()
        context = action.get('context', {})
        
        # Default under_warranty should reflect the ticket's warranty status
        if hasattr(ticket, 'warranty_status'):
            self.assertEqual(
                context['default_under_warranty'],
                ticket.warranty_status == 'under_warranty'
            )
    
    def test_action_create_repair_posts_message(self):
        """Test that action_create_repair posts a message to the ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Get initial message count
        initial_messages = len(ticket.message_ids)
        
        # Call action
        action = ticket.action_create_repair()
        
        # Should have posted a message
        self.assertEqual(len(ticket.message_ids), initial_messages + 1)
        
        # Message should mention repair order creation
        latest_message = ticket.message_ids[0]
        self.assertIn('Repair Order creation initiated', latest_message.body)
    
    def test_action_view_repairs_filter(self):
        """Test action_view_repairs returns correct domain filter."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create repairs for this and another ticket
        repair1 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': ticket.id,
        })
        
        # Create another ticket with a repair
        other_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Other Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        repair2 = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.customer.id,
            'helpdesk_ticket_id': other_ticket.id,
        })
        
        # Get action from first ticket
        action = ticket.action_view_repairs()
        
        # Check domain filters only repairs for this ticket
        domain = action.get('domain', [])
        self.assertEqual(domain, [('helpdesk_ticket_id', '=', ticket.id)])
        
        # Verify view modes
        self.assertEqual(action['view_mode'], 'list,form')
    
    def test_action_view_repairs_empty_ticket(self):
        """Test action_view_repairs works with ticket having no repairs."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Empty Ticket',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Should still return valid action even with no repairs
        action = ticket.action_view_repairs()
        
        self.assertIsInstance(action, dict)
        self.assertIn('domain', action)
        self.assertEqual(action['domain'], [('helpdesk_ticket_id', '=', ticket.id)])


class TestHelpDeskTicketRepairIntegration(HelpdeskRepairTestCommon):
    """Integration tests for helpdesk-repair workflow."""
    
    def test_full_repair_workflow_from_ticket(self):
        """Test complete workflow: ticket -> create repair -> manage repair."""
        # Create ticket
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Defective Product',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
            'description': 'Product is not working',
        })
        
        self.assertEqual(ticket.repair_count, 0)
        
        # Simulate creating repair from action
        action = ticket.action_create_repair()
        context = action['context']
        
        # Create repair with context values
        repair = self.env['repair.order'].create({
            'product_id': context.get('default_product_id') or self.product.id,
            'partner_id': context['default_partner_id'],
            'helpdesk_ticket_id': context['default_helpdesk_ticket_id'],
        })
        
        # Verify ticket sees the repair
        self.assertEqual(ticket.repair_count, 1)
        self.assertIn(repair, ticket.repair_ids)
        
        # Verify repair links back to ticket
        self.assertEqual(repair.helpdesk_ticket_id, ticket)
    
    def test_multiple_repairs_per_ticket(self):
        """Test ticket can have multiple associated repair orders."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Multiple Issues',
            'team_id': self.helpdesk_team.id,
            'customer_id': self.customer.id,
        })
        
        # Create multiple repairs
        repairs = []
        for i in range(3):
            repair = self.env['repair.order'].create({
                'product_id': self.product.id,
                'partner_id': self.customer.id,
                'helpdesk_ticket_id': ticket.id,
            })
            repairs.append(repair)
        
        # Verify all linked to ticket
        self.assertEqual(ticket.repair_count, 3)
        self.assertEqual(set(ticket.repair_ids), set(repairs))
    
    def test_repair_unlink_updates_count(self):
        """Test that unlinking a repair updates the ticket's repair_count."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test',
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
        
        self.assertEqual(ticket.repair_count, 2)
        
        # Unlink one repair
        repair1.unlink()
        
        self.assertEqual(ticket.repair_count, 1)
        self.assertEqual(ticket.repair_ids, repair2)
