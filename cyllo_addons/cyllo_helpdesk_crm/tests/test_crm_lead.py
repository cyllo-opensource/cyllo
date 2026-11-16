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


class TestCrmLeadHelpdesk(TransactionCase):
    """Tests for the helpdesk_ticket_id extension on crm.lead."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'CRM Test Partner',
            'email': 'crm_partner@test.com',
        })

        # Team is required on tickets (team_id is NOT NULL on helpdesk.ticket)
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'CRM Integration Team',
        })

        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'CRM Integration Ticket',
            'customer_id': cls.partner.id,
            'team_id': cls.team.id,
        })
    # ─────────────────────────────────────────────
    # Field existence & defaults
    # ─────────────────────────────────────────────

    def test_helpdesk_ticket_id_field_exists(self):
        """helpdesk_ticket_id Many2one field should exist on crm.lead."""
        lead = self.env['crm.lead'].create({'name': 'Test Lead'})
        self.assertIn('helpdesk_ticket_id', lead._fields)

    def test_helpdesk_ticket_id_default_is_empty(self):
        """A lead created without a ticket should have no helpdesk_ticket_id."""
        lead = self.env['crm.lead'].create({'name': 'Standalone Lead'})
        self.assertFalse(lead.helpdesk_ticket_id)

    # ─────────────────────────────────────────────
    # Linking / unlinking
    # ─────────────────────────────────────────────

    def test_lead_can_be_linked_to_ticket(self):
        """A lead should be linkable to a helpdesk ticket."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead linked to Ticket',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertEqual(lead.helpdesk_ticket_id, self.ticket)

    def test_lead_linked_appears_in_ticket_crm_lead_ids(self):
        """A lead linked via helpdesk_ticket_id should appear on ticket.crm_lead_ids."""
        lead = self.env['crm.lead'].create({
            'name': 'Reverse Relation Lead',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertIn(lead, self.ticket.crm_lead_ids)

    def test_multiple_leads_can_link_to_same_ticket(self):
        """Multiple leads may reference the same ticket (One2many relationship)."""
        lead1 = self.env['crm.lead'].create({
            'name': 'Lead A',
            'helpdesk_ticket_id': self.ticket.id,
        })
        lead2 = self.env['crm.lead'].create({
            'name': 'Lead B',
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertIn(lead1, self.ticket.crm_lead_ids)
        self.assertIn(lead2, self.ticket.crm_lead_ids)
        self.assertEqual(self.ticket.crm_lead_count, 2)

    def test_helpdesk_ticket_id_can_be_cleared(self):
        """helpdesk_ticket_id should be settable to False (unlink from ticket)."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead to be unlinked',
            'helpdesk_ticket_id': self.ticket.id,
        })
        lead.helpdesk_ticket_id = False
        self.assertFalse(lead.helpdesk_ticket_id)
        self.assertNotIn(lead, self.ticket.crm_lead_ids)

    def test_lead_ticket_link_survives_write(self):
        """Writing unrelated fields must not break the ticket link."""
        lead = self.env['crm.lead'].create({
            'name': 'Persistent Lead',
            'helpdesk_ticket_id': self.ticket.id,
        })
        lead.write({'name': 'Persistent Lead - Updated'})
        self.assertEqual(lead.helpdesk_ticket_id, self.ticket)

    # ─────────────────────────────────────────────
    # Field metadata
    # ─────────────────────────────────────────────

    def test_helpdesk_ticket_id_is_indexed(self):
        """helpdesk_ticket_id should be indexed for performance."""
        field = self.env['crm.lead']._fields['helpdesk_ticket_id']
        self.assertTrue(
            getattr(field, 'index', False),
            "helpdesk_ticket_id should have index=True.",
        )

    def test_helpdesk_ticket_id_comodel(self):
        """helpdesk_ticket_id must reference helpdesk.ticket."""
        field = self.env['crm.lead']._fields['helpdesk_ticket_id']
        self.assertEqual(field.comodel_name, 'helpdesk.ticket')

    def test_helpdesk_ticket_id_string_label(self):
        """The field's string label should be 'Helpdesk Ticket'."""
        field = self.env['crm.lead']._fields['helpdesk_ticket_id']
        self.assertEqual(field.string, 'Helpdesk Ticket')

    # ─────────────────────────────────────────────
    # Deletion / cascade behaviour
    # ─────────────────────────────────────────────

    def test_lead_deletion_does_not_delete_ticket(self):
        """Deleting a CRM lead must not cascade to the linked ticket."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead to delete',
            'helpdesk_ticket_id': self.ticket.id,
        })
        lead_ticket_id = self.ticket.id
        lead.unlink()
        ticket_still_exists = self.env['helpdesk.ticket'].browse(lead_ticket_id).exists()
        self.assertTrue(ticket_still_exists, "Ticket should survive lead deletion.")

    # ─────────────────────────────────────────────
    # Reassignment between tickets
    # ─────────────────────────────────────────────

    def test_helpdesk_ticket_id_can_be_reassigned(self):
        """A lead can be moved from one ticket to another."""
        other_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Target Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        lead = self.env['crm.lead'].create({
            'name': 'Reassigned Lead',
            'helpdesk_ticket_id': self.ticket.id,
        })
        lead.helpdesk_ticket_id = other_ticket

        self.assertNotIn(lead, self.ticket.crm_lead_ids)
        self.assertEqual(self.ticket.crm_lead_count, 0)
        self.assertIn(lead, other_ticket.crm_lead_ids)
        self.assertEqual(other_ticket.crm_lead_count, 1)

    def test_lead_survives_ticket_deletion_with_link_cleared(self):
        """Deleting a ticket must keep the lead and clear its link
        (Many2one 'set null' default)."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Ticket to delete',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        lead = self.env['crm.lead'].create({
            'name': 'Orphan-to-be Lead',
            'helpdesk_ticket_id': ticket.id,
        })
        lead_id = lead.id
        ticket.unlink()

        lead = self.env['crm.lead'].browse(lead_id)
        self.assertTrue(lead.exists(), "Lead must survive ticket deletion.")
        self.assertFalse(
            lead.helpdesk_ticket_id,
            "Lead's ticket link must be cleared when the ticket is deleted.",
        )