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

        # Teams are needed for the team/use_crm-scoped tests below
        cls.team_crm = cls.env['helpdesk.team'].create({
            'name': 'CRM Team',
            'use_crm': True,
        })
        cls.team_no_crm = cls.env['helpdesk.team'].create({
            'name': 'No CRM Team',
            'use_crm': False,
        })

        # Create a base helpdesk ticket
        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'Test Ticket #1',
            'customer_id': cls.partner.id,
            'team_id': cls.team_crm.id,
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
            'team_id': self.team_crm.id,
        })
        self.env['crm.lead'].create({
            'name': 'Lead for Other Ticket',
            'helpdesk_ticket_id': other_ticket.id,
        })
        self.assertEqual(self.ticket.crm_lead_count, 0)

    # ─────────────────────────────────────────────
    # Field wiring / compute metadata
    # ─────────────────────────────────────────────

    def test_crm_lead_ids_field_wiring(self):
        """crm_lead_ids must target crm.lead through helpdesk_ticket_id."""
        field = self.env['helpdesk.ticket']._fields['crm_lead_ids']
        self.assertEqual(field.comodel_name, 'crm.lead')
        self.assertEqual(field.inverse_name, 'helpdesk_ticket_id')

    def test_crm_lead_ids_field_label(self):
        """The One2many field label should be 'CRM Leads'."""
        field = self.env['helpdesk.ticket']._fields['crm_lead_ids']
        self.assertEqual(field.string, 'CRM Leads')

    def test_crm_lead_count_is_realtime_compute(self):
        """crm_lead_count should be non-stored and computed on the fly."""
        field = self.env['helpdesk.ticket']._fields['crm_lead_count']
        self.assertFalse(field.store, "crm_lead_count must be a realtime field.")
        self.assertEqual(field.compute, '_compute_crm_lead_count')

    # ─────────────────────────────────────────────
    # Computed count — batch reads & One2many side
    # ─────────────────────────────────────────────

    def test_lead_count_batch_computed_across_tickets(self):
        """The compute loop must keep per-ticket values in a batch read."""
        self.env['crm.lead'].create({
            'name': 'Lead A', 'helpdesk_ticket_id': self.ticket.id,
        })
        other = self.env['helpdesk.ticket'].create({
            'name': 'Batch Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team_crm.id,
        })
        self.env['crm.lead'].create({
            'name': 'Lead B', 'helpdesk_ticket_id': other.id,
        })
        counts = {t.id: t.crm_lead_count for t in self.ticket | other}
        self.assertEqual(counts[self.ticket.id], 1)
        self.assertEqual(counts[other.id], 1)

    def test_lead_created_via_one2many_command_bumps_count(self):
        """Creating a lead through the One2many side must update the count."""
        self.assertEqual(self.ticket.crm_lead_count, 0)
        self.ticket.write({
            'crm_lead_ids': [(0, 0, {'name': 'O2M-created Lead'})],
        })
        self.assertEqual(self.ticket.crm_lead_count, 1)

    # ─────────────────────────────────────────────
    # sudo() compute: user without CRM access
    # ─────────────────────────────────────────────

    def test_lead_count_readable_by_user_without_crm_access(self):
        """A helpdesk user with no sales groups can still see crm_lead_count.

        _compute_crm_lead_count uses sudo(), so the stat button keeps
        working for users forbidden to read crm.lead directly.
        """
        user = self.env['res.users'].create({
            'name': 'Helpdesk Only User',
            'login': 'hd_only_count_user',  # unique login: avoid demo clashes
            'email': 'hd_only@test.com',
            'groups_id': [(6, 0, [
                self.env.ref('cyllo_helpdesk.cyllo_helpdesk_user').id,
            ])],
        })
        # Ticket visibility for this group is member-only (ir.rule in
        # the base module), so the user must belong to the team.
        self.team_crm.write({'member_ids': [(4, user.id)]})
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Auth Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team_crm.id,
        })
        lead = self.env['crm.lead'].create({
            'name': 'Lead for restricted user',
            'helpdesk_ticket_id': ticket.id,
        })

        # Sanity: without CRM groups the user gets an AccessError ...
        with self.assertRaises(AccessError):
            self.env['crm.lead'].with_user(user).browse(lead.id).name

        # ... yet the computed count still works thanks to sudo().
        self.assertEqual(
            ticket.with_user(user).crm_lead_count, 1,
            "crm_lead_count must remain readable without CRM access.",
        )

    # ─────────────────────────────────────────────
    # Team use_crm toggle (UI-only gate)
    # ─────────────────────────────────────────────

    def test_lead_linking_ignores_use_crm_flag(self):
        """use_crm gates the UI buttons only; the relation must still work."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'No-CRM-team Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team_no_crm.id,
        })
        lead = self.env['crm.lead'].create({
            'name': 'Lead on non-CRM team ticket',
            'helpdesk_ticket_id': ticket.id,
        })
        self.assertIn(lead, ticket.crm_lead_ids)
        self.assertEqual(ticket.crm_lead_count, 1)

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

    def test_action_view_crm_leads_res_model_and_xmlid(self):
        """The stat-button action must resolve to the CRM pipeline action."""
        action = self.ticket.action_view_crm_leads()
        self.assertEqual(action['res_model'], 'crm.lead')
        self.assertEqual(
            action['id'],
            self.env.ref('crm.crm_lead_action_pipeline').id,
        )

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

    def test_action_create_crm_lead_res_model_and_target(self):
        """The action must open crm.lead in the current window."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(action['res_model'], 'crm.lead')
        self.assertEqual(action['target'], 'current')

    def test_action_create_crm_lead_form_view_xmlid(self):
        """The action must open the standard CRM lead form view."""
        action = self.ticket.action_create_crm_lead()
        self.assertEqual(action['views'], [
            (self.env.ref('crm.crm_lead_view_form').id, 'form'),
        ])


    # ─────────────────────────────────────────────
    # Action context defaults applied at ORM level
    # ─────────────────────────────────────────────

    def test_crm_lead_create_with_action_context_applies_defaults(self):
        """Creating a lead with the action context pre-fills the defaults."""
        action = self.ticket.action_create_crm_lead()
        lead = self.env['crm.lead'].with_context(
            **action['context']).create({})
        self.assertEqual(lead.name, self.ticket.name)
        self.assertEqual(lead.partner_id, self.partner)
        self.assertEqual(lead.helpdesk_ticket_id, self.ticket)
        self.assertEqual(self.ticket.crm_lead_count, 1)

    # ─────────────────────────────────────────────
    # ensure_one guard — exact exception type
    # ─────────────────────────────────────────────

    def test_actions_raise_valueerror_on_multi_recordsets(self):
        """ensure_one raises ValueError (not AccessError) on multi sets."""
        second_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Fourth Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team_crm.id,
        })
        multi = self.ticket | second_ticket
        with self.assertRaises(ValueError):
            multi.action_view_crm_leads()
        with self.assertRaises(ValueError):
            multi.action_create_crm_lead()