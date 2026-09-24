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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch

class TestGoogleForm(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company_1 = cls.env['res.company'].create({'name': 'Company 1'})
        cls.company_2 = cls.env['res.company'].create({'name': 'Company 2'})
        cls.sales_user = cls.env['res.users'].create({
            'name': 'Sales Admin User',
            'login': 'sales_admin_test_user',
            'company_id': cls.company_1.id,
            'company_ids': [(4, cls.company_1.id), (4, cls.company_2.id)],
            'groups_id': [(4, cls.env.ref('sales_team.group_sale_manager').id), (4, cls.env.ref('base.group_user').id)]
        })
        cls.env.user.company_id = cls.company_1
        cls.env.user.company_ids = [(4, cls.company_1.id), (4, cls.company_2.id)]
        cls.form = cls.env['google.form'].with_company(cls.company_1).create({
            'name': 'Test Form',
            'company_id': cls.company_1.id,
        })
        # Give user Sales Administrator rights to bypass _check_sales_admin_access
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')
        cls.env.user.groups_id = [(4, group_sale_manager.id)]

    def test_form_creation(self):
        """Test form creation validations"""
        self.assertEqual(self.form.company_id, self.company_1)
        with self.assertRaises(UserError):
            test_env = self.env(user=self.sales_user, su=False)
            self.env['google.form'].with_env(test_env).with_company(self.company_1).create({
                'name': 'Another Form',
                'company_id': self.company_2.id,
            })

    def test_form_url_reset(self):
        """Test form_url is reset on specific writes"""
        self.form.with_context(skip_google_form_url_reset=True).write({
            'form_url': 'http://test.url',
            'google_form_id': '12345'
        })
        self.assertEqual(self.form.form_url, 'http://test.url')
        self.form.write({'name': 'Updated Test Form'})
        self.assertFalse(self.form.form_url)

    def test_refresh_access_token_missing_config(self):
        """Test refresh access token fails when config is missing"""
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('cyllo_google.refresh_token', False)
        with self.assertRaises(ValidationError):
            self.form.refresh_access_token()

    @patch('odoo.addons.cyllo_crm_google_form.models.google_form.requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful access token refresh"""
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('cyllo_google.refresh_token', 'test_refresh')
        params.set_param('cyllo_google.client_id', 'test_client')
        params.set_param('cyllo_google.client_secret', 'test_secret')
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'new_access_token'}
        token = self.form.refresh_access_token()
        self.assertEqual(token, 'new_access_token')

    @patch('odoo.addons.cyllo_crm_google_form.models.google_form.GoogleForm.refresh_access_token')
    @patch('odoo.addons.cyllo_crm_google_form.models.google_form.requests.post')
    def test_create_google_form(self, mock_post, mock_refresh):
        """Test creating google form through API"""
        mock_refresh.return_value = 'test_token'
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'formId': 'test_form_id',
            'responderUri': 'http://test.responder.uri'
        }
        self.form.create_google_form()
        self.assertEqual(self.form.google_form_id, 'test_form_id')
        self.assertEqual(self.form.form_url, 'http://test.responder.uri')
        
    @patch('odoo.addons.cyllo_crm_google_form.models.google_form.GoogleForm.refresh_access_token')
    @patch('odoo.addons.cyllo_crm_google_form.models.google_form.requests.get')
    def test_fetch_responses_create_leads(self, mock_get, mock_refresh):
        """Test fetching responses and creating leads"""
        mock_refresh.return_value = 'test_token'
        self.form.with_context(skip_google_form_url_reset=True).write({
            'google_form_id': 'test_form_id',
            'form_url': 'http://test.responder.uri'
        })
        mock_get_form = mock_get.return_value
        mock_get_form.status_code = 200
        mock_get_form.json.return_value = {
            "items": [
                {
                    "title": "Email",
                    "questionItem": {
                        "question": {"questionId": "q1"}
                    }
                }
            ]
        }
        
        # Need to side_effect to return different responses for different GET calls
        def get_side_effect(url, **kwargs):
            mock_resp = type('MockResp', (), {})()
            mock_resp.status_code = 200
            if 'responses' in url:
                mock_resp.json = lambda: {
                    "responses": [
                        {
                            "responseId": "r1",
                            "answers": {
                                "q1": {
                                    "textAnswers": {"answers": [{"value": "test@example.com"}]}
                                }
                            }
                        }
                    ]
                }
            else:
                mock_resp.json = lambda: mock_get_form.json()
            return mock_resp
            
        mock_get.side_effect = get_side_effect
        leads_before = self.env['crm.lead'].search_count([('company_id', '=', self.company_1.id)])
        self.form.fetch_responses_create_leads()
        leads_after = self.env['crm.lead'].search_count([('company_id', '=', self.company_1.id)])
        self.assertEqual(leads_after, leads_before + 1)
        lead = self.env['crm.lead'].search([('company_id', '=', self.company_1.id)], order='id desc', limit=1)
        self.assertEqual(lead.email_from, "test@example.com")
