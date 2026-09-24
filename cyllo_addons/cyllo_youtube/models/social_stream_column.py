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

COMMENTS_STREAM_VIDEO_LIMIT = 5


class SocialStreamColumn(models.Model):
    _inherit = 'social.stream.column'

    def _fetch_videos(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_videos(cursor=cursor)
        result = self.env['social.media.post'].get_youtube_feed_data(channel_id=self.account_res_id, pageToken=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        items = [self._yt_upload_to_item(video) for video in result.get('data', [])]
        return self._normalize_envelope(items, result.get('nextPageToken'))

    def _fetch_comments(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_comments(cursor=cursor)
        Post = self.env['social.media.post']
        feed_result = Post.get_youtube_feed_data(channel_id=self.account_res_id)
        if isinstance(feed_result, dict) and feed_result.get('type') == 'ir.actions.client':
            return feed_result
        items = []
        for video in (feed_result.get('data') or [])[:COMMENTS_STREAM_VIDEO_LIMIT]:
            comments_result = Post.get_youtube_comments(video['id'], channel_id=self.account_res_id)
            for comment in comments_result.get('comments') or []:
                items.append(self._yt_comment_to_item(comment, video))
        items.sort(key=lambda i: i.get('created_at') or '', reverse=True)
        return self._normalize_envelope(items, None)

    def _fetch_moderate(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_moderate(cursor=cursor)
        return self._yt_moderation_stream('heldForReview', cursor)

    def _fetch_likely_spam(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_likely_spam(cursor=cursor)
        return self._yt_moderation_stream('likelySpam', cursor)

    def _yt_moderation_stream(self, status, cursor):
        result = self.env['social.media.post'].get_youtube_moderated_comments(
            self.account_res_id, status, page_token=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _fetch_search(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_search(cursor=cursor)
        config = self.get_config()
        result = self.env['social.media.post'].get_youtube_search(
            self.account_res_id, config.get('search_query', ''),
            order=config.get('order', 'date'), page_token=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _fetch_playlist(self, cursor=None):
        if self.platform != 'youtube.channel':
            return super()._fetch_playlist(cursor=cursor)
        config = self.get_config()
        result = self.env['social.media.post'].get_youtube_playlist_items(
            self.account_res_id, config.get('playlist_id'), page_token=cursor)
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            return result
        return self._normalize_envelope(result.get('items', []), result.get('cursor'))

    def _yt_upload_to_item(self, video):
        stats = video.get('statistics', {})
        thumbnails = video.get('thumbnails', {})
        thumb = thumbnails.get('medium') or thumbnails.get('high') or thumbnails.get('default') or {}
        return {
            'id': video.get('id'),
            'item_kind': 'post',
            'author_name': video.get('channelTitle'),
            'author_avatar_url': video.get('channelThumb'),
            'text': video.get('title'),
            'thumbnail_url': thumb.get('url'),
            'permalink': 'https://www.youtube.com/watch?v=%s' % video.get('id'),
            'posted_date': self._parse_date(video.get('publishedAt')),
            'like_count': int(stats.get('likeCount', 0)) if stats.get('likeCount') else 0,
            'comment_count': int(stats.get('commentCount', 0)) if stats.get('commentCount') else 0,
            'view_count': int(stats.get('viewCount', 0)) if stats.get('viewCount') else 0,
        }

    def _yt_comment_to_item(self, comment, video):
        return {
            'id': comment.get('id'),
            'item_kind': 'comment_thread',
            'author_name': comment.get('username'),
            'author_avatar_url': comment.get('author_profile_img'),
            'text': comment.get('text'),
            'created_at': self._parse_date(comment.get('publishedAt')),
            'like_count': comment.get('likeCount', 0),
            'can_remove': True,
            'can_reply': True,
            'reply_count': comment.get('reply_count', 0),
            'replies': [],
            'extra': {
                'video_id': video.get('id'),
                'video_title': video.get('title'),
                'parent_title': video.get('title') or 'this video',
                'parent_permalink': 'https://www.youtube.com/watch?v=%s' % video.get('id'),
                'userid': comment.get('userid'),
                'lead_id': self._existing_lead_id('unique_yt_comment_number', comment.get('id')),
            },
        }
