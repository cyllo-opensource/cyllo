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
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestHelpDeskTicketCRM(TransactionCase):
    """Tests for HelpDeskTicket CRM integration in cyllo_helpdesk_crm."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a partner/customer
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
        })

        # Create a base helpdesk ticket
        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'Test Ticket #1',
            'customer_id': cls.partner.id,
        })

    # ─────────────────────────────────────────────
    # Field / computed-field tests
    # ─────────────────────────────────────────────

    def test_crm_lead_ids_field_exists(self):
        """crm_lead_ids One2many field should exist on helpdesk.ticket."""
        self.assertIn('crm_lead_ids', self.ticket._fields)

    def test_crm_lead_count_default_zero(self):
        """A new ticket with no leads should have crm_lead_count == 0."""
        self.assertEqual(self.ticket.crm_lead_count, 0)

    def test_crm_lead_count_increments_when_lead_linked(self):
        """crm_lead_count should reflect the number of linked CRM leads."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead from Ticket',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertEqual(self.ticket.crm_lead_count, 1)

        lead2 = self.env['crm.lead'].create({
            'name': 'Second Lead from Ticket',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertEqual(self.ticket.crm_lead_count, 2)

        # Clean up
        lead.unlink()
        lead2.unlink()

    def test_crm_lead_count_decrements_when_lead_removed(self):
        """crm_lead_count should decrease when a lead is unlinked."""
        lead = self.env['crm.lead'].create({
            'name': 'Temporary Lead',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertEqual(self.ticket.crm_lead_count, 1)
        lead.unlink()
        self.assertEqual(self.ticket.crm_lead_count, 0)

    def test_crm_lead_count_isolated_per_ticket(self):
        """Leads on other tickets must not affect this ticket's count."""
        other_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Other Ticket',
            'customer_id': self.partner.id,
        })
        self.env['crm.lead'].create({
            'name': 'Lead for Other Ticket',
            'helpdesk_ticket_id': other_ticket.id,
        })
        self.assertEqual(self.ticket.crm_lead_count, 0)

    # ─────────────────────────────────────────────
    # action_view_crm_leads tests
    # ─────────────────────────────────────────────

    def test_action_view_crm_leads_returns_action(self):
        """action_view_crm_leads should return a dict (ir.actions)."""
        action = self.ticket.action_view_crm_leads()
        self.assertIsInstance(action, dict)

    def test_action_view_crm_leads_domain_filters_by_ticket(self):
        """Action domain must restrict leads to the current ticket."""
        action = self.ticket.action_view_crm_leads()
        self.assertIn(('helpdesk_ticket_id', '=', self.ticket.id), action['domain'])

    def test_action_view_crm_leads_default_context(self):
        """Action context must pre-fill helpdesk_ticket_id."""
        action = self.ticket.action_view_crm_leads()
        self.assertEqual(
            action['context'].get('default_helpdesk_ticket_id'),
            self.ticket.id,
        )

    def test_action_view_crm_leads_view_mode(self):
        """Action view_mode should contain list and form."""
        action = self.ticket.action_view_crm_leads()
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])

    # ─────────────────────────────────────────────
    # action_create_crm_lead tests
    # ─────────────────────────────────────────────

    def test_action_create_crm_lead_returns_action(self):
        """action_create_crm_lead should return a dict."""
        action = self.ticket.action_create_crm_lead()
        self.assertIsInstance(action, dict)

    def test_action_create_crm_lead_default_name(self):
        """Default lead name should be taken from the ticket name."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(action['context'].get('default_name'), self.ticket.name)

    def test_action_create_crm_lead_default_partner(self):
        """Default partner_id should be the ticket's customer."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(
            action['context'].get('default_partner_id'),
            self.partner.id,
        )

    def test_action_create_crm_lead_default_ticket_id(self):
        """Context must pass the current ticket id to the new lead form."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(
            action['context'].get('default_helpdesk_ticket_id'),
            self.ticket.id,
        )

    def test_action_create_crm_lead_view_mode_is_form(self):
        """Create action must open a form view, not a list."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(action.get('view_mode'), 'form')

    def test_action_create_crm_lead_posts_chatter_message(self):
        """A chatter message should be posted when create-lead is triggered."""
        before = self.ticket.message_ids
        self.ticket.action_create_crm_lead()
        after = self.ticket.message_ids
        new_messages = after - before
        self.assertTrue(
            new_messages,
            "Expected at least one new chatter message after action_create_crm_lead.",
        )
        self.assertIn(
            'CRM Lead creation initiated',
            new_messages[0].body,
        )

    # ─────────────────────────────────────────────
    # ensure_one guard
    # ─────────────────────────────────────────────

    def test_action_view_crm_leads_requires_single_record(self):
        """action_view_crm_leads must raise if called on a multi-record set."""
        second_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Second Ticket',
            'customer_id': self.partner.id,
        })
        multi = self.ticket | second_ticket
        with self.assertRaises(Exception):
            multi.action_view_crm_leads()

    def test_action_create_crm_lead_requires_single_record(self):
        """action_create_crm_lead must raise if called on a multi-record set."""
        second_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Third Ticket',
            'customer_id': self.partner.id,
        })
        multi = self.ticket | second_ticket
        with self.assertRaises(Exception):
            multi.action_create_crm_lead()
