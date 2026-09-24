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
import logging
import urllib.parse
from datetime import datetime

import requests

from odoo import models

_logger = logging.getLogger(__name__)

LINKEDIN_POSTS_PAGE_SIZE = 15
LINKEDIN_COMMENTS_POST_LIMIT = 5
LINKEDIN_POLL_DURATION_LABELS = {
    'ONE_DAY': '1 day',
    'THREE_DAYS': '3 days',
    'SEVEN_DAYS': '7 days',
    'FOURTEEN_DAYS': '14 days',
}


class SocialStreamColumn(models.Model):
    """LinkedIn implementation of the social.stream.column dispatch hooks."""
    _inherit = 'social.stream.column'

    def _fetch_posts(self, cursor=None):
        if self.platform != 'linkedin.organization':
            return super()._fetch_posts(cursor=cursor)

        org = self.env['linkedin.organization'].sudo().browse(self.account_res_id)
        account = org.account_id
        if not org.exists() or not account.linkedin_access_token:
            return self._normalize_envelope([])

        rest_headers = {
            'Authorization': f'Bearer {account.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202602',
        }
        owner_urn = org.org_urn

        start = int(cursor) if cursor else 0
        params = {
            'q': 'author',
            'author': owner_urn,
            'count': LINKEDIN_POSTS_PAGE_SIZE,
            'start': start,
        }
        try:
            resp = requests.get(
                'https://api.linkedin.com/rest/posts',
                params=params,
                headers=rest_headers,
                timeout=30,
            )
            if not resp.ok:
                _logger.error('LinkedIn Posts API error %s: %s', resp.status_code, resp.text[:300])
                return self._normalize_envelope([])

            data = resp.json()
            elements = data.get('elements', [])
            paging = data.get('paging', {})
            links = paging.get('links', [])
            has_more = any(link.get('rel') == 'next' for link in links)
            if not has_more and 'total' in paging:
                has_more = (start + LINKEDIN_POSTS_PAGE_SIZE) < paging['total']
            next_cursor = str(start + LINKEDIN_POSTS_PAGE_SIZE) if has_more else None

            items = [
                self._li_post_to_item(element, org, rest_headers)
                for element in elements
            ]
            return self._normalize_envelope(items, next_cursor)

        except Exception:
            _logger.exception('LinkedIn _fetch_posts failed for account %s', account.name)
            return self._normalize_envelope([])

    def _fetch_comments(self, cursor=None):
        if self.platform != 'linkedin.organization':
            return super()._fetch_comments(cursor=cursor)

        org = self.env['linkedin.organization'].sudo().browse(self.account_res_id)
        account = org.account_id
        if not org.exists() or not account.linkedin_access_token:
            return self._normalize_envelope([])

        legacy_headers = {'Authorization': f'Bearer {account.linkedin_access_token}'}
        rest_headers = dict(legacy_headers)
        rest_headers.update({
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202602',
        })
        owner_urn = org.org_urn

        try:
            resp = requests.get(
                'https://api.linkedin.com/rest/posts',
                params={'q': 'author', 'author': owner_urn, 'count': LINKEDIN_COMMENTS_POST_LIMIT, 'start': 0},
                headers=rest_headers,
                timeout=30,
            )
            if not resp.ok:
                return self._normalize_envelope([])
            posts = resp.json().get('elements', [])
        except Exception:
            _logger.exception('LinkedIn _fetch_comments: failed to get posts')
            return self._normalize_envelope([])

        items = []
        for post in posts:
            post_urn = post.get('id', '')
            post_text = post.get('commentary', '')
            if not post_urn:
                continue
            try:
                encoded_urn = urllib.parse.quote(post_urn)
                c_resp = requests.get(
                    f'https://api.linkedin.com/v2/socialActions/{encoded_urn}/comments'
                    f'?projection=(elements*(id,message,created,actor~,commentsSummary))',
                    headers=legacy_headers,
                    timeout=20,
                )
                if not c_resp.ok:
                    continue
                for comment in c_resp.json().get('elements', []):
                    items.append(self._li_comment_to_item(comment, post_urn, post_text))
            except Exception:
                _logger.debug('LinkedIn _fetch_comments: failed to get comments for %s', post_urn)

        return self._normalize_envelope(items, None)

    def _li_post_to_item(self, element, org, rest_headers):
        """Convert a LinkedIn REST /posts element to the stream card dict.

        Also:
        - Returns poll question/options/votes as structured data (item['poll'])
          instead of flattening into text, so the template can render real
          progress bars instead of a plain-text dump.
        - Fetches real like/comment counts from the V2 socialActions endpoint.
        """
        post_urn = element.get('id', '')
        text = element.get('commentary', '')

        image_url = False
        image_urls = []
        content = element.get('content', {}) or {}

        media = content.get('media', {})
        if media:
            image_url = (
                media.get('downloadUrl')
                or media.get('thumbnailUrl')
                or self._li_resolve_image_urn(media.get('id', ''), rest_headers)
            )

        if not image_url:
            multi_image = content.get('multiImage', {})
            if multi_image:
                for img in multi_image.get('images', []):
                    resolved = (
                        img.get('downloadUrl')
                        or img.get('thumbnailUrl')
                        or self._li_resolve_image_urn(img.get('id', ''), rest_headers)
                    )
                    if resolved:
                        image_urls.append(resolved)
                image_url = image_urls[0] if image_urls else False

        poll = content.get('poll', {})
        poll_data = False
        if poll:
            total_votes = poll.get('uniqueVotersCount', 0)
            poll_options = []
            for opt in poll.get('options', []):
                vote_count = opt.get('voteCount', 0)
                pct = round((vote_count / total_votes) * 100) if total_votes else 0
                poll_options.append({
                    'text': opt.get('text', ''),
                    'votes': vote_count,
                    'pct': pct,
                })
            duration = (poll.get('settings') or {}).get('duration', '')
            poll_data = {
                'question': poll.get('question', ''),
                'options': poll_options,
                'total_votes': total_votes,
                'duration': LINKEDIN_POLL_DURATION_LABELS.get(
                    duration, duration.replace('_', ' ').title() if duration else ''),
            }

        ts = element.get('publishedAt') or element.get('createdAt')
        posted_date = (
            datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
            if ts else False
        )

        like_count = 0
        comment_count = 0
        if post_urn:
            try:
                legacy_headers = {'Authorization': rest_headers.get('Authorization', '')}
                encoded_urn = urllib.parse.quote(post_urn, safe='')
                action_resp = requests.get(
                    f'https://api.linkedin.com/v2/socialActions/{encoded_urn}',
                    headers=legacy_headers,
                    timeout=15,
                )
                if action_resp.ok:
                    action_data = action_resp.json()
                    like_count = action_data.get('likesSummary', {}).get('totalLikes', 0)
                    comment_count = (
                        action_data.get('commentsSummary', {}).get('aggregatedTotalComments')
                        or action_data.get('commentsSummary', {}).get('totalComments', 0)
                    )
            except Exception:
                _logger.debug('LinkedIn socialActions fetch failed for %s', post_urn)

        return {
            'id': post_urn,
            'item_kind': 'post',
            'author_name': org.name,
            'author_avatar_url': org.logo_url or False,
            'text': text,
            'image_url': image_url,
            'image_urls': image_urls if len(image_urls) > 1 else False,
            'poll': poll_data,
            'permalink': f'https://www.linkedin.com/feed/update/{post_urn}' if post_urn else False,
            'posted_date': posted_date,
            'like_count': like_count,
            'comment_count': comment_count,
        }

    def _li_comment_to_item(self, comment, post_urn, post_text):
        """Convert a LinkedIn V2 socialActions comment element to a stream card dict."""
        actor = comment.get('actor~', {})
        first = actor.get('localizedFirstName', '')
        last = actor.get('localizedLastName', '')
        author_name = (f'{first} {last}'.strip()) or actor.get('localizedName', 'LinkedIn User')

        created_ms = comment.get('created', {}).get('time', 0)
        created_at = (
            datetime.fromtimestamp(created_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
            if created_ms else ''
        )
        text = comment.get('message', {}).get('text', '')

        return {
            'id': comment.get('id'),
            'item_kind': 'comment_thread',
            'author_name': author_name,
            'author_avatar_url': False,
            'text': text,
            'created_at': created_at,
            'like_count': 0,
            'can_remove': False,
            'can_reply': False,
            'reply_count': 0,
            'replies': [],
            'extra': {
                'post_id': post_urn,
                'post_text': post_text,
                'parent_title': post_text or 'LinkedIn post',
                'parent_permalink': f'https://www.linkedin.com/feed/update/{post_urn}',
            },
        }

    def _li_resolve_image_urn(self, urn, rest_headers):
        """Try to resolve a urn:li:image: URN to a download URL."""
        if not urn or 'urn:li:image:' not in urn:
            return False
        try:
            encoded = urllib.parse.quote(urn, safe='')
            r = requests.get(
                f'https://api.linkedin.com/rest/images/{encoded}',
                headers=rest_headers,
                timeout=15,
            )
            if r.ok:
                d = r.json()
                return d.get('downloadUrl') or d.get('thumbnail')
            _logger.warning(
                'LinkedIn _li_resolve_image_urn: %s returned %s: %s',
                urn, r.status_code, r.text[:300],
            )
        except Exception:
            _logger.exception('LinkedIn _li_resolve_image_urn failed for %s', urn)
        return False
