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
from odoo.tests import common

class TestYoutubeChannel(common.TransactionCase):
    """
    Test cases for 'youtube.channel' model, covering channel management, 
    connectivity states, and account integration.
    """

    def setUp(self):
        """
        Setup test environment for YouTube channel tests, including 
        active accounts.
        """
        super(TestYoutubeChannel, self).setUp()
        self.youtube_account = self.env['youtube.account'].create({
            'name': 'Test YouTube Account',
            'client_number': 'test_client_id',
            'client_secret': 'test_client_secret',
            'state': 'sync',
            'access_token': 'test_access_token',
            'company_id': self.env.company.id,
        })

        self.youtube_channel = self.env['youtube.channel'].create({
            'name': 'Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'test_channel_123',
            'youtube_etag': 'test_etag_456',
            'customUrl': 'test_custom_url',
            'is_active': True,
            'company_id': self.env.company.id,
        })

    def test_youtube_channel_creation(self):
        """
        Test the successful creation and attribute validation of a YouTube channel.
        """
        self.assertEqual(self.youtube_channel.name, 'Test Channel')
        self.assertEqual(self.youtube_channel.youtube_number, 'test_channel_123')
        self.assertTrue(self.youtube_channel.is_active)

    def test_get_connected_channels(self):
        """
        Test the RPC method that retrieves all actively connected YouTube channels.
        """
        self.env['youtube.channel'].create({
            'name': 'Second Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'test_channel_456',
            'youtube_etag': 'test_etag_789',
            'customUrl': 'test_custom_url_2',
            'is_active': True,
            'company_id': self.env.company.id,
        })

        connected = self.env['youtube.channel'].get_connected_channels()
        self.assertGreaterEqual(len(connected), 2)
        channel_names = [ch['name'] for ch in connected]
        self.assertIn('Test Channel', channel_names)
        self.assertIn('Second Channel', channel_names)

    def test_get_connected_channels_only_synced(self):
        """
        Test that only channels with synchronized accounts are considered connected.
        """
        unsynced_account = self.env['youtube.account'].create({
            'name': 'Unsynced Account',
            'client_number': 'unsynced_client',
            'client_secret': 'unsynced_secret',
            'state': 'new',
            'company_id': self.env.company.id,
        })

        unsynced_channel = self.env['youtube.channel'].create({
            'name': 'Unsynced Channel',
            'youtube_account_id': unsynced_account.id,
            'youtube_number': 'unsynced_channel_123',
            'youtube_etag': 'unsynced_etag',
            'customUrl': 'unsynced_url',
            'is_active': False,
            'company_id': self.env.company.id,
        })

        connected = self.env['youtube.channel'].get_connected_channels()
        channel_ids = [ch['id'] for ch in connected]
        self.assertIn(self.youtube_channel.id, channel_ids)
        self.assertNotIn(unsynced_channel.id, channel_ids)

    def test_set_default_account_from_channel(self):
        """
        Test setting the global default YouTube account based on a specific channel.
        """
        result = self.env['youtube.channel'].set_default_account_from_channel(
            self.youtube_channel.id
        )
        self.assertTrue(result)
        default_account_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_youtube_account.default_youtube_account_id'
        )
        self.assertEqual(int(default_account_id), self.youtube_account.id)

    def test_set_default_account_invalid_channel(self):
        """
        Test the robust handling when trying to set a default account for an invalid channel.
        """
        result = self.env['youtube.channel'].set_default_account_from_channel(99999)
        self.assertTrue(result)

    def test_channel_account_relationship(self):
        """
        Test the relational integrity between channels and their parent YouTube accounts.
        """
        self.assertEqual(self.youtube_channel.youtube_account_id.id, self.youtube_account.id)
        self.assertIn(self.youtube_channel, self.youtube_account.channel_ids)

    def test_channel_active_inactive(self):
        """
        Test toggling the activation status of a YouTube channel.
        """
        self.youtube_channel.is_active = False
        self.assertFalse(self.youtube_channel.is_active)
        self.youtube_channel.is_active = True
        self.assertTrue(self.youtube_channel.is_active)

    def test_channel_company_default(self):
        """
        Test the automated assignment of the current company to a new channel.
        """
        channel = self.env['youtube.channel'].create({
            'name': 'Company Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'company_channel_123',
            'youtube_etag': 'company_etag',
            'customUrl': 'company_url',
        })
        self.assertEqual(channel.company_id, self.env.company)

    def test_multiple_channels_same_account(self):
        """
        Test the support for linking multiple channels to the same YouTube account.
        """
        channel2 = self.env['youtube.channel'].create({
            'name': 'Second Channel Same Account',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_789',
            'youtube_etag': 'etag_789',
            'customUrl': 'url_789',
        })

        channels = self.env['youtube.channel'].search([
            ('youtube_account_id', '=', self.youtube_account.id)
        ])
        self.assertGreaterEqual(len(channels), 2)
        self.assertIn(self.youtube_channel, channels)
        self.assertIn(channel2, channels)
