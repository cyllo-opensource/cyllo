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
from datetime import timedelta
from unittest.mock import patch, MagicMock
from odoo import fields
from odoo.tests.common import TransactionCase

class TestCylloOfficeConnector(TransactionCase):
    """
    Test cases for the Office 365 Connector, covering contact synchronization,
    To-Do task management, and API lifecycle.
    """

    def setUp(self):
        """
        Setup test environment for Office 365 Connector tests.
        """
        super(TestCylloOfficeConnector, self).setUp()
        self.Connector = self.env['cyllo.office.connector']
        self.Partner = self.env['res.partner']
        self.Activity = self.env['mail.activity']
        self.ConnectorLine = self.env['cyllo.office.connector.line']
        self.company = self.env.user.company_id
        
        self.connector = self.Connector.create({
            'name': 'Test Connector',
            'client_number': 'test_client_id',
            'client_secrets': 'test_client_secret',
            'access_token': 'test_access_token',
            'access_refresh_token': 'test_refresh_token',
            'company_id': self.company.id,
            'onedrive_token_validity': fields.Datetime.now() + timedelta(hours=1)
        })

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_sync_contact_success(self, mock_requests):
        """
        Test successful contact synchronization subscription with Office 365.
        """
        # Mock responses for subscription creation
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'sub_id_123'}
        mock_requests.post.return_value = mock_response

        # Execute
        self.connector.action_sync_contact()

        # Verify
        self.assertEqual(self.connector.contact_create_subscription_number, 'sub_id_123')
        self.assertEqual(self.connector.contact_update_subscription_number, 'sub_id_123')
        self.assertEqual(self.connector.contact_delete_subscription_number, 'sub_id_123')
        self.assertTrue(self.connector.contact_synced)
        
        # Verify config parameters
        param_conn_id = self.env['ir.config_parameter'].sudo().get_param('cyllo_office_365_connector.contact_office_connector_id')
        self.assertEqual(int(param_conn_id), self.connector.id)

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_unsync_contact(self, mock_requests):
        """
        Test the process of unsynchronizing contacts from Office 365.
        """
        # Setup initial state
        self.connector.contact_create_subscription_number = 'sub_id_1'
        self.connector.contact_delete_subscription_number = 'sub_id_2'
        self.connector.contact_update_subscription_number = 'sub_id_3'
        self.connector.contact_synced_expiration_date = fields.Datetime.now() + timedelta(days=1)
        
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_requests.delete.return_value = mock_response

        # Execute
        self.connector.action_unsync_contact()

        # Verify
        self.assertFalse(self.connector.contact_create_subscription_number)
        self.assertFalse(self.connector.contact_synced)

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_get_office365_contacts(self, mock_requests):
        """
        Test importing contacts from Office 365 into Odoo partners.
        """
        # Mock get contacts response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [{
                'id': 'contact_123',
                'displayName': 'John Doe',
                'mobilePhone': '1234567890',
                'emailAddresses': [{'address': 'john@example.com'}],
                'homeAddress': {
                    'street': '123 Main St',
                    'city': 'City',
                    'countryOrRegion': 'Country',
                    'postalCode': '12345'
                },
                'personalNotes': 'Notes'
            }]
        }
        mock_requests.get.return_value = mock_response

        # Execute
        res = self.connector.action_get_office365_contacts()

        # Verify
        self.assertEqual(res['params']['type'], 'success')
        
        # Check partner creation
        partner = self.Partner.search([('name', '=', 'John Doe')], limit=1)
        self.assertTrue(partner)
        self.assertEqual(partner.email, 'john@example.com')
        
        # Check connector line
        line = self.ConnectorLine.search([
            ('office_365_identifier', '=', 'contact_123'),
            ('type', '=', 'partner')
        ])
        self.assertTrue(line)
        self.assertEqual(line.partner_id, partner)

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_export_contacts(self, mock_requests):
        """
        Test exporting Odoo partners to Office 365 contacts.
        """
        # Create a partner to export
        partner = self.Partner.create({'name': 'Export User', 'email': 'export@example.com'})
        
        # Mock post response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'new_contact_id_456'}
        mock_requests.post.return_value = mock_response

        # Execute
        res = self.connector.action_export_contacts()

        # Verify
        self.assertEqual(res['params']['type'], 'success')
        self.assertEqual(partner.office_365_identifier, 'new_contact_id_456')
        
        # Check connector line for the specific partner
        line = self.ConnectorLine.search([
            ('office_365_identifier', '=', 'new_contact_id_456'),
            ('type', '=', 'partner'),
            ('partner_id', '=', partner.id)
        ])
        self.assertTrue(line)
        self.assertEqual(line.partner_id, partner)

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_import_to_do(self, mock_requests):
        """
        Test importing To-Do tasks from Office 365 as Odoo activities.
        """
        # Mock list response
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {'value': [{'id': 'list_1'}]}
        
        # Mock tasks response
        mock_task_resp = MagicMock()
        mock_task_resp.status_code = 200
        mock_task_resp.json.return_value = {'value': [{
            'id': 'task_1',
            'title': 'Test Task',
            'status': 'notStarted',
            'body': {'content': 'Task Body'},
            'dueDateTime': {'dateTime': '2025-01-01T12:00:00.0000000'}
        }]}
        
        # Configure side_effect for multiple get calls
        mock_requests.get.side_effect = [mock_list_resp, mock_task_resp]

        # Execute
        self.connector.action_import_to_do()

        # Verify Activity Creation
        activity = self.Activity.search([('summary', '=', 'Test Task')], limit=1)
        self.assertTrue(activity)
        self.assertTrue('Task Body' in str(activity.note))
        
        # Check connector line
        line = self.ConnectorLine.search([
            ('office_365_identifier', '=', 'task_1'),
            ('type', '=', 'activity')
        ])
        self.assertTrue(line)
        self.assertEqual(line.activity_id, activity)

    @patch('odoo.addons.cyllo_office_365_connector.models.cyllo_office_connector.requests')
    def test_action_export_to_do(self, mock_requests):
        """
        Test exporting Odoo activities as Office 365 To-Do tasks.
        """
        # Create activity
        activity = self.Activity.create({
            'summary': 'Export Task',
            'res_id': self.connector.company_id.partner_id.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'note': 'Export Note'
        })
        
        # Mock responses
        self.connector.task_list = 'list_123'
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'new_task_id_789'}
        mock_requests.post.return_value = mock_response

        # Execute
        res = self.connector.action_export_to_do()

        # Verify
        self.assertEqual(res['params']['type'], 'success')
        
        # Check connector line for the specific activity
        line = self.ConnectorLine.search([
            ('office_365_identifier', '=', 'new_task_id_789'),
            ('type', '=', 'activity'),
            ('activity_id', '=', activity.id)
        ])
        self.assertTrue(line)
        self.assertEqual(line.activity_id, activity)
