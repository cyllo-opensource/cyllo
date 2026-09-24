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
import base64
from io import BytesIO
from PIL import Image
from odoo.tests.common import TransactionCase
from unittest.mock import patch, Mock
from odoo.exceptions import ValidationError


class TestSocialMediaPostDashboardInstagram(TransactionCase):
    """Covers social.insta.account's contribution to social.media.post's
    dashboard/connect dispatch hooks (moved here from
    cyllo_social_media_marketing when social.insta.account moved out)."""

    def setUp(self):
        super(TestSocialMediaPostDashboardInstagram, self).setUp()
        self.insta_account = self.env['social.insta.account'].create({
            'facebook_insta_page_name': 'Insta Page',
            'state': 'connected',
            'instagram_access_token': 'token',
            'instagram_page_access_token': 'token',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        })

    def test_get_dashboard_data(self):
        """Test the Instagram tile in the aggregated dashboard data."""
        self.env['social.media.post'].create({
            'name': 'IG Post',
            'description': 'Test Content',
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'state': 'post',
            'insta_account_ids': [(6, 0, [self.insta_account.id])],
            'ig_likes_count': 20,
            'ig_comments_count': 8,
        })

        result = self.env['social.media.post'].get_dashboard_data()

        self.assertTrue(result)
        self.assertIn('dashboard_data', result)

        data = result['dashboard_data']
        ig_data = next(
            (d for d in data if d['platform'] == 'social.insta.account'), None
        )
        self.assertIsNotNone(ig_data)
        self.assertEqual(ig_data['account_name'], 'Insta Page')
        self.assertEqual(ig_data['total_likes'], 20)
        self.assertEqual(ig_data['total_comments'], 8)


class TestSocialMediaPostInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.insta_account = cls.env['social.insta.account'].create({
            'instagram_base_url': 'https://graph.facebook.com/v17.0',
            'facebook_insta_page_number': '123456789',
            'facebook_insta_page_name': 'Fake Page',
            'instagram_access_token': 'fake_token',
            'instagram_page_access_token': 'fake_page_token',
            'meta_app_number': '987654321',
            'meta_app_secret': 'fake_secret',
            'state': 'not connected',
            'company_id': cls.env.company.id
        })

        img = Image.new('RGB', (1, 1), color='white')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_base64 = base64.b64encode(buffer.getvalue())

        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'test.jpg',
            'mimetype': 'image/jpeg',
            'datas': img_base64,
            'public': False
        })

        cls.post = cls.env['social.media.post'].create({
            'name': 'Test Instagram Post',
            'description': 'Test Instagram Post',
            'post_on_instagram': True,
            'insta_account_ids': [(6, 0, [cls.insta_account.id])],
            'ir_attachment_ids': [(6, 0, [cls.attachment.id])],
            'mode': 'photo',
            'company_id': cls.env.company.id,
        })

    @patch('requests.get')
    @patch('requests.post')
    def test_action_post_success(self, mock_post, mock_get):
        """
        Test posting a social media post to Instagram successfully.
        """

        mock_get.side_effect = [
            Mock(json=Mock(return_value={'instagram_business_account': {'id': '987654321'}})),
            Mock(json=Mock(return_value={'username': 'fakeuser', 'name': 'Fake User'}))
        ]

        def post_side_effect(url, data):
            if 'media_publish' in url:
                mock_resp = Mock()
                mock_resp.text = '{"id": "published123"}'
                return mock_resp
            return Mock(text='{"id": "media123"}')

        mock_post.side_effect = post_side_effect

        self.post.action_post()

        self.assertEqual(self.post.ig_media_number, 'published123')
        self.assertEqual(self.post.posted_image_url, self.attachment.public_url)


class TestInstagramFetchContacts(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.insta_account = cls.env["social.insta.account"].create({
            "instagram_account_number": "123",
            "instagram_business_account_number": "123",
            "instagram_access_token": "TEST_ACCESS_TOKEN",
            "instagram_page_access_token": "TEST_PAGE_ACCESS_TOKEN",
            "facebook_insta_page_name": "Test Page",
            "meta_app_number": "META_APP_ID",
            "meta_app_secret": "META_APP_SECRET",
            "instagram_base_url": "https://graph.facebook.com/v19.0",
            "state": "connected",
        })

        cls.post = cls.env["social.media.post"].create({
            "name": "Test Instagram Post",
            "description": "Test Instagram Post",
            "ig_media_number": "MEDIA_123",
            "posted_on_ig": True,
            "insta_account_ids": [(6, 0, [cls.insta_account.id])],
            "company_id": cls.env.company.id,
        })

    @patch("odoo.addons.cyllo_instagram.models.social_media_post.SocialMediaPost.get_ig_comments_data")
    def test_action_fetch_data_from_ig_feed_creates_partner(self, mock_comments):
        """
        Test partner creation when a new Instagram user is found.
        """

        mock_comments.return_value = {
            "comments": {
                "data": [{"id": "COMMENT_1"}]
            }
        }

        with patch("odoo.addons.cyllo_instagram.models.social_media_post.requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(json=Mock(return_value={"from": {"id": "USER_1"}})),
                Mock(json=Mock(return_value={"id": "USER_1", "name": "Instagram User"})),
            ]

            result = self.post.action_fetch_data_from_ig_feed()

        partner = self.env["res.partner"].search([("unique_ig_number", "=", "USER_1")])
        self.assertTrue(partner, "Partner was not created!")
        self.assertEqual(partner.name, "Instagram User")
        self.assertEqual(partner.insta_account_id.id, self.insta_account.id)
        self.assertEqual(partner.post_id.id, self.post.id)

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("new contact saved", result["params"]["message"])

    @patch("odoo.addons.cyllo_instagram.models.social_media_post.SocialMediaPost.get_ig_comments_data")
    def test_action_fetch_data_from_ig_feed_no_new_partner(self, mock_comments):
        """
        Test scenario when all partners already exist.
        """

        self.env["res.partner"].create({
            "name": "Instagram User",
            "unique_ig_number": "USER_1",
            "insta_account_id": self.insta_account.id,
            "post_id": self.post.id,
        })

        mock_comments.return_value = {
            "comments": {
                "data": [{"id": "COMMENT_1"}]
            }
        }

        with patch("odoo.addons.cyllo_instagram.models.social_media_post.requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(json=Mock(return_value={"from": {"id": "USER_1"}})),
                Mock(json=Mock(return_value={"id": "USER_1", "name": "Instagram User"})),
            ]

            result = self.post.action_fetch_data_from_ig_feed()

        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("No new contacts", result["params"]["message"])
