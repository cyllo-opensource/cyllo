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
from odoo.exceptions import UserError
from odoo.fields import Datetime


class TestFrontdeskVisitor(TransactionCase):
    """Tests for FrontdeskVisitor model: state transitions, check-in/out, and drink flow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Station with all features enabled
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Main Lobby',
            'is_host': True,
            'is_drink': True,
            'notify_by_email': False,
            'notify_by_discuss': False,
        })

        # Station with host and drink disabled
        cls.station_minimal = cls.env['frontdesk.frontdesk'].create({
            'name': 'Side Entrance',
            'is_host': False,
            'is_drink': False,
        })

        # Host employee
        cls.host = cls.env['hr.employee'].create({
            'name': 'Jane Host',
            'work_email': 'jane@example.com',
        })

        # Drink
        cls.drink = cls.env['frontdesk.drink'].create({
            'name': 'Coffee',
            'sequence': 1,
        })
        cls.station.drink_selection_ids = [(4, cls.drink.id)]

    # ------------------------------------------------------------------
    # Creation / defaults
    # ------------------------------------------------------------------

    def test_meeting_visitor_created_in_draft(self):
        """Meeting-type visitor must start in 'draft' and have an access token."""
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Test Meeting',
            'visitor_type': 'meeting',
            'station_id': self.station.id,
        })
        self.assertEqual(visitor.state, 'draft')
        self.assertTrue(visitor.access_token, "Meeting visitor must have an access token.")

    def test_enquiry_visitor_created_in_planned(self):
        """Enquiry-type visitor must start in 'planned' and have no access token."""
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Test Enquiry',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        self.assertEqual(visitor.state, 'planned')
        self.assertFalse(visitor.access_token)

    def test_sequence_auto_assigned(self):
        """Visitor reference should be assigned from sequence, not left as 'New'."""
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Seq Visitor',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        self.assertNotEqual(visitor.name, 'New')
        self.assertTrue(visitor.name)

    def test_host_cleared_when_station_has_no_host(self):
        """host_id must be cleared on create when station.is_host is False."""
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'No-Host Visitor',
            'visitor_type': 'enquiry',
            'station_id': self.station_minimal.id,
            'host_id': self.host.id,
        })
        self.assertFalse(visitor.host_id)

    def test_drink_cleared_when_station_has_no_drink(self):
        """drink_id must be cleared on create when station.is_drink is False."""
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'No-Drink Visitor',
            'visitor_type': 'enquiry',
            'station_id': self.station_minimal.id,
            'drink_id': self.drink.id,
        })
        self.assertFalse(visitor.drink_id)

    # ------------------------------------------------------------------
    # Check-in / Check-out / Cancel
    # ------------------------------------------------------------------

    def _planned_visitor(self, name='Check-In Visitor'):
        return self.env['frontdesk.visitor'].create({
            'visitor_name': name,
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })

    def test_check_in_sets_state_and_time(self):
        visitor = self._planned_visitor()
        self.assertEqual(visitor.state, 'planned')
        visitor.action_check_in()
        self.assertEqual(visitor.state, 'checked_in')
        self.assertTrue(visitor.check_in)

    def test_check_in_requires_planned_state(self):
        visitor = self._planned_visitor()
        visitor.action_check_in()
        # Already checked in → should raise
        with self.assertRaises(UserError):
            visitor.action_check_in()

    def test_check_out_sets_state_and_time(self):
        visitor = self._planned_visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        self.assertEqual(visitor.state, 'checked_out')
        self.assertTrue(visitor.check_out)

    def test_check_out_requires_checked_in_state(self):
        visitor = self._planned_visitor()
        with self.assertRaises(UserError):
            visitor.action_check_out()

    def test_cancel_from_planned(self):
        visitor = self._planned_visitor()
        visitor.action_cancel()
        self.assertEqual(visitor.state, 'cancelled')

    def test_cancel_from_checked_in(self):
        visitor = self._planned_visitor()
        visitor.action_check_in()
        visitor.action_cancel()
        self.assertEqual(visitor.state, 'cancelled')

    def test_cancel_checked_out_raises(self):
        visitor = self._planned_visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        with self.assertRaises(UserError):
            visitor.action_cancel()

    # ------------------------------------------------------------------
    # Duration computation
    # ------------------------------------------------------------------

    def test_duration_computed_after_check_out(self):
        visitor = self._planned_visitor()
        visitor.action_check_in()
        visitor.action_check_out()
        self.assertGreaterEqual(visitor.duration, 0.0)

    def test_duration_zero_without_check_in(self):
        visitor = self._planned_visitor()
        self.assertEqual(visitor.duration, 0.0)

    # ------------------------------------------------------------------
    # Drink served
    # ------------------------------------------------------------------

    def test_action_drink_served(self):
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Drink Visitor',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
            'drink_id': self.drink.id,
        })
        self.assertFalse(visitor.drink_served)
        visitor.action_drink_served()
        self.assertTrue(visitor.drink_served)

    # ------------------------------------------------------------------
    # Partner onchange
    # ------------------------------------------------------------------

    def test_onchange_partner_fills_fields(self):
        partner = self.env['res.partner'].create({
            'name': 'ACME Corp',
            'is_company': True,
            'email': 'acme@example.com',
            'phone': '+919876543210',
        })
        contact = self.env['res.partner'].create({
            'name': 'Alice',
            'parent_id': partner.id,
            'email': 'alice@acme.com',
            'phone': '+919876543211',
        })

        visitor = self.env['frontdesk.visitor'].new({
            'visitor_name': '',
            'visitor_type': 'meeting',
            'station_id': self.station.id,
            'partner_id': contact.id,
        })
        visitor._onchange_partner_id()

        self.assertEqual(visitor.visitor_name, contact.name)
        self.assertEqual(visitor.email, contact.email)
        self.assertEqual(visitor.company, 'ACME Corp')

    # ------------------------------------------------------------------
    # Write — visitor_type change updates state and token
    # ------------------------------------------------------------------

    def test_write_change_to_enquiry_clears_token(self):
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Switch Visitor',
            'visitor_type': 'meeting',
            'station_id': self.station.id,
        })
        self.assertEqual(visitor.state, 'draft')
        self.assertTrue(visitor.access_token)

        visitor.write({'visitor_type': 'enquiry'})
        self.assertEqual(visitor.state, 'planned')

    # ------------------------------------------------------------------
    # Enquiry action
    # ------------------------------------------------------------------

    def test_action_create_enquiry_raises_for_meeting_type(self):
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Meeting Guy',
            'visitor_type': 'meeting',
            'station_id': self.station.id,
        })
        with self.assertRaises(UserError):
            visitor.action_create_enquiry()

    def test_action_create_enquiry_returns_wizard_action(self):
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Enquiry Guy',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        result = visitor.action_create_enquiry()
        self.assertEqual(result['res_model'], 'frontdesk.visitor.enquiry.wizard')

    def test_action_create_enquiry_raises_if_already_linked(self):
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Repeat Enquiry',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        # Simulate an enquiry already linked
        enquiry = self.env['frontdesk.enquiry'].create({
            'visitor_name': visitor.visitor_name,
            'station_id': self.station.id,
            'enquiry_type': 'general',
            'subject': 'Test',
            'visitor_id': visitor.id,
        })
        visitor.enquiry_id = enquiry.id
        with self.assertRaises(UserError):
            visitor.action_create_enquiry()
