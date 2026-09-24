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
import unittest


class TestHelpDeskTicketFieldService(TransactionCase):
    """Tests for HelpDeskTicket field service integration in cyllo_helpdesk_field_service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.team = cls.env['helpdesk.team'].create({
            'name': 'FS Test Team',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'FS Test Customer',
            'email': 'fs_customer@test.com',
        })

        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'Field Service Test Ticket',
            'customer_id': cls.partner.id,
            'team_id': cls.team.id,
            'priority': '1',
        })

    # ─────────────────────────────────────────────
    # Field existence
    # ─────────────────────────────────────────────

    def test_field_service_request_ids_field_exists(self):
        """field_service_request_ids One2many field should exist on helpdesk.ticket."""
        self.assertIn('field_service_request_ids', self.ticket._fields)

    def test_field_service_request_count_field_exists(self):
        """field_service_request_count Integer field should exist on helpdesk.ticket."""
        self.assertIn('field_service_request_count', self.ticket._fields)

    # ─────────────────────────────────────────────
    # Computed field: field_service_request_count
    # ─────────────────────────────────────────────

    def test_request_count_default_zero(self):
        """A new ticket with no FSRs should have field_service_request_count == 0."""
        self.assertEqual(self.ticket.field_service_request_count, 0)

    def test_request_count_increments_on_link(self):
        """field_service_request_count should increase as FSRs are linked."""
        fsr1 = self.env['field.service.request'].create({
            'helpdesk_ticket_id': self.ticket.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(self.ticket.field_service_request_count, 1)

        fsr2 = self.env['field.service.request'].create({
            'helpdesk_ticket_id': self.ticket.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(self.ticket.field_service_request_count, 2)

        fsr1.unlink()
        fsr2.unlink()

    def test_request_count_decrements_on_unlink(self):
        """field_service_request_count should drop back to 0 when FSR is removed."""
        fsr = self.env['field.service.request'].create({
            'helpdesk_ticket_id': self.ticket.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(self.ticket.field_service_request_count, 1)
        fsr.unlink()
        self.assertEqual(self.ticket.field_service_request_count, 0)

    def test_request_count_isolated_per_ticket(self):
        """FSRs on another ticket must not affect this ticket's count."""
        other_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Other Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        self.env['field.service.request'].create({
            'helpdesk_ticket_id': other_ticket.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(self.ticket.field_service_request_count, 0)

    # ─────────────────────────────────────────────
    # Priority mapping in action_create_field_service_request
    # ─────────────────────────────────────────────

    def _get_create_action_priority(self, priority_val):
        """Helper: create a ticket with given priority and return the mapped value."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': f'Priority Test Ticket {priority_val}',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
            'priority': priority_val,
        })
        action = ticket.action_create_field_service_request()
        return action['context'].get('default_priority')

    def test_priority_map_0_maps_to_b(self):
        self.assertEqual(self._get_create_action_priority('0'), 'b')

    def test_priority_map_1_maps_to_a(self):
        self.assertEqual(self._get_create_action_priority('1'), 'a')

    def test_priority_map_2_maps_to_c(self):
        self.assertEqual(self._get_create_action_priority('2'), 'c')

    def test_priority_map_3_maps_to_d(self):
        self.assertEqual(self._get_create_action_priority('3'), 'd')

    def test_priority_map_unknown_defaults_to_a(self):
        """An unrecognised priority value should fall back to 'a'."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Unknown Priority Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        # Bypass ORM selection validation by patching the priority read
        from unittest.mock import patch
        with patch.object(type(ticket), 'priority', new_callable=lambda: property(lambda self: '9')):
            action = ticket.action_create_field_service_request()
        self.assertEqual(action['context'].get('default_priority'), 'a')

    # ─────────────────────────────────────────────
    # action_create_field_service_request
    # ─────────────────────────────────────────────

    def test_create_action_returns_dict(self):
        """action_create_field_service_request should return an action dict."""
        action = self.ticket.action_create_field_service_request()
        self.assertIsInstance(action, dict)

    def test_create_action_view_mode_is_form(self):
        """Create action must open a form view."""
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(action.get('view_mode'), 'form')

    def test_create_action_target_is_current(self):
        """Create action must open in the current window."""
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(action.get('target'), 'current')

    def test_create_action_context_default_partner(self):
        """default_partner_id in context must equal the ticket's customer."""
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(
            action['context'].get('default_partner_id'),
            self.partner.id,
        )

    def test_create_action_context_default_ticket_id(self):
        """default_helpdesk_ticket_id in context must equal the current ticket."""
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(
            action['context'].get('default_helpdesk_ticket_id'),
            self.ticket.id,
        )

    def test_create_action_context_default_description(self):
        """default_description in context must equal the ticket's description."""
        self.ticket.description = '<p>Issue details here</p>'
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(
            action['context'].get('default_description'),
            self.ticket.description,
        )

    def test_create_action_context_no_sale_order_when_absent(self):
        """default_sale_order_id must be False when ticket has no sale order."""
        action = self.ticket.action_create_field_service_request()
        self.assertFalse(action['context'].get('default_sale_order_id'))

    def test_create_action_context_sale_order_when_present(self):
        """default_sale_order_id must carry the sale order id when present."""
        if 'sale_order_id' not in self.ticket._fields:
            self.skipTest('sale_order_id field not available on helpdesk.ticket')
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.ticket.sale_order_id = sale_order
        action = self.ticket.action_create_field_service_request()
        self.assertEqual(
            action['context'].get('default_sale_order_id'),
            sale_order.id,
        )
        # Clean up
        self.ticket.sale_order_id = False

    def test_create_action_posts_chatter_message(self):
        """A chatter message should be posted when the create action is called."""
        before = self.ticket.message_ids
        self.ticket.action_create_field_service_request()
        after = self.ticket.message_ids
        new_msgs = after - before
        self.assertTrue(new_msgs, "Expected a chatter message after create action.")
        self.assertIn('Field Service Request creation initiated', new_msgs[0].body)

    def test_create_action_requires_single_record(self):
        """action_create_field_service_request must raise on a multi-record set."""
        second = self.env['helpdesk.ticket'].create({
            'name': 'Second Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        with self.assertRaises(Exception):
            (self.ticket | second).action_create_field_service_request()

    # ─────────────────────────────────────────────
    # action_view_field_service_requests
    # ─────────────────────────────────────────────

    def test_view_action_returns_dict(self):
        """action_view_field_service_requests should return an action dict."""
        action = self.ticket.action_view_field_service_requests()
        self.assertIsInstance(action, dict)

    def test_view_action_domain_filters_by_ticket(self):
        """Domain must restrict FSRs to the current ticket."""
        action = self.ticket.action_view_field_service_requests()
        self.assertIn(('helpdesk_ticket_id', '=', self.ticket.id), action['domain'])

    def test_view_action_view_mode(self):
        """View action must include both list and form modes."""
        action = self.ticket.action_view_field_service_requests()
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])

    def test_view_action_requires_single_record(self):
        """action_view_field_service_requests must raise on a multi-record set."""
        second = self.env['helpdesk.ticket'].create({
            'name': 'Third Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        with self.assertRaises(Exception):
            (self.ticket | second).action_view_field_service_requests()
