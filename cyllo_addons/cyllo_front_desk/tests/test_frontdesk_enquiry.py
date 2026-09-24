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


class TestFrontdeskEnquiry(TransactionCase):
    """Tests for FrontdeskEnquiry model: lifecycle, auto-visitor creation, state transitions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Reception Alpha',
        })

        cls.handler = cls.env['hr.employee'].create({
            'name': 'Help Desk Agent',
            'work_email': 'agent@example.com',
        })

    def _make_enquiry(self, **kwargs):
        vals = {
            'visitor_name': 'Test Visitor',
            'station_id': self.station.id,
            'enquiry_type': 'general',
            'subject': 'General Query',
        }
        vals.update(kwargs)
        return self.env['frontdesk.enquiry'].create(vals)

    # ------------------------------------------------------------------
    # Auto-visitor creation on enquiry create
    # ------------------------------------------------------------------

    def test_enquiry_auto_creates_visitor(self):
        enquiry = self._make_enquiry()
        self.assertTrue(enquiry.visitor_id, "A visitor should be auto-created on enquiry creation.")
        self.assertEqual(enquiry.visitor_id.visitor_type, 'enquiry')
        self.assertEqual(enquiry.visitor_id.state, 'planned')

    def test_auto_visitor_back_links_to_enquiry(self):
        enquiry = self._make_enquiry()
        self.assertEqual(enquiry.visitor_id.enquiry_id, enquiry)

    def test_auto_visitor_inherits_contact_info(self):
        enquiry = self._make_enquiry(
            visitor_name='Jane Doe',
            phone='+919876500001',
            email='jane@example.com',
            company='Jane Corp',
            handled_by=self.handler.id,
        )
        visitor = enquiry.visitor_id
        self.assertEqual(visitor.visitor_name, 'Jane Doe')
        self.assertEqual(visitor.phone, '+919876500001')
        self.assertEqual(visitor.email, 'jane@example.com')
        self.assertEqual(visitor.company, 'Jane Corp')
        self.assertEqual(visitor.host_id, self.handler)

    def test_sequence_reference_assigned(self):
        enquiry = self._make_enquiry()
        self.assertNotEqual(enquiry.name, 'New')
        self.assertTrue(enquiry.name)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def test_action_in_progress_from_new(self):
        enquiry = self._make_enquiry()
        self.assertEqual(enquiry.state, 'new')
        enquiry.action_in_progress()
        self.assertEqual(enquiry.state, 'in_progress')

    def test_action_in_progress_raises_if_not_new(self):
        enquiry = self._make_enquiry()
        enquiry.action_in_progress()
        with self.assertRaises(UserError):
            enquiry.action_in_progress()

    def test_action_close_from_in_progress(self):
        enquiry = self._make_enquiry()
        enquiry.action_in_progress()
        enquiry.action_close()
        self.assertEqual(enquiry.state, 'closed')

    def test_action_close_from_new(self):
        enquiry = self._make_enquiry()
        enquiry.action_close()
        self.assertEqual(enquiry.state, 'closed')

    def test_action_close_raises_if_lost(self):
        enquiry = self._make_enquiry()
        enquiry.action_mark_lost()
        with self.assertRaises(UserError):
            enquiry.action_close()

    def test_action_mark_lost(self):
        enquiry = self._make_enquiry()
        enquiry.action_mark_lost()
        self.assertEqual(enquiry.state, 'lost')

    def test_action_reset_new(self):
        enquiry = self._make_enquiry()
        enquiry.action_in_progress()
        enquiry.action_reset_new()
        self.assertEqual(enquiry.state, 'new')

    # ------------------------------------------------------------------
    # action_view_visitor
    # ------------------------------------------------------------------

    def test_action_view_visitor_returns_form(self):
        enquiry = self._make_enquiry()
        result = enquiry.action_view_visitor()
        self.assertEqual(result['res_model'], 'frontdesk.visitor')
        self.assertEqual(result['res_id'], enquiry.visitor_id.id)

    def test_action_view_visitor_raises_when_not_linked(self):
        enquiry = self._make_enquiry()
        enquiry.visitor_id = False
        with self.assertRaises(UserError):
            enquiry.action_view_visitor()

    # ------------------------------------------------------------------
    # action_convert_to_visitor (legacy path, visitor_id not pre-linked)
    # ------------------------------------------------------------------

    def test_convert_to_visitor_raises_if_already_linked(self):
        enquiry = self._make_enquiry()
        # Auto-creation already links a visitor
        with self.assertRaises(UserError):
            enquiry.action_convert_to_visitor()

    def test_convert_to_visitor_creates_partner_when_no_match(self):
        """When no existing partner matches, one should be created."""
        enquiry = self._make_enquiry(
            visitor_name='Unique Contact XYZ',
            email='uniquexyz@nowhere.test',
            company='XYZ Corp',
        )
        # Detach the auto-created visitor so we can test manual conversion
        enquiry.visitor_id = False
        enquiry.action_convert_to_visitor()
        self.assertTrue(enquiry.partner_id)
        self.assertEqual(enquiry.partner_id.name, 'Unique Contact XYZ')
