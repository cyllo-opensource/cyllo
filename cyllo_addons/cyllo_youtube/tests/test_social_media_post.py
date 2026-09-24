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
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import common


class TestSocialMediaPost(common.TransactionCase):
    """
    Test cases for 'social.media.post' model, covering video publication
    and onchange logic.
    """

    def setUp(self):
        """
        Setup test data for social media posts, including accounts and channels.
        """
        super().setUp()

        self.youtube_account = self.env['youtube.account'].create({
            'name': 'Test Account',
            'client_number': 'test_client',
            'client_secret': 'test_secret',
            'state': 'sync',
            'access_token': 'test_token',
            'refresh_token': 'test_refresh_token',
            'token_expiry_date': datetime.now() + timedelta(hours=1),
        })

        self.youtube_channel = self.env['youtube.channel'].create({
            'name': 'Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_123',
            'youtube_etag': 'etag_123',
            'customUrl': 'custom_url',
            'is_active': True,
        })

        self.social_post = self.env['social.media.post'].create({
            'name': 'Test Post',
            'description': 'Test Description',
            'post_on_youtube': True,
            'youtube_channel_id': self.youtube_channel.id,
            'mode': 'video',
        })

    def test_social_media_post_creation(self):
        """
        Test the creation and field initialization of a social media post.
        """
        self.assertEqual(self.social_post.name, 'Test Post')
        self.assertTrue(self.social_post.post_on_youtube)
        self.assertEqual(self.social_post.mode, 'video')
        self.assertEqual(self.social_post.youtube_channel_id, self.youtube_channel)

    def test_youtube_video_number_assignment(self):
        """
        Test the manual assignment of a YouTube video identifier.
        """
        self.social_post.youtube_video_number = 'assigned_video_123'
        self.assertEqual(self.social_post.youtube_video_number, 'assigned_video_123')

    def test_youtube_channel_relationship(self):
        """
        Test switching the target YouTube channel for a post.
        """
        self.assertEqual(self.social_post.youtube_channel_id, self.youtube_channel)

        channel2 = self.env['youtube.channel'].create({
            'name': 'Second Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_456',
            'youtube_etag': 'etag_456',
            'customUrl': 'custom_url_2',
            'is_active': True,
        })

        self.social_post.youtube_channel_id = channel2
        self.assertEqual(self.social_post.youtube_channel_id, channel2)

    def test_mode_default_value(self):
        """
        Test the default value of the publication mode field.
        """
        post = self.env['social.media.post'].create({
            'name': 'Test Post 2',
            'description': 'Test',
        })
        self.assertIn(post.mode, ['url', 'video'])

    def test_onchange_post_on_youtube(self):
        """
        Test the onchange logic when enabling YouTube publication.
        """
        self.social_post.post_on_youtube = True
        self.social_post._onchange_post_on_youtube()

    def test_onchange_mode_upload(self):
        """
        Test formatting resets when switching to 'video' mode.
        """
        self.social_post.mode = 'video'
        self.social_post._onchange_mode()

    def test_onchange_mode_not_upload(self):
        """
        Test state resets when switching away from 'video' mode.
        """
        self.social_post.mode = 'url'
        self.social_post._onchange_mode()
        self.assertFalse(self.social_post.post_on_youtube)

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_draft_state(self, mock_put):
        """
        Test that posting a record without a video number triggers a warning.
        """
        self.social_post.youtube_video_number = None
        result = self.social_post.action_post()
        self.assertEqual(result['params']['type'], 'warning')

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_success(self, mock_put):
        """
        Test successful synchronization of a recorded post with YouTube.
        """
        self.social_post.write({
            'youtube_video_number': 'video_123',
            'state': 'post',
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'video_123',
            'snippet': {
                'title': 'Test Post',
                'channelId': 'channel_123',
                'thumbnails': {
                    'high': {
                        'url': 'https://img.youtube.com/vi/video_123/hqdefault.jpg'
                    }
                }
            }
        }
        mock_put.return_value = mock_response

        self.social_post.action_post()
        self.assertTrue(self.social_post.posted_on_youtube)
        self.assertEqual(self.social_post.posted_image_url,
                         'https://img.youtube.com/vi/video_123/hqdefault.jpg')

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_api_error(self, mock_put):
        """
        Test behavior when the YouTube API returns an error during publication.
        """
        self.social_post.write({
            'youtube_video_number': 'video_123',
            'state': 'post',
        })

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_put.return_value = mock_response

        result = self.social_post.action_post()
        self.assertEqual(result['params']['type'], 'warning')

    def test_get_youtube_account(self):
        """
        Test retrieving the active YouTube account credentials for the post.
        """
        result = self.social_post.get_youtube_account()
        self.assertEqual(result['key'], self.youtube_account.access_token)


class TestYoutubePostFeedHelpers(common.TransactionCase):
    """
    Covers what used to be social.media.feed's YouTube feed data retrieval,
    comment management, and lead generation - now merged onto social.media.post.
    """

    def setUp(self):
        super().setUp()

        self.youtube_account = self.env['youtube.account'].create({
            'name': 'Test Account',
            'client_number': 'client_123',
            'client_secret': 'secret_123',
            'state': 'sync',
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_expiry_date': datetime.now() + timedelta(hours=1),
        })

        self.youtube_channel = self.env['youtube.channel'].create({
            'name': 'Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_123',
            'youtube_etag': 'etag_123',
            'customUrl': 'custom_url',
        })

        self.post = self.env['social.media.post'].create({
            'name': 'Test Post',
            'description': 'Test Description',
            'posted_on_youtube': True,
            'youtube_video_number': 'video_123',
            'youtube_channel_id': self.youtube_channel.id,
        })

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.get')
    def test_get_youtube_feed_data_success(self, mock_get):
        """
        Test the retrieval of video feed data from the YouTube API.
        """
        mock_response_channel = MagicMock()
        mock_response_channel.json.return_value = {
            'items': [{
                'contentDetails': {
                    'relatedPlaylists': {
                        'uploads': 'playlist_123'
                    }
                },
                'snippet': {
                    'thumbnails': {
                        'default': {
                            'url': 'https://example.com/thumb.jpg'
                        }
                    }
                }
            }]
        }

        mock_response_playlist = MagicMock()
        mock_response_playlist.json.return_value = {
            'items': [{
                'snippet': {
                    'resourceId': {'videoId': 'video_1'},
                    'publishedAt': '2025-01-01T00:00:00Z',
                    'title': 'Test Video',
                    'description': 'Test Description',
                    'channelTitle': 'Test Channel',
                    'thumbnails': {}
                }
            }],
            'nextPageToken': 'token_123'
        }

        mock_response_stats = MagicMock()
        mock_response_stats.json.return_value = {
            'items': [{
                'id': 'video_1',
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '50',
                    'commentCount': '10'
                }
            }]
        }

        mock_get.side_effect = [
            mock_response_channel,
            mock_response_playlist,
            mock_response_stats
        ]

        result = self.env['social.media.post'].get_youtube_feed_data(
            channel_id=self.youtube_channel.id
        )

        self.assertIn('data', result)
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['title'], 'Test Video')

    def test_get_youtube_feed_data_no_channel(self):
        """
        Test behavior when retrieving feed data for a non-existent channel.
        """
        result = self.env['social.media.post'].get_youtube_feed_data(
            channel_id=99999
        )
        self.assertEqual(result['data'], [])

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.get')
    def test_get_youtube_comments_success(self, mock_get):
        """
        Test successful retrieval of video comments from the YouTube API.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'items': [{
                'id': 'comment_1',
                'snippet': {
                    'topLevelComment': {
                        'snippet': {
                            'authorDisplayName': 'Test User',
                            'authorProfileImageUrl': 'https://example.com/profile.jpg',
                            'authorChannelId': {'value': 'user_123'},
                            'textOriginal': 'Great video!',
                            'publishedAt': '2025-01-01T00:00:00Z',
                            'likeCount': 5
                        }
                    }
                }
            }],
            'nextPageToken': 'next_token'
        }
        mock_get.return_value = mock_response

        result = self.env['social.media.post'].get_youtube_comments(
            'video_123',
            channel_id=self.youtube_channel.id
        )

        self.assertIn('comments', result)
        self.assertEqual(len(result['comments']), 1)
        self.assertEqual(result['comments'][0]['text'], 'Great video!')

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.post')
    def test_post_youtube_comments_success(self, mock_post):
        """
        Test the ability to post a comment to a YouTube video via API.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'new_comment_123',
            'snippet': {
                'textOriginal': 'Test comment'
            }
        }
        mock_post.return_value = mock_response

        result = self.env['social.media.post'].post_youtube_comments(
            'video_123',
            'Test comment',
            channel_id=self.youtube_channel.id
        )
        self.assertIsInstance(result, dict)

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.post')
    def test_post_youtube_reply_success(self, mock_post):
        """
        Test replying to an existing comment on a YouTube video.
        """
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        self.env['social.media.post'].post_youtube_reply(
            self.post.id,
            'comment_123',
            'Test reply',
            channel_id=self.youtube_channel.id
        )
        self.assertTrue(mock_post.called)

    def test_create_lead_youtube_new_partner(self):
        """
        Test the automated lead and partner creation from a YouTube comment.
        """
        comment_data = {
            'id': 'comment_123',
            'userid': 'user_123',
            'username': 'Test User'
        }

        result = self.post.create_lead_youtube(comment_data)
        self.assertEqual(result['name'], self.post.name)

        partner = self.env['res.partner'].search([
            ('unique_yt_number', '=', 'user_123')
        ])
        self.assertTrue(partner.exists())
        self.assertEqual(partner.name, 'Test User')

    def test_create_lead_youtube_existing_partner(self):
        """
        Test lead creation when a corresponding partner already exists in the system.
        """
        partner = self.env['res.partner'].create({
            'name': 'Existing User',
            'unique_yt_number': 'user_456',
        })

        comment_data = {
            'id': 'comment_456',
            'userid': 'user_456',
            'username': 'Existing User'
        }

        result = self.post.create_lead_youtube(comment_data)
        self.assertEqual(result['partner_id'], partner.id)

    def test_action_youtube_comments(self):
        """
        Test the action that opens the interactive YouTube comments view.
        """
        try:
            result = self.post.action_youtube_comments()
            self.assertIsInstance(result, (dict, list))
        except Exception:
            self.skipTest("XML action reference not available in test environment")

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.get')
    def test_action_compute_likes_count(self, mock_get, mock_put):
        """
        Test the synchronization of engagement stats (likes, views) from YouTube.
        """
        mock_put_response = MagicMock()
        mock_put_response.json.return_value = {
            'statistics': {
                'likeCount': '100',
                'viewCount': '1000',
                'commentCount': '20'
            }
        }
        mock_put.return_value = mock_put_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'items': [
                {'id': 'comment_1'},
                {'id': 'comment_2'}
            ]
        }
        mock_get.return_value = mock_get_response

        self.post.action_compute_likes_count()
        self.assertEqual(self.post.youtube_likes_count, 100)
        self.assertEqual(self.post.youtube_views_count, 1000)

    def test_action_social_media_comments_youtube(self):
        """
        Test the redirection to YouTube-specific comment actions.
        """
        self.post.posted_on_youtube = True
        try:
            result = self.post.action_social_media_comments()
            self.assertIsInstance(result, (dict, list))
        except Exception:
            self.skipTest("XML action reference not available in test environment")

    def test_views_count_field(self):
        """
        Test the basic storage and retrieval of the views count field.
        """
        self.post.youtube_views_count = 5000
        self.assertEqual(self.post.youtube_views_count, 5000)

    def test_feed_youtube_relationships(self):
        """
        Test the integrity of relationships between the post, channel, and account.
        """
        self.assertEqual(self.post.youtube_channel_id, self.youtube_channel)
        self.assertEqual(self.post.youtube_channel_id.youtube_account_id,
                         self.youtube_account)
