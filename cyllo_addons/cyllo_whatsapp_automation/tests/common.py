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
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

FLOWS_MODULE = 'odoo.addons.cyllo_whatsapp_automation.models.whatsapp_flows'
TEMPLATE_MODULE = 'odoo.addons.cyllo_whatsapp_automation.models.whatsapp_template'


def fake_response(status=200, payload=None):
    """Build a stand-in for a `requests` response."""
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload if payload is not None else {}
    return response


def api_error(code=100, subcode=0, message='Boom', title='Title',
              user_msg='User message'):
    """Build the error body returned by the Meta Graph API."""
    return {'error': {
        'code': code, 'error_subcode': subcode, 'message': message,
        'error_user_title': title, 'error_user_msg': user_msg}}


class WhatsappAutomationCommon(TransactionCase):
    """Shared fixtures for the WhatsApp automation tests.

    Every external call (Meta Graph API) is expected to be mocked by the
    individual test; nothing in this module touches the network.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write({
            'token': 'test_token',
            'account_uid': 'test_account',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Flow Customer',
            'whatsapp_number': '919999999999',
        })
        cls.partner_model = cls.env.ref('base.model_res_partner')
        cls.product = cls.env['product.product'].create({
            'name': 'Flow Product',
            'list_price': 25.0,
            'description_sale': 'A product sold from WhatsApp',
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Second Product',
            'list_price': 10.0,
        })

    # -- builders -----------------------------------------------------------
    def _create_flow(self, name='Test Flow', **vals):
        return self.env['whatsapp.flows'].create({'name': name, **vals})

    def _create_screen(self, flow, name='Screen 1', button='Next', contents=()):
        return self.env['whatsapp.flows.screens'].create({
            'name': name,
            'flow_id': flow.id,
            'button_name': button,
            'content_ids': [(0, 0, vals) for vals in contents],
        })

    def _create_template(self, name='Test Template', **vals):
        values = {
            'name': name,
            'template_name': name.lower().replace(' ', '_') + '_tpl',
            'model_id': self.partner_model.id,
            'body': 'Hello',
        }
        values.update(vals)
        return self.env['whatsapp.template'].create(values)

    def _create_response(self, flow, template, with_lines=True, **vals):
        response = self.env['flows.user.response'].create({
            'flows_id': flow.id,
            'template_id': template.id,
            'partner_id': self.partner.id,
            'number': self.partner.whatsapp_number,
            **vals,
        })
        if with_lines:
            screen = flow.screen_ids[:1]
            self.env['flows.user.response.line'].create([{
                'response_id': response.id,
                'field_label': 'Name',
                'user_input': 'John',
                'screen_id': screen.id,
                'response_key': 'screen_0_TextInput_0',
            }])
        return response

    def _flow_with_content(self):
        """A two screen flow: text + short answer, then a single choice."""
        flow = self._create_flow()
        self._create_screen(flow, 'Details', 'Next', [
            {'content_type': 'text', 'content_text_type': 'large_heading',
             'text': 'Welcome'},
            {'content_type': 'text_answer', 'label': 'Name',
             'content_text_answer_type': 'short_answer',
             'shot_answer_type': 'text'},
        ])
        self._create_screen(flow, 'Choice', 'Done', [
            {'content_type': 'selection', 'label': 'Colour',
             'content_selection_type': 'single_choice',
             'option_ids': [(0, 0, {'options': 'Red'}),
                            (0, 0, {'options': 'Blue'})]},
        ])
        return flow

    @staticmethod
    def _children(screen_json):
        return screen_json['layout']['children'][0]['children']
