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
class TestHelpdeskLivechat(TransactionCase):
    """Test suite for the Cyllo Helpdesk Livechat integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a visitor partner
        cls.visitor_partner = cls.env['res.partner'].create({
            'name': 'Livechat Visitor',
            'email': 'visitor@test.com',
            'phone': '5551234567',
        })

        # Create helpdesk team with livechat ticket creation enabled
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Livechat Support Team',
            'use_livechat_ticket_creation': True,
        })

        # Create a livechat channel
        cls.livechat_channel = cls.env['im_livechat.channel'].create({
            'name': 'Website Support',
            'user_ids': [(6, 0, cls.env.user.ids)],
        })

        # Create a discuss channel simulating a livechat session
        cls.channel = cls.env['discuss.channel'].create({
            'name': 'Livechat Session',
            'channel_type': 'livechat',
            'livechat_operator_id': cls.env.user.partner_id.id,
            'livechat_channel_id': cls.livechat_channel.id,
            'channel_member_ids': [
                (0, 0, {'partner_id': cls.env.user.partner_id.id}),
                (0, 0, {'partner_id': cls.visitor_partner.id}),
            ],
        })

    def test_execute_command_ticket_creates_ticket(self):
        """Test that /ticket command creates a helpdesk ticket with correct data."""
        ticket_id = self.channel.execute_command_ticket(body="/ticket Printer not working")
        ticket = self.env['helpdesk.ticket'].browse(ticket_id)

        self.assertTrue(ticket.exists())
        self.assertEqual(ticket.name, 'Printer not working')
        self.assertEqual(ticket.customer_id, self.visitor_partner)
        self.assertEqual(ticket.email, self.visitor_partner.email)
        self.assertEqual(ticket.phone, self.visitor_partner.phone)
        self.assertEqual(ticket.source, 'livechat')

    def test_execute_command_ticket_no_name_returns_false(self):
        """Test that /ticket with no ticket name sends a usage hint and returns False."""
        result = self.channel.execute_command_ticket(body="/ticket")
        self.assertFalse(result)

        result = self.channel.execute_command_ticket(body="")
        self.assertFalse(result)

    def test_execute_command_ticket_uses_livechat_team(self):
        """Test that the ticket is assigned to the team with use_livechat_ticket_creation enabled."""
        ticket_id = self.channel.execute_command_ticket(body="/ticket Network issue")
        ticket = self.env['helpdesk.ticket'].browse(ticket_id)

        self.assertEqual(ticket.team_id, self.team,
                         "Ticket should be assigned to the team with livechat ticket creation enabled.")

    def test_execute_command_ticket_fallback_team(self):
        """Test fallback to any team when no team has use_livechat_ticket_creation enabled."""
        self.team.use_livechat_ticket_creation = False
        ticket_id = self.channel.execute_command_ticket(body="/ticket Fallback test")
        ticket = self.env['helpdesk.ticket'].browse(ticket_id)

        self.assertTrue(ticket.exists())
        self.assertTrue(ticket.team_id, "A fallback team should be assigned.")

    def test_get_ticket_customer_partner(self):
        """Test that _get_ticket_customer_partner returns the visitor partner (not the operator)."""
        customer = self.channel._get_ticket_customer_partner()
        self.assertEqual(customer, self.visitor_partner,
                         "Should return the visitor partner, not the operator.")

    def test_get_ticket_description(self):
        """Test that _get_ticket_description builds a transcript from channel messages."""
        self.channel.message_post(
            body="<p>Hello, I need help with my order.</p>",
            author_id=self.visitor_partner.id,
        )
        description = self.channel._get_ticket_description()
        self.assertIn('help with my order', description)

    def test_get_livechat_ticket_team(self):
        """Test that _get_livechat_ticket_team returns the configured team."""
        result = self.channel._get_livechat_ticket_team()
        self.assertEqual(result, self.team)

        # Disable the flag and verify no team is returned
        self.team.use_livechat_ticket_creation = False
        result = self.channel._get_livechat_ticket_team()
        self.assertFalse(result)

    def test_help_message_contains_ticket_command(self):
        """Test that the help message extra text mentions /ticket."""
        msg = self.channel._execute_command_help_message_extra()
        self.assertIn('/ticket', msg)

    def test_execute_command_ticket_no_team_returns_false(self):
        """Test that /ticket returns False when no helpdesk team exists at all."""
        # Remove all tickets first (they reference teams via FK), then teams
        self.env['helpdesk.ticket'].sudo().search([]).unlink()
        self.env['helpdesk.team'].sudo().search([]).unlink()
        result = self.channel.execute_command_ticket(body="/ticket No team test")
        self.assertFalse(result)
