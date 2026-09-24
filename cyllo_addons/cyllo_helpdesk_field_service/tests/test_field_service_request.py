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


class TestFieldServiceRequestHelpdesk(TransactionCase):
    """Tests for the helpdesk_ticket_id extension on field.service.request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.team = cls.env['helpdesk.team'].create({
            'name': 'FSR Test Team',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'FSR Helpdesk Partner',
            'email': 'fsr_partner@test.com',
        })

        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': 'FSR Integration Ticket',
            'customer_id': cls.partner.id,
            'team_id': cls.team.id,
        })

    # ─────────────────────────────────────────────
    # Field existence & metadata
    # ─────────────────────────────────────────────

    def test_helpdesk_ticket_id_field_exists(self):
        """helpdesk_ticket_id Many2one field should exist on field.service.request."""
        fsr = self.env['field.service.request'].create({'partner_id': self.partner.id})
        self.assertIn('helpdesk_ticket_id', fsr._fields)

    def test_helpdesk_ticket_id_comodel(self):
        """helpdesk_ticket_id must reference helpdesk.ticket."""
        field = self.env['field.service.request']._fields['helpdesk_ticket_id']
        self.assertEqual(field.comodel_name, 'helpdesk.ticket')

    def test_helpdesk_ticket_id_string_label(self):
        """Field string label should be 'Helpdesk Ticket'."""
        field = self.env['field.service.request']._fields['helpdesk_ticket_id']
        self.assertEqual(field.string, 'Helpdesk Ticket')

    def test_helpdesk_ticket_id_is_indexed(self):
        """helpdesk_ticket_id should have index=True for performance."""
        field = self.env['field.service.request']._fields['helpdesk_ticket_id']
        self.assertTrue(
            getattr(field, 'index', False),
            "helpdesk_ticket_id should have index=True.",
        )

    # ─────────────────────────────────────────────
    # Defaults
    # ─────────────────────────────────────────────

    def test_helpdesk_ticket_id_default_is_empty(self):
        """An FSR created without a ticket should have no helpdesk_ticket_id."""
        fsr = self.env['field.service.request'].create({'partner_id': self.partner.id})
        self.assertFalse(fsr.helpdesk_ticket_id)

    # ─────────────────────────────────────────────
    # Linking / unlinking
    # ─────────────────────────────────────────────

    def test_fsr_can_be_linked_to_ticket(self):
        """An FSR should be linkable to a helpdesk ticket at creation."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertEqual(fsr.helpdesk_ticket_id, self.ticket)

    def test_linked_fsr_appears_in_ticket_ids(self):
        """An FSR linked via helpdesk_ticket_id must appear in ticket.field_service_request_ids."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertIn(fsr, self.ticket.field_service_request_ids)

    def test_multiple_fsrs_can_link_to_same_ticket(self):
        """Multiple FSRs may reference the same ticket."""
        fsr1 = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        fsr2 = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        self.assertIn(fsr1, self.ticket.field_service_request_ids)
        self.assertIn(fsr2, self.ticket.field_service_request_ids)
        self.assertEqual(self.ticket.field_service_request_count, 2)

    def test_helpdesk_ticket_id_can_be_cleared(self):
        """helpdesk_ticket_id should be settable to False (unlink from ticket)."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        fsr.helpdesk_ticket_id = False
        self.assertFalse(fsr.helpdesk_ticket_id)
        self.assertNotIn(fsr, self.ticket.field_service_request_ids)

    def test_fsr_can_be_reassigned_to_different_ticket(self):
        """An FSR's ticket link should be updatable via write()."""
        other_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Reassignment Target Ticket',
            'customer_id': self.partner.id,
            'team_id': self.team.id,
        })
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        fsr.write({'helpdesk_ticket_id': other_ticket.id})
        self.assertEqual(fsr.helpdesk_ticket_id, other_ticket)
        self.assertNotIn(fsr, self.ticket.field_service_request_ids)
        self.assertIn(fsr, other_ticket.field_service_request_ids)

    def test_ticket_link_survives_write_on_other_fields(self):
        """Writing unrelated fields must not clear the ticket link."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        fsr.write({'partner_id': self.partner.id})  # no-op write on another field
        self.assertEqual(fsr.helpdesk_ticket_id, self.ticket)

    # ─────────────────────────────────────────────
    # Cascade / deletion safety
    # ─────────────────────────────────────────────

    def test_fsr_deletion_does_not_delete_ticket(self):
        """Deleting an FSR must not cascade to the linked ticket."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        ticket_id = self.ticket.id
        fsr.unlink()
        self.assertTrue(
            self.env['helpdesk.ticket'].browse(ticket_id).exists(),
            "Ticket should survive FSR deletion.",
        )

    def test_fsr_unlinked_from_ticket_after_deletion(self):
        """After FSR deletion the ticket's request list must be empty."""
        fsr = self.env['field.service.request'].create({
            'partner_id': self.partner.id,
            'helpdesk_ticket_id': self.ticket.id,
        })
        fsr.unlink()
        self.assertEqual(self.ticket.field_service_request_count, 0)
        self.assertFalse(self.ticket.field_service_request_ids)
