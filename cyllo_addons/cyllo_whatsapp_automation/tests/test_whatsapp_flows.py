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
import json
from unittest.mock import MagicMock, mock_open, patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import (FLOWS_MODULE, WhatsappAutomationCommon, api_error,
                     fake_response)


@tagged('post_install', '-at_install')
class TestWhatsappFlows(WhatsappAutomationCommon):
    """Tests for the `whatsapp.flows` model."""

    # -- computed fields ----------------------------------------------------
    def test_compute_flow_name(self):
        flow = self._create_flow('My  Test Flow')
        db_uuid = self.env['ir.config_parameter'].sudo().get_param(
            'database.uuid').replace('-', '')
        self.assertEqual(flow.flow_name, f'my__test_flow_{db_uuid}')

    def test_compute_flow_name_follows_rename(self):
        flow = self._create_flow('Old Name')
        flow.name = 'New Name'
        self.assertTrue(flow.flow_name.startswith('new_name_'))

    def test_defaults(self):
        flow = self._create_flow()
        self.assertEqual(flow.state, 'draft')
        self.assertTrue(flow.active)
        self.assertEqual(flow.user_id, self.env.user)
        self.assertEqual(flow.company_id, self.env.company)

    def test_compute_response_done_count(self):
        flow = self._create_flow()
        template = self._create_template()
        self.assertEqual(flow.response_done_count, 0)
        self._create_response(flow, template, with_lines=False)
        self._create_response(flow, template, with_lines=False)
        flow._compute_response_done_count()
        self.assertEqual(flow.response_done_count, 2)

    def test_number_to_word(self):
        flow = self._create_flow()
        self.assertEqual(flow.number_to_word(1).lower(), 'one')
        self.assertEqual(flow.number_to_word(3).lower(), 'three')

    # -- account configuration ---------------------------------------------
    def test_account_details(self):
        details = self._create_flow().get_whatsapp_account_details
        self.assertEqual(details, {
            'cloud_token': 'test_token', 'account_uid': 'test_account',
            'phone_uid': 'test_phone', 'app_uid': 'test_app'})

    def test_account_details_missing_configuration(self):
        self.env.user.token = False
        with self.assertRaises(ValidationError):
            self._create_flow().get_whatsapp_account_details

    # -- screen JSON generation --------------------------------------------
    def test_create_screens_without_screens(self):
        self.assertEqual(self._create_flow().create_screens(), [])

    def test_create_screens_text_types(self):
        flow = self._create_flow()
        mapping = {'large_heading': 'TextHeading',
                   'small_heading': 'TextSubheading',
                   'caption': 'TextCaption', 'body': 'TextBody'}
        self._create_screen(flow, contents=[
            {'content_type': 'text', 'content_text_type': key, 'text': key}
            for key in mapping])
        children = self._children(flow.create_screens()[0])
        self.assertEqual([c['type'] for c in children[:4]],
                         list(mapping.values()))
        self.assertEqual([c['text'] for c in children[:4]], list(mapping))

    def test_create_screens_text_answers(self):
        flow = self._create_flow()
        screen = self._create_screen(flow, contents=[
            {'content_type': 'text_answer', 'label': 'Name',
             'content_text_answer_type': 'short_answer',
             'shot_answer_type': 'email', 'instructions': 'Your email'},
            {'content_type': 'text_answer', 'label': 'Notes',
             'content_text_answer_type': 'paragraph', 'required': False},
            {'content_type': 'text_answer', 'label': 'Birthday',
             'content_text_answer_type': 'date_picker'},
        ])
        children = self._children(flow.create_screens()[0])
        text_input, text_area, date_picker = children[:3]
        self.assertEqual(text_input['type'], 'TextInput')
        self.assertEqual(text_input['input-type'], 'email')
        self.assertEqual(text_input['helper-text'], 'Your email')
        self.assertTrue(text_input['required'])
        self.assertEqual(text_area['type'], 'TextArea')
        self.assertFalse(text_area['required'])
        self.assertEqual(text_area['helper-text'], ' ')
        self.assertEqual(date_picker['type'], 'DatePicker')
        # every answer gets its own payload key stored on the content
        self.assertEqual(screen.content_ids.mapped('input_key'), [
            'screen_0_TextInput_0', 'screen_0_TextInput_1',
            'screen_0_TextInput_2'])

    def test_create_screens_selection_types(self):
        flow = self._create_flow()
        options = [(0, 0, {'options': 'A'}), (0, 0, {'options': 'B'})]
        self._create_screen(flow, contents=[
            {'content_type': 'selection', 'label': 'Single',
             'content_selection_type': 'single_choice', 'option_ids': options},
            {'content_type': 'selection', 'label': 'Multi',
             'content_selection_type': 'multiple_choice',
             'option_ids': options},
            {'content_type': 'selection', 'label': 'Drop',
             'content_selection_type': 'drop_down', 'option_ids': options},
        ])
        screen_json = flow.create_screens()[0]
        single, multi, drop = self._children(screen_json)[:3]
        self.assertEqual(single['type'], 'RadioButtonsGroup')
        self.assertEqual(multi['type'], 'CheckboxGroup')
        self.assertEqual(drop['type'], 'Dropdown')
        self.assertEqual([o['title'] for o in single['data-source']],
                         ['A', 'B'])
        # checkbox answers are arrays, everything else is a string
        self.assertEqual(screen_json['data'], {})
        payload = self._children(screen_json)[-1]['on-click-action']['payload']
        self.assertEqual(len(payload), 3)

    def test_create_screens_navigation_and_completion(self):
        flow = self._flow_with_content()
        first, second = flow.create_screens()
        self.assertEqual(first['id'].lower(), 'screen_one')
        self.assertEqual(second['id'].lower(), 'screen_two')
        footer = self._children(first)[-1]
        self.assertEqual(footer['type'], 'Footer')
        self.assertEqual(footer['label'], 'Next')
        action = footer['on-click-action']
        self.assertEqual(action['name'], 'navigate')
        self.assertEqual(action['next']['name'], 'SCREEN_TWO')
        self.assertIn('screen_0_TextInput_0', action['payload'])
        self.assertNotIn('terminal', first)
        # the last screen completes the flow and forwards earlier answers
        last_footer = self._children(second)[-1]
        self.assertEqual(last_footer['label'], 'Done')
        self.assertEqual(last_footer['on-click-action']['name'], 'complete')
        self.assertTrue(second['terminal'])
        self.assertTrue(second['success'])
        self.assertIn('screen_0_TextInput_0', second['data'])
        self.assertEqual(
            last_footer['on-click-action']['payload']['screen_0_TextInput_0'],
            '${data.screen_0_TextInput_0}')

    def test_create_screens_media(self):
        flow = self._create_flow()
        png = (b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4'
               b'z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==')
        self._create_screen(flow, contents=[
            {'content_type': 'media', 'image_1920': png}])
        image_node = self._children(flow.create_screens()[0])[0]
        self.assertEqual(image_node['type'], 'Image')
        self.assertEqual(image_node['scale-type'], 'contain')
        self.assertTrue(image_node['src'])

    # -- state transitions with the Meta API mocked -------------------------
    def test_confirm_requires_screens(self):
        with self.assertRaises(ValidationError):
            self._create_flow().action_confirm_flows()

    @patch(FLOWS_MODULE + '.open', new_callable=mock_open, create=True)
    @patch(FLOWS_MODULE + '.requests.post')
    def test_confirm_flow(self, mock_post, _mock_open):
        mock_post.return_value = fake_response(200, {'id': '12345'})
        flow = self._flow_with_content()
        flow.action_confirm_flows()
        self.assertEqual(flow.flow_id, '12345')
        self.assertEqual(flow.state, 'confirmed')
        # the flow is created first and its JSON uploaded second
        self.assertEqual(mock_post.call_count, 2)
        create_call, upload_call = mock_post.call_args_list
        self.assertIn('/test_account/flows', create_call.args[0])
        self.assertEqual(create_call.kwargs['json']['name'], flow.flow_name)
        self.assertEqual(
            create_call.kwargs['headers']['Authorization'], 'Bearer test_token')
        self.assertIn('/12345/assets', upload_call.args[0])

    @patch(FLOWS_MODULE + '.requests.post')
    def test_confirm_flow_invalid_token(self, mock_post):
        mock_post.return_value = fake_response(400, api_error(code=190))
        flow = self._flow_with_content()
        with self.assertRaisesRegex(ValidationError, 'Invalid access token'):
            flow.action_confirm_flows()
        self.assertEqual(flow.state, 'draft')

    @patch(FLOWS_MODULE + '.requests.post')
    def test_confirm_flow_api_error(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(message='Bad flow'))
        flow = self._flow_with_content()
        with self.assertRaisesRegex(ValidationError, 'Bad flow'):
            flow.action_confirm_flows()
        self.assertEqual(flow.state, 'draft')

    @patch(FLOWS_MODULE + '.open', new_callable=mock_open, create=True)
    @patch(FLOWS_MODULE + '.requests.post')
    def test_update_created_flow_upload_error(self, mock_post, _mock_open):
        mock_post.return_value = fake_response(
            400, api_error(message='Invalid JSON'))
        flow = self._flow_with_content()
        flow.flow_id = '1'
        with self.assertRaisesRegex(ValidationError, 'Invalid JSON'):
            flow.update_created_flow()

    @patch(FLOWS_MODULE + '.open', new_callable=mock_open, create=True)
    @patch(FLOWS_MODULE + '.requests.post')
    def test_update_created_flow_uploads_screens(self, mock_post, _mock_open):
        mock_post.return_value = fake_response(200, {})
        flow = self._flow_with_content()
        flow.flow_id = '55'
        flow.update_created_flow()
        written = ''.join(
            call.args[0] for call in _mock_open().write.call_args_list)
        data = json.loads(written)
        self.assertEqual(data['version'], '7.3')
        self.assertEqual(len(data['screens']), 2)

    @patch(FLOWS_MODULE + '.requests.post')
    def test_publish_flow(self, mock_post):
        mock_post.return_value = fake_response(200, {'success': True})
        flow = self._create_flow(flow_id='77', state='confirmed')
        flow.action_publish_flows()
        self.assertEqual(flow.state, 'published')
        self.assertIn('/77/publish', mock_post.call_args.args[0])

    @patch(FLOWS_MODULE + '.requests.post')
    def test_publish_flow_error(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(message='Not valid'))
        flow = self._create_flow(flow_id='77', state='confirmed')
        with self.assertRaisesRegex(ValidationError, 'Not valid'):
            flow.action_publish_flows()
        self.assertEqual(flow.state, 'confirmed')

    @patch(FLOWS_MODULE + '.requests.post')
    def test_deprecate_flow(self, mock_post):
        mock_post.return_value = fake_response(200, {'success': True})
        flow = self._create_flow(flow_id='88', state='published')
        flow.action_deprecate_flow()
        self.assertEqual(flow.state, 'deprecate')
        self.assertFalse(flow.active)

    @patch(FLOWS_MODULE + '.requests.post')
    def test_deprecate_flow_error(self, mock_post):
        mock_post.return_value = fake_response(
            400, api_error(message='Cannot deprecate'))
        flow = self._create_flow(flow_id='88', state='published')
        with self.assertRaisesRegex(ValidationError, 'Cannot deprecate'):
            flow.action_deprecate_flow()
        self.assertEqual(flow.state, 'published')
        self.assertTrue(flow.active)

    @patch(FLOWS_MODULE + '.requests.get')
    def test_preview_flow(self, mock_get):
        mock_get.return_value = fake_response(
            200, {'preview': {'preview_url': 'https://preview.example/x'}})
        action = self._create_flow(flow_id='99').action_preview_flow()
        self.assertEqual(action['tag'], 'flow_preview_tag')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['params']['url'], 'https://preview.example/x')

    @patch(FLOWS_MODULE + '.requests.get')
    def test_preview_flow_without_url(self, mock_get):
        mock_get.return_value = fake_response(200, {})
        action = self._create_flow(flow_id='99').action_preview_flow()
        self.assertEqual(action['params']['url'], '')

    # -- deletion -----------------------------------------------------------
    def test_unlink_draft_flow(self):
        flow = self._create_flow()
        flow.unlink()
        self.assertFalse(flow.exists())

    def test_unlink_published_flow_is_blocked(self):
        flow = self._create_flow(state='published')
        with self.assertRaises(ValidationError):
            flow.unlink()
        self.assertTrue(flow.exists())

    @patch(FLOWS_MODULE + '.requests.delete')
    def test_unlink_confirmed_flow_deletes_remote_flow(self, mock_delete):
        mock_delete.return_value = fake_response(200, {'success': True})
        flow = self._create_flow(state='confirmed', flow_id='42')
        flow.unlink()
        self.assertFalse(flow.exists())
        self.assertIn('/42', mock_delete.call_args.args[0])

    @patch(FLOWS_MODULE + '.requests.delete')
    def test_unlink_confirmed_flow_remote_error(self, mock_delete):
        mock_delete.return_value = fake_response(
            400, api_error(message='Remote refused'))
        flow = self._create_flow(state='confirmed', flow_id='42')
        with self.assertRaisesRegex(ValidationError, 'Remote refused'):
            flow.unlink()
        self.assertTrue(flow.exists())

    # -- actions ------------------------------------------------------------
    def test_action_analysis_flow(self):
        flow = self._create_flow()
        action = flow.action_analysis_flow()
        self.assertEqual(action['tag'], 'flow_analysis_tag')
        self.assertEqual(action['target'], 'fullscreen')
        self.assertEqual(action['context']['active_id'], flow.id)

    def test_action_flows_user_input_completed(self):
        flow = self._create_flow()
        action = flow.action_flows_user_input_completed()
        self.assertEqual(action['res_model'], 'flows.user.response')
        self.assertEqual(action['context']['search_default_flows_id'], flow.id)

    # -- analysis data and report ------------------------------------------
    def test_send_data_without_responses(self):
        flow = self._flow_with_content()
        data = flow.send_data()
        self.assertEqual(data['flow_name'], flow.name)
        self.assertEqual(data['response_count'], 0)
        self.assertEqual(data['leads_generated'], 0)
        # one text answer and one selection are countable labels
        self.assertEqual(data['label_count'], 2)
        self.assertEqual([s['screen_name'] for s in data['screens']],
                         ['Details', 'Choice'])
        # text-only contents are not part of the analysis
        self.assertEqual(len(data['screens'][0]['contents']), 1)

    def test_send_data_groups_responses_by_label(self):
        flow = self._flow_with_content()
        template = self._create_template()
        response = self._create_response(flow, template)
        data = flow.send_data()
        self.assertEqual(data['response_count'], 1)
        content = data['screens'][0]['contents'][0]
        self.assertEqual(content['label'], 'Name')
        self.assertEqual(len(content['user_responses']), 1)
        line = content['user_responses'][0]
        self.assertEqual(line['user_input'], 'John')
        self.assertEqual(line['partner'], 'Flow Customer')
        self.assertEqual(line['whatsapp_number'], '919999999999')
        self.assertEqual(line['response_id'], response.id)
        self.assertEqual(data['screens'][1]['contents'][0]['user_responses'], [])

    def test_get_xlsx_report(self):
        flow = self._flow_with_content()
        template = self._create_template()
        self._create_response(flow, template)
        payload = {'data': flow.send_data()}
        for data in (payload, json.dumps(payload)):
            response = MagicMock()
            flow.get_xlsx_report(data, response)
            written = response.stream.write.call_args.args[0]
            # an .xlsx file is a zip archive
            self.assertEqual(written[:2], b'PK')

    def test_get_xlsx_report_empty_data(self):
        response = MagicMock()
        self._create_flow().get_xlsx_report({}, response)
        self.assertEqual(response.stream.write.call_args.args[0][:2], b'PK')
