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
from odoo import models


class SocialStreamColumn(models.Model):
    _inherit = 'social.stream.column'

    def _refresh_account_avatar(self):
        if self.platform != 'social.fb.account':
            return super()._refresh_account_avatar()
        account = self.env['social.fb.account'].browse(self.account_res_id)
        if account.exists() and account.profile_picture_url != self.account_avatar_url:
            self.account_avatar_url = account.profile_picture_url or False

    def _fetch_posts(self, cursor=None):
        if self.platform != 'social.fb.account':
            return super()._fetch_posts(cursor=cursor)
        result = self.env['social.media.post'].get_feed_data(account_res_id=self.account_res_id, loadMore=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        items = [self._fb_post_to_item(post) for post in result.get('data', [])]
        return self._normalize_envelope(items, (result.get('paging') or {}).get('next'))

    def _fetch_comments(self, cursor=None):
        """ Facebook has no single "all comments for this account" endpoint -
        comments are always scoped per-post, so this pages through the same
        feed _fetch_posts() uses (loadMore=cursor, following its own
        paging.next) and checks each post's comments - "Load More" keeps
        paging the feed further back instead of being capped at a fixed
        number of posts. """
        if self.platform != 'social.fb.account':
            return super()._fetch_comments(cursor=cursor)
        Post = self.env['social.media.post']
        feed_result = Post.get_feed_data(account_res_id=self.account_res_id, loadMore=cursor)
        if isinstance(feed_result, dict) and feed_result.get('type') == 'ir.actions.client':
            return feed_result
        items = []
        for post in feed_result.get('data') or []:
            comments_result = Post.get_facebook_comments(feed=post.get('id'), account_res_id=self.account_res_id)
            if isinstance(comments_result, dict) and comments_result.get('type') == 'ir.actions.client':
                continue
            comment_list = comments_result.get('data') or [] if isinstance(comments_result, dict) else []
            for comment in comment_list:
                items.append(self._fb_comment_to_item(comment, post))
        items.sort(key=lambda i: i.get('created_at') or '', reverse=True)
        next_cursor = (feed_result.get('paging') or {}).get('next')
        return self._normalize_envelope(items, next_cursor)

    def _fetch_mentions(self, cursor=None):
        if self.platform != 'social.fb.account':
            return super()._fetch_mentions(cursor=cursor)
        result = self.env['social.media.post'].get_facebook_mentions(self.account_res_id, cursor=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _fetch_unpublished(self, cursor=None):
        if self.platform != 'social.fb.account':
            return super()._fetch_unpublished(cursor=cursor)
        result = self.env['social.media.post'].get_facebook_unpublished_posts(self.account_res_id, cursor=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _fb_post_to_item(self, post):
        return {
            'id': post.get('id'),
            'item_kind': 'post',
            'author_name': post.get('author_name'),
            'author_avatar_url': post.get('profile_image_url'),
            'text': post.get('description'),
            'image_url': post.get('posted_image_url'),
            'image_urls': post.get('posted_image_urls'),
            'permalink': post.get('author_link_url'),
            'posted_date': post.get('posted_date'),
            'like_count': post.get('likes_count', 0),
            'comment_count': post.get('comments_count', 0),
        }

    def _fb_comment_to_item(self, comment, post):
        base_url = self.env['social.fb.account'].browse(self.account_res_id).facebook_base_url
        return {
            'id': comment.get('id'),
            'item_kind': 'comment_thread',
            'author_name': comment.get('username'),
            'author_avatar_url': self._fb_avatar_url(base_url, comment.get('userid')),
            'text': comment.get('text'),
            'created_at': self._parse_date(comment.get('created_time')),
            'like_count': comment.get('like_count', 0),
            'can_remove': comment.get('can_remove', False),
            'can_reply': True,
            'reply_count': comment.get('reply_count', 0),
            'replies': [],
            'extra': {
                'post_id': post.get('id'),
                'post_text': post.get('description'),
                'parent_title': post.get('description') or 'this post',
                'parent_permalink': post.get('author_link_url'),
                'userid': comment.get('userid'),
                'lead_id': self._existing_lead_id('unique_fb_comment_number', comment.get('id')),
            },
        }

    def _fb_avatar_url(self, base_url, user_id):
        """Facebook exposes a user/Page-scoped-user's profile picture at this
        stable public redirect - no extra API round trip needed per comment."""
        if not user_id or user_id == '0':
            return False
        return f"{base_url}/{user_id}/picture?type=normal"
