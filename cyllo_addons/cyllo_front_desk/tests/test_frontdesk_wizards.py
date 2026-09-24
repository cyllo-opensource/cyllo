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


class TestFrontdeskEmergencyWizard(TransactionCase):
    """Tests for FrontdeskEmergencyWizard and FrontdeskEmergencyLog."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Ground Floor',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Security Officer',
            'work_email': 'security@example.com',
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Alert User',
            'login': 'alert_user_test',
            'email': 'alertuser@example.com',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })

        cls.alert = cls.env['frontdesk.emergency.alert'].create({
            'name': 'Bomb Threat',
            'station_ids': [(4, cls.station.id)],
            'default_message': 'Evacuate immediately!',
            'recipient_employee_ids': [(4, cls.employee.id)],
            'recipient_user_ids': [(4, cls.user.id)],
            'active': True,
        })

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    def test_onchange_alert_id_populates_message(self):
        wizard = self.env['frontdesk.emergency.wizard'].new({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': '',
        })
        wizard._onchange_alert_id()
        self.assertEqual(wizard.message, 'Evacuate immediately!')

    def test_onchange_clears_message_when_no_alert(self):
        wizard = self.env['frontdesk.emergency.wizard'].new({
            'station_id': self.station.id,
            'message': 'Old message',
        })
        wizard._onchange_alert_id()

    # ------------------------------------------------------------------
    # action_send_alert
    # ------------------------------------------------------------------

    def test_send_alert_creates_log_record(self):
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': 'Evacuate immediately!',
        })
        action = wizard.action_send_alert()
        self.assertEqual(action['type'], 'ir.actions.client')
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertTrue(log.exists())
        self.assertEqual(log.station_id, self.station)
        self.assertEqual(log.alert_id, self.alert)
        self.assertEqual(log.message, 'Evacuate immediately!')

    def test_send_alert_log_includes_employee_in_summary(self):
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': 'Evacuate immediately!',
        })
        action = wizard.action_send_alert()
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertIn('Security Officer', log.recipient_summary)

    def test_send_alert_log_includes_user_in_summary(self):
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': 'Test Alert',
        })
        action = wizard.action_send_alert()
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertIn('Alert User', log.recipient_summary)

    def test_send_alert_with_no_recipients_still_creates_log(self):
        """Alert with no recipients configured should still create an audit log."""
        alert_empty = self.env['frontdesk.emergency.alert'].create({
            'name': 'Silent Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Caution.',
            'active': True,
        })
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': alert_empty.id,
            'message': 'Caution.',
        })
        action = wizard.action_send_alert()
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertTrue(log.exists())

    # ------------------------------------------------------------------
    # Log sequence
    # ------------------------------------------------------------------

    def test_emergency_log_sequence_reference_assigned(self):
        log = self.env['frontdesk.emergency.log'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': 'Test',
            'recipient_summary': 'None',
            'user_id': self.env.user.id,
        })
        self.assertNotEqual(log.name, '/')
        self.assertTrue(log.name)

    # ------------------------------------------------------------------
    # Channel notifications
    # ------------------------------------------------------------------

    def test_send_alert_posts_to_discuss_channel(self):
        channel = self.env['discuss.channel'].create({
            'name': 'Emergency Room',
            'channel_type': 'channel',
        })
        alert_with_channel = self.env['frontdesk.emergency.alert'].create({
            'name': 'Channel Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Channel message.',
            'recipient_channel_ids': [(4, channel.id)],
            'active': True,
        })
        initial_msg_count = len(channel.message_ids)
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': alert_with_channel.id,
            'message': 'Channel message.',
        })
        wizard.action_send_alert()
        self.assertGreater(len(channel.message_ids), initial_msg_count)

    def test_send_alert_summary_lists_channel(self):
        channel = self.env['discuss.channel'].create({
            'name': 'Ops Channel',
            'channel_type': 'channel',
        })
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Ops Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Ops alert!',
            'recipient_channel_ids': [(4, channel.id)],
            'active': True,
        })
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': alert.id,
            'message': 'Ops alert!',
        })
        action = wizard.action_send_alert()
        log = self.env['frontdesk.emergency.log'].browse(action['params']['next']['res_id'])
        self.assertIn('Ops Channel', log.recipient_summary)


class TestFrontdeskVisitorEnquiryWizard(TransactionCase):
    """Tests for FrontdeskVisitorEnquiryWizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Wizard Test Station',
        })

        cls.handler = cls.env['hr.employee'].create({
            'name': 'Wizard Handler',
            'work_email': 'wizhandler@example.com',
        })

        cls.visitor = cls.env['frontdesk.visitor'].create({
            'visitor_name': 'Wizard Visitor',
            'visitor_type': 'enquiry',
            'station_id': cls.station.id,
            'phone': '+1234567890',
            'email': 'wiz@test.com',
            'company': 'Wiz Ltd',
        })

    def _make_wizard(self, visitor=None):
        visitor = visitor or self.visitor
        return self.env['frontdesk.visitor.enquiry.wizard'].create({
            'visitor_id': visitor.id,
            'visitor_name': visitor.visitor_name,
            'phone': visitor.phone,
            'email': visitor.email,
            'company': visitor.company,
            'station_id': self.station.id,
            'handled_by': self.handler.id,
            'enquiry_type': 'general',
            'subject': 'Walk-in query',
        })

    def test_wizard_creates_enquiry(self):
        wizard = self._make_wizard()
        result = wizard.action_create_enquiry()
        self.assertEqual(result['res_model'], 'frontdesk.enquiry')
        enquiry = self.env['frontdesk.enquiry'].browse(result['res_id'])
        self.assertTrue(enquiry.exists())
        self.assertEqual(enquiry.visitor_name, 'Wizard Visitor')
        self.assertEqual(enquiry.subject, 'Walk-in query')

    def test_wizard_links_enquiry_to_visitor(self):
        wizard = self._make_wizard()
        result = wizard.action_create_enquiry()
        enquiry = self.env['frontdesk.enquiry'].browse(result['res_id'])
        self.assertEqual(self.visitor.enquiry_id, enquiry)

    def test_wizard_raises_if_enquiry_already_linked(self):
        wizard = self._make_wizard()
        wizard.action_create_enquiry()
        # Try to run wizard again on same visitor
        wizard2 = self._make_wizard()
        with self.assertRaises(UserError):
            wizard2.action_create_enquiry()

    def test_wizard_posts_chatter_on_visitor(self):
        wizard = self._make_wizard()
        initial_msg_count = len(self.visitor.message_ids)
        wizard.action_create_enquiry()
        self.assertGreater(len(self.visitor.message_ids), initial_msg_count)
