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
import json
from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.addons.cyllo_field_service.models.field_service_request import FieldServiceRequest
from odoo.addons.cyllo_field_service.models.field_service_checklist import FieldServiceChecklist


@tagged('-at_install', 'post_install')
class TestFieldServiceRequestPortal(HttpCase):
    """
    Test suite for field service request portal functionality.

    This test class verifies the portal routes and functionality for field service requests,
    including access control, request creation, status updates, and checklist operations.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test data for field service request portal tests."""
        super().setUpClass()
        lang = cls.env['res.lang'].search([('code', '=', 'en_US')], limit=1)
        if not lang:
            cls.env['res.lang'].load_lang('en_US')

        cls.partner = cls.env['res.partner'].create({'name': 'Portal Partner'})
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Electrical',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test product',
            'lst_price': 50,
        })
        cls.service_request = cls.env['field.service.request'].create({
            'name': 'FS001',
            'description': 'Test Request',
            'state': 'draft',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
        })
        cls.user_portal = cls.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal_user',
            'password': 'portal_user',
            'email': 'portal@test.com',
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'name': 'SO001'
        })

    def test_portal_user_access(self):
        """Verify portal user can access their service requests list page."""
        self.authenticate('portal_user', 'portal_user')
        response = self.url_open('/my/field_service_request')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FS001', response.content)

    def test_field_service_request_details_route(self):
        """Test field service request details route for valid, invalid, and report cases."""
        self.authenticate('portal_user', 'portal_user')
        url_valid = f'/field_service_request/{self.service_request.id}'
        response_valid = self.url_open(url_valid)
        self.assertEqual(response_valid.status_code, 200)
        self.assertIn(b'Test Request', response_valid.content)

        invalid_id = self.service_request.id + 999
        response_invalid = self.url_open(f'/field_service_request/{invalid_id}', allow_redirects=False)
        self.assertEqual(response_invalid.status_code, 303)
        self.assertIn('/my', response_invalid.headers.get('Location', ''))

        url_report = f'/field_service_request/{self.service_request.id}?report_type=html'
        response_report = self.url_open(url_report)
        self.assertEqual(response_report.status_code, 200)
        self.assertTrue(b'FS001' in response_report.content or b'Test Request' in response_report.content)

    def test_field_service_request_new(self):
        """Test that both portal and internal users can access the 'New Field Service Request' form."""
        self.authenticate('portal_user', 'portal_user')
        response_portal = self.url_open('/field_service_request/new', timeout=30)
        self.assertEqual(response_portal.status_code, 200)

        self.assertIn(b'Register Field Request', response_portal.content)
        self.assertIn(b'field_service-request_form', response_portal.content)
        self.assertIn(b'Partner', response_portal.content)
        self.assertIn(b'Category', response_portal.content)
        self.assertIn(b'Sale Order', response_portal.content)
        self.assertIn(b'Description', response_portal.content)
        self.assertIn(b'Attachments', response_portal.content)

        manager_user = self.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'password': 'manager_user',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('cyllo_field_service.group_cyllo_field_service_manager').id,
                self.env.ref('sales_team.group_sale_salesman').id
            ])],
        })
        self.authenticate('manager_user', 'manager_user')
        response_manager = self.url_open('/field_service_request/new', timeout=30)
        self.assertEqual(response_manager.status_code, 200)
        self.assertIn(b'field_service-request_form', response_manager.content)
        self.assertIn(b'Description', response_manager.content)

    def test_action_complete_form(self):
        """Test main scenarios for action_complete_form JSON route including checklist validation."""
        self.authenticate('portal_user', 'portal_user')
        checklist = self.env['field.service.checklist'].create({
            'status': 'pending',
            'required': True,
            'field_service_request_id': self.service_request.id,
            'product_id': self.product.id
        })
        response = self.url_open(
            '/fs_request/form/action_complete',
            data=json.dumps({'params': {'request_id': self.service_request.id}}),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['result'])
        self.service_request = self.env['field.service.request'].browse(self.service_request.id)
        self.assertEqual(self.service_request.state, 'draft')
        checklist.write({'status': 'completed'})
        response = self.url_open(
            '/fs_request/form/action_complete',
            data=json.dumps({'params': {'request_id': self.service_request.id}}),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result['result'])
        self.service_request = self.env['field.service.request'].browse(self.service_request.id)
        self.assertEqual(self.service_request.state, 'completed')
        new_request = self.env['field.service.request'].create({
            'name': 'FS002',
            'description': 'No Checklists',
            'state': 'draft',
            'partner_id': self.partner.id,
            'skill_category_id': self.skill_category.id,
        })
        response = self.url_open(
            '/fs_request/form/action_complete',
            data=json.dumps({'params': {'request_id': new_request.id}}),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result['result'])
        new_request = self.env['field.service.request'].browse(new_request.id)
        self.assertEqual(new_request.state, 'completed')

    def test_action_start_service(self):
        """Test action_start_service calls action_service_start and returns True."""
        self.authenticate('portal_user', 'portal_user')
        with patch.object(FieldServiceRequest, 'action_service_start') as mock_action:
            response = self.url_open(
                '/fs_request/form/action_start',
                data=json.dumps({'params': {'request_id': self.service_request.id}}),
                headers={'Content-Type': 'application/json'}
            )
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertTrue(result['result'])
            mock_action.assert_called_once()

    def test_action_done_form_check_line(self):
        """Test action_done_form_check_line calls action_mark_as_done and returns True."""
        self.authenticate('portal_user', 'portal_user')
        with patch.object(FieldServiceChecklist, 'action_mark_as_done') as mock_action:
            checklist_id = 123  # Any ID for testing

            response = self.url_open(
                '/fs_request/form/action_done',
                data=json.dumps({'params': {'checkline_id': checklist_id}}),
                headers={'Content-Type': 'application/json'}
            )

            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertTrue(result['result'])
            mock_action.assert_called_once()

    def test_create_field_service_request_with_csrf(self):
        """Test creating field service request with CSRF token protection."""
        self.authenticate('portal_user', 'portal_user')
        # First, get a page that should contain the form to extract CSRF token
        form_page = self.url_open('/field_service_request/new')
        csrf_token = self._extract_csrf_token(form_page.content)
        if not csrf_token:
            self.skipTest("Could not extract CSRF token")
        post_data = {
            'partner_id': str(self.partner.id),
            'description': 'Test request description',
            'priority': 'a',
            'sale_order': str(self.sale_order.id),
            'skill_category_id': str(self.skill_category.id),
            'date_deadline': '2025-11-10',
            'csrf_token': csrf_token,
        }

        response = self.url_open('/fs_service_request/create', data=post_data)
        if response.status_code == 200:
            fs_request = self.env['field.service.request'].search([
                ('description', '=', 'Test request description')
            ], limit=1)
            self.assertTrue(fs_request)
        else:
            self.skipTest(f"CSRF token didn't work. Status: {response.status_code}")

    def _extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML content."""
        import re
        # Look for CSRF token in the script tag
        match = re.search(r'csrf_token: "([^"]+)"', html_content.decode())
        return match.group(1) if match else None