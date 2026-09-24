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
from unittest.mock import Mock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.fields import Datetime
from odoo import _
from odoo.http import _request_stack
from odoo.addons.cyllo_front_desk.controllers.main import FrontdeskMeetingController


class TestFrontdeskMeetingApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1. Create a Station
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Main Reception',
            'is_host': True,
        })
        
        # 2. Create a Host Employee
        cls.host = cls.env['hr.employee'].create({
            'name': 'John Doe',
            'work_email': 'johndoe@example.com',
        })

    def _get_response_content(self, response):
        if isinstance(response, str):
            return response
        if hasattr(response, 'get_data'):
            return response.get_data(as_text=True)
        if hasattr(response, 'data'):
            return response.data.decode('utf-8')
        return str(response)

    def test_meeting_approval_flow(self):
        # 1. Create a Meeting-type visitor with a host
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Alice Smith',
            'visitor_type': 'meeting',
            'host_id': self.host.id,
            'station_id': self.station.id,
            'purpose': 'Project Discussion',
            'expected_arrival': Datetime.now(),
        })

        # Assert initial state is Draft, email NOT yet sent
        self.assertEqual(visitor.state, 'draft')
        self.assertTrue(visitor.access_token)
        self.assertFalse(visitor.is_approval_email_sent)

        # 2. Click Send Request button
        visitor.action_send_request()
        self.assertTrue(visitor.is_approval_email_sent)

        # Assert email is sent to the host
        mails = self.env['mail.mail'].search([('email_to', '=', self.host.work_email)])
        self.assertTrue(mails)
        self.assertIn(visitor.access_token, mails[0].body_html)

        # 3. Clicking Send Request again should raise UserError
        with self.assertRaises(UserError):
            visitor.action_send_request()

        # 4. Test Controller Approval with access token
        controller = FrontdeskMeetingController()
        
        mock_request = Mock(
            env=self.env,
            make_response=lambda html, headers: html
        )
        _request_stack.push(mock_request)
        try:
            # Call approve method in controller
            response = controller.approve_meeting(visitor.access_token)
            self.assertTrue(response)
            self.assertIn("Meeting Approved", self._get_response_content(response))

            # Refresh visitor and check state
            visitor.invalidate_model()
            self.assertEqual(visitor.state, 'planned')
            self.assertEqual(visitor.approved_by_id, self.host)
            self.assertTrue(visitor.approved_datetime)

            # Check chatter message
            chatter_messages = visitor.message_ids.mapped('body')
            self.assertTrue(any("Meeting request approved by" in msg for msg in chatter_messages))

            # 5. Repeat click: should not alter state and should return already processed
            response_processed = controller.approve_meeting(visitor.access_token)
            self.assertIn("Already Processed", self._get_response_content(response_processed))
        finally:
            _request_stack.pop()

    def test_meeting_rejection_flow(self):
        # 1. Create a Meeting-type visitor
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Bob Miller',
            'visitor_type': 'meeting',
            'host_id': self.host.id,
            'station_id': self.station.id,
            'purpose': 'Interview',
            'expected_arrival': Datetime.now(),
        })

        self.assertEqual(visitor.state, 'draft')
        self.assertFalse(visitor.is_approval_email_sent)

        # 2. Send Request, then Test Controller Rejection
        visitor.action_send_request()

        controller = FrontdeskMeetingController()
        
        mock_request = Mock(
            env=self.env,
            make_response=lambda html, headers: html
        )
        _request_stack.push(mock_request)
        try:
            # Call reject method in controller
            response = controller.reject_meeting(visitor.access_token)
            self.assertTrue(response)
            self.assertIn("Meeting Rejected", self._get_response_content(response))

            # Check visitor state
            visitor.invalidate_model()
            self.assertEqual(visitor.state, 'cancelled')
            self.assertEqual(visitor.rejected_by_id, self.host)
            self.assertTrue(visitor.rejected_datetime)

            # Check chatter message
            chatter_messages = visitor.message_ids.mapped('body')
            self.assertTrue(any("Meeting request rejected by" in msg for msg in chatter_messages))

            # Repeat click on reject
            response_processed = controller.reject_meeting(visitor.access_token)
            self.assertIn("Already Processed", self._get_response_content(response_processed))

            # Trying to approve now should also return already processed
            response_approve = controller.approve_meeting(visitor.access_token)
            self.assertIn("Already Processed", self._get_response_content(response_approve))
        finally:
            _request_stack.pop()

    def test_send_request_validation(self):
        # Test: sending request without host should raise error
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'No Host Visitor',
            'visitor_type': 'meeting',
            'station_id': self.station.id,
            'purpose': 'Discussion',
            'expected_arrival': Datetime.now(),
        })
        with self.assertRaises(UserError):
            visitor.action_send_request()

        # Test: sending request for enquiry type should raise error
        enquiry_visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Enquiry Visitor',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        with self.assertRaises(UserError):
            enquiry_visitor.action_send_request()

    def test_non_meeting_visitor_flow(self):
        # Enquiry type visitor should start in Planned state immediately
        visitor = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Charlie Green',
            'visitor_type': 'enquiry',
            'host_id': self.host.id,
            'station_id': self.station.id,
        })

        self.assertEqual(visitor.state, 'planned')
        self.assertFalse(visitor.access_token)
        self.assertFalse(visitor.is_approval_email_sent)
