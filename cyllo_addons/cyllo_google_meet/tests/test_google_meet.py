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

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestGoogleMeet(TransactionCase):

    def setUp(self):
        super(TestGoogleMeet, self).setUp()
        self.CalendarEvent = self.env['calendar.event']
        self.Partner = self.env['res.partner']
        self.partner1 = self.Partner.create({'name': 'Partner 1', 'email': 'partner1@example.com'})
        self.partner2 = self.Partner.create({'name': 'Partner 2', 'email': 'partner2@example.com'})
        self.env['ir.config_parameter'].sudo().set_param('cyllo_google.refresh_token', 'dummy_refresh')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_google.client_id', 'dummy_client_id')
        self.env['ir.config_parameter'].sudo().set_param('cyllo_google.client_secret', 'dummy_client_secret')

    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.post')
    def test_01_create_google_meet(self, mock_post):
        """ Test creating a calendar event with Google Meet enabled """
        mock_response_token = MagicMock()
        mock_response_token.status_code = 200
        mock_response_token.json.return_value = {'access_token': 'mock_access_token'}
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_event_id_123',
            'conferenceData': {
                'entryPoints': [{'entryPointType': 'video', 'uri': 'https://meet.google.com/mock'}]
            }
        }
        # requests.post is called twice: once for token, once for meet creation
        mock_post.side_effect = [mock_response_token, mock_response_meet]
        event = self.CalendarEvent.create({
            'name': 'Test Meet Event',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_google_meet': True,
            'partner_ids': [(6, 0, [self.partner1.id, self.partner2.id])]
        })
        self.assertTrue(event.google_meet_url)
        self.assertEqual(event.google_meet_url, 'https://meet.google.com/mock')
        self.assertEqual(event.google_meet_event_id, 'mock_event_id_123')
        self.assertTrue(event.description)
        self.assertIn('Join Google Meet', event.description)
        self.assertIn('https://meet.google.com/mock', event.description)
        action = event.action_google_meet_url()
        self.assertEqual(action.get('url'), 'https://meet.google.com/mock')
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertEqual(action.get('target'), 'new')

    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.post')
    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.delete')
    def test_02_delete_google_meet(self, mock_delete, mock_post):
        """ Test unlinking a calendar event with Google Meet enabled """
        mock_response_token = MagicMock()
        mock_response_token.status_code = 200
        mock_response_token.json.return_value = {'access_token': 'mock_access_token'}
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_event_id_123',
            'conferenceData': {
                'entryPoints': [{'entryPointType': 'video', 'uri': 'https://meet.google.com/mock'}]
            }
        }
        mock_post.side_effect = [mock_response_token, mock_response_meet]

        event = self.CalendarEvent.create({
            'name': 'Test Meet Event Delete',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_google_meet': True,
        })
        self.assertEqual(event.google_meet_event_id, 'mock_event_id_123')
        mock_post.side_effect = [mock_response_token]
        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204
        mock_delete.return_value = mock_delete_response
        event.unlink()
        mock_delete.assert_called_once()
        self.assertIn('mock_event_id_123', mock_delete.call_args[0][0])

    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.post')
    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.delete')
    def test_03_onchange_is_google_meet(self, mock_delete, mock_post):
        """ Test onchange method when is_google_meet is unchecked """
        event = self.CalendarEvent.new({
            'name': 'Test Meet Event Onchange',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_google_meet': True,
            'google_meet_event_id': 'mock_event_id_123',
            'google_meet_url': 'https://meet.google.com/mock'
        })
        mock_response_token = MagicMock()
        mock_response_token.status_code = 200
        mock_response_token.json.return_value = {'access_token': 'mock_access_token'}
        mock_post.side_effect = [mock_response_token]
        event.is_google_meet = False
        event._onchange_is_google_meet()
        self.assertFalse(event.google_meet_url)
        self.assertFalse(event.google_meet_event_id)
        mock_delete.assert_called_once()

    def test_04_missing_oauth_config(self):
        """ Test missing oauth configuration """
        self.env['ir.config_parameter'].sudo().set_param('cyllo_google.refresh_token', False)
        with self.assertRaises(ValidationError):
            self.CalendarEvent.create({
                'name': 'Test Meet Event No Config',
                'start': datetime.datetime.now(),
                'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
                'is_google_meet': True,
            })

    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.post')
    def test_05_planned_google_meet_updates_activity(self, mock_post):
        """A Google Meet activity keeps its planned note in sync with the event."""
        mock_response_token = MagicMock()
        mock_response_token.status_code = 200
        mock_response_token.json.return_value = {'access_token': 'mock_access_token'}
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_event_id_123',
            'conferenceData': {
                'entryPoints': [{'entryPointType': 'video', 'uri': 'https://meet.google.com/mock'}]
            }
        }
        mock_post.side_effect = [mock_response_token, mock_response_meet]

        activity_type = self.env.ref('mail.mail_activity_data_meeting')
        scheduler = self.env['mail.activity.schedule'].with_context(
            active_model='res.partner', active_id=self.partner1.id,
        ).create({
            'activity_type_id': activity_type.id,
            'is_google_meet': True,
        })
        action = scheduler.action_create_calendar_event()
        self.assertTrue(action['context']['default_is_google_meet'])

        event = self.CalendarEvent.with_context(action['context']).create({
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
        })
        self.assertTrue(event.activity_ids)
        self.assertIn('https://meet.google.com/mock', event.activity_ids.note)
        self.assertIn('Start:', event.activity_ids.note)
        self.assertIn('End:', event.activity_ids.note)

    @patch('odoo.addons.cyllo_google_meet.models.calendar_event.requests.post')
    def test_06_alarm_notification(self, mock_post):
        """ Test alarm notification """
        mock_response_token = MagicMock()
        mock_response_token.status_code = 200
        mock_response_token.json.return_value = {'access_token': 'mock_access_token'}
        mock_response_meet = MagicMock()
        mock_response_meet.status_code = 200
        mock_response_meet.json.return_value = {
            'id': 'mock_event_id_123',
            'conferenceData': {
                'entryPoints': [{'entryPointType': 'video', 'uri': 'https://meet.google.com/mock'}]
            }
        }
        mock_post.side_effect = [mock_response_token, mock_response_meet]
        event = self.CalendarEvent.create({
            'name': 'Test Meet Event Alarm',
            'start': datetime.datetime.now(),
            'stop': datetime.datetime.now() + datetime.timedelta(hours=1),
            'is_google_meet': True,
            'partner_ids': [(6, 0, [self.partner1.id])]
        })
        # We need to mock the bus._sendone method specifically on the env
        with patch.object(type(self.env['bus.bus']), '_sendone') as mock_sendone, \
             patch.object(type(self.env['calendar.event']), 'message_post') as mock_message_post:
            event._google_meet_alarm_notification()
            mock_message_post.assert_called_once()
            self.assertIn('Google Meet Reminder', mock_message_post.call_args[1].get('body', ''))
            # _sendone is called for each attendee's partner (partner1 and the current user who creates the event)
            self.assertTrue(mock_sendone.called)
            call_args = mock_sendone.call_args[0]
            self.assertEqual(call_args[1]['title'], 'Google Meet Reminder')
            self.assertEqual(call_args[1]['meet_url'], 'https://meet.google.com/mock')
