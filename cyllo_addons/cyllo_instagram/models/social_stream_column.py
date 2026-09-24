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
        if self.platform != 'social.insta.account':
            return super()._refresh_account_avatar()
        account = self.env['social.insta.account'].browse(self.account_res_id)
        if account.exists() and account.profile_picture_url != self.account_avatar_url:
            self.account_avatar_url = account.profile_picture_url or False

    def _fetch_posts(self, cursor=None):
        if self.platform != 'social.insta.account':
            return super()._fetch_posts(cursor=cursor)
        result = self.env['social.media.post'].get_insta_feed_data(account_res_id=self.account_res_id, loadMore=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        items = [self._ig_media_to_item(media) for media in result.get('data', [])]
        return self._normalize_envelope(items, (result.get('paging') or {}).get('next'))

    def _fetch_comments(self, cursor=None):
        """ Instagram has no single "all comments for this account" endpoint -
        comments are always scoped per-media, so this pages through the same
        feed _fetch_posts() uses (loadMore=cursor, following its own
        paging.next) and checks each media's comments - "Load More" keeps
        paging the feed further back instead of being capped at a fixed
        number of posts. """
        if self.platform != 'social.insta.account':
            return super()._fetch_comments(cursor=cursor)
        Post = self.env['social.media.post']
        feed_result = Post.get_insta_feed_data(account_res_id=self.account_res_id, loadMore=cursor)
        if isinstance(feed_result, dict) and feed_result.get('type') == 'ir.actions.client':
            return feed_result
        items = []
        for media in feed_result.get('data') or []:
            comments_result = Post.get_instagram_comments(feed=media.get('id'), account_res_id=self.account_res_id)
            if isinstance(comments_result, dict) and comments_result.get('type') == 'ir.actions.client':
                continue
            for comment in comments_result.get('data') or []:
                items.append(self._ig_comment_to_item(comment, media))
        items.sort(key=lambda i: i.get('created_at') or '', reverse=True)
        next_cursor = (feed_result.get('paging') or {}).get('next')
        return self._normalize_envelope(items, next_cursor)

    def _fetch_hashtag_recent(self, cursor=None):
        if self.platform != 'social.insta.account':
            return super()._fetch_hashtag_recent(cursor=cursor)
        return self._ig_hashtag_stream('recent', cursor)

    def _fetch_hashtag_trending(self, cursor=None):
        if self.platform != 'social.insta.account':
            return super()._fetch_hashtag_trending(cursor=cursor)
        return self._ig_hashtag_stream('top', cursor)

    def _ig_hashtag_stream(self, kind, cursor):
        hashtag = self.get_config().get('hashtag')
        result = self.env['social.media.post'].get_instagram_hashtag_media(
            self.account_res_id, hashtag, kind, cursor=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _ig_media_to_item(self, media):
        is_video = media.get('media_type') == 'VIDEO'
        image_urls = False
        image_url = media.get('media_url') if not is_video else False
        if media.get('media_type') == 'CAROUSEL_ALBUM':
            children_urls = [
                child.get('media_url') for child in media.get('children', {}).get('data', [])
                if child.get('media_type') != 'VIDEO' and child.get('media_url')
            ]
            image_url = children_urls[0] if children_urls else False
            image_urls = children_urls if len(children_urls) > 1 else False
        return {
            'id': media.get('id'),
            'item_kind': 'post',
            'author_name': media.get('username'),
            'author_avatar_url': media.get('profile_picture_url'),
            'text': media.get('caption'),
            'image_url': image_url,
            'image_urls': image_urls,
            'video_url': media.get('media_url') if is_video else False,
            'permalink': media.get('permalink'),
            'posted_date': self._parse_date(media.get('timestamp')),
            'like_count': media.get('like_count', 0),
            'comment_count': media.get('comments_count', 0),
        }

    def _ig_comment_to_item(self, comment, media):
        return {
            'id': comment.get('id'),
            'item_kind': 'comment_thread',
            'author_name': comment.get('username'),
            'author_avatar_url': False,
            'text': comment.get('text'),
            'created_at': self._parse_date(comment.get('timestamp')),
            'like_count': comment.get('like_count', 0),
            'can_remove': False,
            'can_reply': True,
            'reply_count': comment.get('reply_count', 0),
            'replies': [],
            'extra': {
                'post_id': media.get('id'),
                'post_text': media.get('caption'),
                'parent_title': media.get('caption') or 'this post',
                'parent_permalink': media.get('permalink'),
                'from_id': comment.get('from', {}).get('id'),
                'lead_id': self._existing_lead_id('unique_ig_comment_number', comment.get('id')),
            },
        }
