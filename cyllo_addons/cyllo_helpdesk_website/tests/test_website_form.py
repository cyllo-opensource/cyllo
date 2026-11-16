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
import base64
from unittest.mock import MagicMock, patch
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.addons.cyllo_helpdesk_website.controllers.website_form import WebsiteForm


_CONTROLLER = 'odoo.addons.cyllo_helpdesk_website.controllers.website_form'


# attribute 'getlist'" in test_insert_record_with_attachments)
class _Files(dict):
    def getlist(self, name):
        return [self[name]] if name in self else []

# Assigning `real_env.user = mock_user` DOES work in Odoo 17 (Environment.user
# is a lazy_property/non-data descriptor) but it mutates the SHARED test
# Environment created in setUpClass: env.company then derives from the mocked
# user and psycopg2 receives a MagicMock. Never write on the real env.
class _FakeEnv:

    def __init__(self, real_env, user=None):
        self._real_env = real_env
        if user is not None:
            self.user = user

    def __getattr__(self, name):
        return getattr(self._real_env, name)

    def __getitem__(self, model_name):
        return self._real_env[model_name]


class TestWebsiteForm(TransactionCase):
    """
    Test suite for the WebsiteForm controller in cyllo_helpdesk_website.
    Uses mock requests to unit-test the controller logic in a clean transaction.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Team = cls.env['helpdesk.team']
        cls.Ticket = cls.env['helpdesk.ticket']
        cls.Partner = cls.env['res.partner']
        cls.Model = cls.env['ir.model']

        # search([('use_website_ticket_creation', '=', True)], limit=1)
        # deterministically returns the test team. db1 contains other teams
        # (e.g. id 1) already enabled, which caused:
        #   - team(1) != team(149) in default_search
        #   - "ValidationError not raised" in no_default_team
        #   - values['team_id'] == 1 in insert_record_values_assignment
        # Writes are rolled back with the test transaction.
        cls.env['helpdesk.team'].search([]).write({
            'use_website_ticket_creation': False,
        })

        # Helpdesk teams
        cls.team_website = cls.Team.create({
            'name': 'Website Support Team',
            'use_website_ticket_creation': True,
        })
        cls.team_no_website = cls.Team.create({
            'name': 'Internal Support Team',
            'use_website_ticket_creation': False,
        })

        cls.partner = cls.Partner.create({
            'name': 'Test Form Partner',
            'email': 'form.test@example.com',
            'phone': '123456789',
        })

        cls.ticket = cls.Ticket.create({
            'name': 'Mock Ticket',
            'team_id': cls.team_website.id,
        })

        cls.ticket_model = cls.Model.search(
            [('model', '=', 'helpdesk.ticket')], limit=1)

    def setUp(self):
        super().setUp()
        self.controller = WebsiteForm()

    def _patch_request(self, mock_request):
        """Patch `request` inside the controller module."""
        return patch(_CONTROLLER + '.request', mock_request)

    # ── Test _get_website_ticket_team ─────────────────────────────

    def test_get_website_ticket_team_valid_id(self):
        """Passing a valid team_id should return that team."""
        values = {'team_id': str(self.team_website.id)}
        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env)
        with self._patch_request(mock_request):
            team = self.controller._get_website_ticket_team(values)
        self.assertEqual(team, self.team_website)

    def test_get_website_ticket_team_invalid_id(self):
        """Passing an invalid team_id or disabled team raises ValidationError."""
        values = {'team_id': '99999'}
        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env)
        with self._patch_request(mock_request), \
             self.assertRaises(ValidationError):
            self.controller._get_website_ticket_team(values)

        values = {'team_id': str(self.team_no_website.id)}
        with self._patch_request(mock_request), \
             self.assertRaises(ValidationError):
            self.controller._get_website_ticket_team(values)

    def test_get_website_ticket_team_default_search(self):
        """If no team_id, return the first team with website creation enabled."""
        values = {}
        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env)
        with self._patch_request(mock_request):
            team = self.controller._get_website_ticket_team(values)
        self.assertEqual(team, self.team_website)

    def test_get_website_ticket_team_no_default_team(self):
        """Raises ValidationError if no team has website creation enabled."""
        self.team_website.use_website_ticket_creation = False
        values = {}
        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env)
        with self._patch_request(mock_request), \
             self.assertRaises(ValidationError):
            self.controller._get_website_ticket_team(values)

    # ── Test _get_or_create_partner ───────────────────────────────

    def test_get_or_create_partner_logged_in(self):
        """If a user is logged in, return their partner_id."""
        mock_user = MagicMock()
        mock_user._is_public.return_value = False
        mock_user.partner_id = self.partner

        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env, user=mock_user)

        values = {}
        with self._patch_request(mock_request):
            partner = self.controller._get_or_create_partner(values)
        self.assertEqual(partner, self.partner)

    def test_get_or_create_partner_public_existing_email(self):
        """Public user with existing email updates partner name and phone."""
        mock_user = MagicMock()
        mock_user._is_public.return_value = True

        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env, user=mock_user)

        values = {
            'email': 'form.test@example.com',
            'phone': '987654321',
            'partner_name': 'Updated Form Partner Name',
        }
        with self._patch_request(mock_request):
            partner = self.controller._get_or_create_partner(values)
        self.assertEqual(partner, self.partner)
        self.assertEqual(partner.name, 'Updated Form Partner Name')
        self.assertEqual(partner.phone, '987654321')

    def test_get_or_create_partner_public_new_email(self):
        """Public user with new email creates a new partner record."""
        mock_user = MagicMock()
        mock_user._is_public.return_value = True

        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env, user=mock_user)

        values = {
            'email': 'new.visitor@example.com',
            'phone': '5551122',
            'partner_name': 'New Visitor',
        }
        with self._patch_request(mock_request):
            partner = self.controller._get_or_create_partner(values)
        self.assertNotEqual(partner, self.partner)
        self.assertEqual(partner.name, 'New Visitor')
        self.assertEqual(partner.email, 'new.visitor@example.com')
        self.assertEqual(partner.phone, '5551122')

    # ── Test insert_record custom logic ───────────────────────────

    @patch('odoo.addons.website.controllers.form.WebsiteForm.insert_record')
    def test_insert_record_values_assignment(self, mock_super_insert):
        """insert_record enriches values with team, customer, source, subject."""
        mock_super_insert.return_value = self.ticket.id

        mock_user = MagicMock()
        mock_user._is_public.return_value = False
        mock_user.partner_id = self.partner

        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env, user=mock_user)
        mock_request.httprequest = MagicMock()
        mock_request.httprequest.files = {}

        values = {
            'email': 'test@example.com',
            'description': 'Help desk ticket description text',
        }

        with self._patch_request(mock_request):
            self.controller.insert_record(
                mock_request, self.ticket_model, values, custom=None)

        self.assertEqual(values['team_id'], self.team_website.id)
        self.assertEqual(values['customer_id'], self.partner.id)
        self.assertEqual(values['source'], 'website')
        self.assertEqual(values['name'], 'Website Ticket')

    @patch('odoo.addons.website.controllers.form.WebsiteForm.insert_record')
    def test_insert_record_with_attachments(self, mock_super_insert):
        """insert_record handles file uploads and creates ir.attachment records."""
        mock_super_insert.return_value = self.ticket.id

        mock_user = MagicMock()
        mock_user._is_public.return_value = False
        mock_user.partner_id = self.partner

        mock_file = MagicMock()
        mock_file.filename = 'screenshot.png'
        mock_file.read.return_value = b'fake_image_binary_data'

        mock_request = MagicMock()
        mock_request.env = _FakeEnv(self.env, user=mock_user)
        mock_request.httprequest = MagicMock()
        mock_request.httprequest.files = _Files({'attachment_ids': mock_file})

        values = {
            'name': 'Ticket with screenshot',
            'email': 'test@example.com',
            'description': 'Details here',
        }

        with self._patch_request(mock_request):
            self.controller.insert_record(
                mock_request, self.ticket_model, values, custom=None)

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'helpdesk.ticket'),
            ('res_id', '=', self.ticket.id),
            ('name', '=', 'screenshot.png')
        ])
        self.assertTrue(attachment)
        self.assertEqual(
            base64.b64decode(attachment.datas), b'fake_image_binary_data')
        self.assertIn(attachment, self.ticket.attachment_ids)