# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
import datetime
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestZoomMeet(TransactionCase):

    def setUp(self):
        super(TestZoomMeet, self).setUp()
        self.CalendarEvent = self.env['calendar.event']
        self.Partner = self.env['res.partner']
        self.partner1 = self.Partner.create({'name': 'Partner 1', 'email': 'partner1@example.com'})
        self.partner2 = self.Partner.create({'name': 'Partner 2', 'email': 'partner2@example.com'})
        self.env['ir.config_parameter'].sudo().set_param('cyllo_zoom.zoom_token', 'mock_zoom_token')

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.post')
    def test_01_create_zoom_meet(self, mock_post):
        """ Test creating a calendar event with Zoom Meet enabled """
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_zoom_event_123',
            'join_url': 'https://zoom.us/j/mock_zoom_event_123',
            'password': 'mock_password'
        }
        
        mock_post.return_value = mock_response_meet
        event = self.CalendarEvent.create({
            'name': 'Test Zoom Event',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_zoom_meet': True,
            'partner_ids': [(6, 0, [self.partner1.id, self.partner2.id])]
        })
        self.assertTrue(event.zoom_meet_url)
        self.assertEqual(event.zoom_meet_url, 'https://zoom.us/j/mock_zoom_event_123')
        self.assertEqual(event.zoom_event, 'mock_zoom_event_123')
        self.assertEqual(event.zoom_meet_code, 'mock_zoom_event_123')
        self.assertEqual(event.zoom_meet_password, 'mock_password')
        self.assertTrue(event.description)
        self.assertIn('Join Zoom Meeting', event.description)
        self.assertIn('mock_zoom_event_123', event.description)
        action = event.action_zoom_meet_url()
        self.assertEqual(action.get('url'), 'https://zoom.us/j/mock_zoom_event_123')
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertEqual(action.get('target'), 'new')

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.post')
    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.delete')
    def test_02_delete_zoom_meet(self, mock_delete, mock_post):
        """ Test unlinking a calendar event with Zoom Meet enabled """
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_zoom_event_123',
            'join_url': 'https://zoom.us/j/mock_zoom_event_123',
            'password': 'mock_password'
        }
        mock_post.return_value = mock_response_meet

        event = self.CalendarEvent.create({
            'name': 'Test Zoom Event Delete',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_zoom_meet': True,
        })
        
        self.assertEqual(event.zoom_event, 'mock_zoom_event_123')
        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204
        mock_delete.return_value = mock_delete_response
        event.unlink()
        mock_delete.assert_called_once()
        self.assertIn('mock_zoom_event_123', mock_delete.call_args[0][0])

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.delete')
    def test_03_onchange_is_zoom_meet(self, mock_delete):
        """ Test onchange method when is_zoom_meet is unchecked """
        event = self.CalendarEvent.new({
            'name': 'Test Zoom Event Onchange',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_zoom_meet': True,
            'zoom_event': 'mock_zoom_event_123',
            'zoom_meet_url': 'https://zoom.us/j/mock_zoom_event_123',
            'zoom_meet_code': 'mock_zoom_event_123',
            'zoom_meet_password': 'mock_password'
        })
        event.is_zoom_meet = False
        event._onchange_is_zoom_meet()
        self.assertFalse(event.zoom_meet_url)
        self.assertFalse(event.zoom_event)
        self.assertFalse(event.zoom_meet_code)
        self.assertFalse(event.zoom_meet_password)
        mock_delete.assert_called_once()

    def test_04_missing_oauth_config(self):
        """ Test missing zoom token configuration """
        self.env['ir.config_parameter'].sudo().set_param('cyllo_zoom.zoom_token', False)
        with self.assertRaises(UserError):
            self.CalendarEvent.create({
                'name': 'Test Zoom Event No Config',
                'start': datetime.datetime.now(),
                'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
                'is_zoom_meet': True,
            })

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.post')
    def test_05_planned_zoom_meet_updates_activity(self, mock_post):
        """A Zoom Meet activity receives the generated meeting details."""
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_zoom_event_123',
            'join_url': 'https://zoom.us/j/mock_zoom_event_123',
            'password': 'mock_password',
        }
        mock_post.return_value = mock_response_meet

        activity_type = self.env.ref('mail.mail_activity_data_meeting')
        scheduler = self.env['mail.activity.schedule'].with_context(
            active_model='res.partner', active_id=self.partner1.id,
        ).create({
            'activity_type_id': activity_type.id,
            'is_zoom_meet': True,
        })
        action = scheduler.action_create_calendar_event()
        self.assertTrue(action['context']['default_is_zoom_meet'])

        event = self.CalendarEvent.with_context(action['context']).create({
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
        })
        self.assertTrue(event.activity_ids)
        self.assertIn('https://zoom.us/j/mock_zoom_event_123', event.activity_ids.note)
        self.assertIn('Start:', event.activity_ids.note)
        self.assertIn('End:', event.activity_ids.note)

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.post')
    def test_06_alarm_notification(self, mock_post):
        """ Test zoom alarm notification """
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_zoom_event_123',
            'join_url': 'https://zoom.us/j/mock_zoom_event_123',
            'password': 'mock_password'
        }
        mock_post.return_value = mock_response_meet
        event = self.CalendarEvent.create({
            'name': 'Test Zoom Event Alarm',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_zoom_meet': True,
            'partner_ids': [(6, 0, [self.partner1.id])]
        })
        # We need to mock the bus._sendone method specifically on the env
        # as well as the message_post method
        with patch.object(type(self.env['bus.bus']), '_sendone') as mock_sendone, \
             patch.object(type(self.env['calendar.event']), 'message_post') as mock_message_post:
            event._zoom_alarm_notification()
            mock_message_post.assert_called_once()
            self.assertIn('Zoom Meeting Reminder', mock_message_post.call_args[1].get('body', ''))
            # _sendone is called for each attendee's partner
            self.assertTrue(mock_sendone.called)
            call_args = mock_sendone.call_args[0]
            self.assertEqual(call_args[1]['title'], 'Zoom Meeting Reminder')
            self.assertEqual(call_args[1]['zoom_url'], 'https://zoom.us/j/mock_zoom_event_123')

    @patch('odoo.addons.cyllo_zoom.models.calendar_event.requests.post')
    def test_07_token_expired_retry(self, mock_post):
        """ Test zoom token expiration and automatic retry during meeting creation """
        # First call fails with code 124 (token expired)
        mock_response_expired = MagicMock()
        mock_response_expired.json.return_value = {'code': 124}
        # Second call succeeds
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            'id': 'mock_zoom_event_retry',
            'join_url': 'https://zoom.us/j/mock_zoom_event_retry',
            'password': 'mock_password_retry'
        }
        mock_post.side_effect = [mock_response_expired, mock_response_success]
        with patch.object(type(self.env['res.config.settings']), 'action_zoom_meet_refresh_token') as mock_refresh:
            event = self.CalendarEvent.create({
                'name': 'Test Zoom Event Retry',
                'start': datetime.datetime.now(),
                'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
                'is_zoom_meet': True,
            })
            mock_refresh.assert_called_once()
            self.assertEqual(event.zoom_event, 'mock_zoom_event_retry')
