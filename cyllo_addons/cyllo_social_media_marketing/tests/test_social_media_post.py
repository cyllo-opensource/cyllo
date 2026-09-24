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
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestSocialMediaPost(TransactionCase):

    def setUp(self):
        super(TestSocialMediaPost, self).setUp()
        self.post = self.env['social.media.post'].create({
            'name': 'Test Post',
            'description': 'Test Content',
            'company_id': self.env.company.id,
            'user_id': self.env.user.id
        })

    def test_initial_state(self):
        self.assertEqual(self.post.state, 'draft')
        self.assertEqual(self.post.mode, 'url')

    def test_action_post(self):
        self.post.action_post()
        self.assertEqual(self.post.state, 'post')
        self.assertTrue(self.post.posted_date)

    def test_onchange_mode(self):
        self.post.mode = 'content_only'
        self.post._onchange_mode()


class TestSocialMediaPostDashboard(TransactionCase):
    """Covers social.media.post's platform-agnostic dispatch helpers.
    FB/IG-specific dashboard-tile and connect-flow coverage now lives
    alongside those models in cyllo_facebook/cyllo_instagram's own test
    suites - this module has no dependency on either, so it can't assume
    social.fb.account/social.insta.account exist here."""

    def test_get_model(self):
        """Test get_model method with mocked ir.module.module lookup"""
        from unittest.mock import MagicMock

        fake_module = MagicMock()

        def module_search_side_effect(domain, limit=1):
            domain_str = str(domain)

            if 'cyllo_facebook' in domain_str:
                return fake_module
            if 'cyllo_instagram' in domain_str:
                return fake_module

            return False

        with patch('odoo.models.Model.search',
                   side_effect=module_search_side_effect):

            res_fb = self.env['social.media.post'].get_model('social.fb.account')
            self.assertTrue(res_fb)

            res_ig = self.env['social.media.post'].get_model('social.insta.account')
            self.assertTrue(res_ig)

            res_yt = self.env['social.media.post'].get_model('youtube.account')
            self.assertFalse(res_yt)
