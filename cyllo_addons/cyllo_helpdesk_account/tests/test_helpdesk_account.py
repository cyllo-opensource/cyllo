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
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestHelpdeskAccount(TransactionCase):
    """Test suite for the Cyllo Helpdesk Account integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Find a sale journal
        cls.journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', cls.env.company.id)
        ], limit=1)

        # Create a commercial partner (parent)
        cls.parent_partner = cls.env['res.partner'].create({
            'name': 'Parent Company Partner',
            'is_company': True,
        })

        # Create a child partner (customer)
        cls.customer = cls.env['res.partner'].create({
            'name': 'Child Contact Partner',
            'parent_id': cls.parent_partner.id,
        })

        # Create a Helpdesk Team
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Billing Support Team',
        })

        # Create an invoice for the child partner
        cls.invoice_child = cls.env['account.move'].create({
            'partner_id': cls.customer.id,
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting Fee Child',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        cls.invoice_child.action_post()

        # Create an invoice for the parent partner
        cls.invoice_parent = cls.env['account.move'].create({
            'partner_id': cls.parent_partner.id,
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting Fee Parent',
                'quantity': 1,
                'price_unit': 200.0,
            })],
        })
        cls.invoice_parent.action_post()

    def test_invoice_fields_and_computes(self):
        """Test the computation of customer invoice count and ticket invoice relations."""
        # Create a helpdesk ticket for the child partner
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Billing Discrepancy Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
            'invoice_id': self.invoice_child.id,
        })

        # Check compute field customer_invoice_count (should count both parent and child invoices)
        ticket._compute_customer_invoice_count()
        self.assertEqual(ticket.customer_invoice_count, 2, 
                         "The invoice count should cover the commercial partner hierarchy (parent & child).")

        # Test line items domain / association
        ticket.invoice_line_ids = ticket.invoice_id.invoice_line_ids
        self.assertTrue(ticket.invoice_line_ids)
        self.assertEqual(ticket.invoice_line_ids[0].name, 'Consulting Fee Child')

    def test_action_view_customer_invoices(self):
        """Test the action to view customer invoices."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Invoice Query Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        action = ticket.action_view_customer_invoices()
        self.assertEqual(action.get('view_mode'), 'tree')
        self.assertEqual(action.get('views')[0][1], 'tree')
        
        # Verify the domain limits to child/parent commercial partner hierarchy
        expected_domain = [
            ('partner_id', 'child_of', self.customer.commercial_partner_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ]
        self.assertEqual(action.get('domain'), expected_domain)

    def test_action_create_refund(self):
        """Test the action to create a refund from the ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Refund Request Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        # Should raise UserError if no invoice_id is set
        with self.assertRaises(UserError):
            ticket.action_create_refund()

        # Set the invoice_id
        ticket.invoice_id = self.invoice_child.id
        action = ticket.action_create_refund()

        # Check that the reversal wizard action is returned
        self.assertEqual(action.get('context', {}).get('active_model'), 'account.move')
        self.assertEqual(action.get('context', {}).get('active_ids'), [self.invoice_child.id])

    def test_refund_ids_and_count(self):
        """Test that refunds linked to the ticket are properly computed and returned."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Refund Link Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        # Create a refund / credit note linked to this ticket
        refund = self.env['account.move'].create({
            'partner_id': self.customer.id,
            'move_type': 'out_refund',
            'journal_id': self.journal.id,
            'helpdesk_ticket_id': ticket.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Refund for consulting fee',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

        ticket._compute_refund_count()
        self.assertEqual(ticket.refund_count, 1)
        self.assertIn(refund, ticket.refund_ids)
