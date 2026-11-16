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
class TestHelpdeskAccount(TransactionCase):
    """Test suite for the Cyllo Helpdesk Account integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Find a sale journal (used for refunds / credit notes)
        cls.journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', cls.env.company.id)
        ], limit=1)

        # Create a Helpdesk Team
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Billing Support Team',
        })

        # Create a customer partner
        cls.customer = cls.env['res.partner'].create({
            'name': 'Child Contact Partner',
        })

    def test_invoice_does_not_count_as_refund(self):
        """A regular customer invoice linked to the ticket must NOT be
        counted by the refund One2many domain."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Billing Discrepancy Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        self.env['account.move'].create({
            'partner_id': self.customer.id,
            'move_type': 'out_invoice',
            'journal_id': self.journal.id,
            'helpdesk_ticket_id': ticket.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting Fee',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })

        # Only out_refund moves belong to refund_ids / refund_count
        self.assertEqual(ticket.refund_count, 0)
        self.assertFalse(ticket.refund_ids)

    def test_action_view_refunds(self):
        """Test the refunds stat-button action."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Refund Query Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        action = ticket.action_view_refunds()
        self.assertEqual(action.get('res_model'), 'account.move')
        self.assertEqual(action.get('target'), 'current')
        self.assertEqual(action.get('domain'), [
            ('helpdesk_ticket_id', '=', ticket.id),
            ('move_type', '=', 'out_refund'),
        ])

    def test_action_create_refund(self):
        """Test the action to open the refund wizard from the ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Refund Request Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        action = ticket.action_create_refund()

        # A wizard action is returned (no ticket-side invoice lock anymore)
        self.assertEqual(action.get('res_model'), 'helpdesk.refund.wizard')
        self.assertEqual(action.get('target'), 'new')
        context = action.get('context', {})
        self.assertEqual(context.get('default_ticket_id'), ticket.id)
        self.assertEqual(context.get('default_customer_id'), self.customer.id)

    def test_refund_ids_and_count(self):
        """Test that refunds linked to the ticket are properly computed."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Refund Link Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        # Create a credit note linked to this ticket
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

    def test_refund_wizard_creates_credit_note(self):
        """Test the end-to-end wizard flow: confirm without invoice
        creates a standalone credit note linked to the ticket."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Wizard Refund Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        })

        wizard = self.env['helpdesk.refund.wizard'].with_context(
            default_ticket_id=ticket.id,
            default_customer_id=self.customer.id,
        ).create({
            'journal_id': self.journal.id,
        })

        action = wizard.action_confirm()
        credit_note = self.env['account.move'].browse(action['res_id'])

        self.assertEqual(credit_note.move_type, 'out_refund')
        self.assertEqual(credit_note.helpdesk_ticket_id, ticket)