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
from collections import defaultdict

import requests
from odoo import _, api, fields, models
from odoo.tools.safe_eval import datetime

from odoo.addons.cyllo_social_media_marketing.models.social_media_post import PLATFORM_REGISTRY

_logger = logging.getLogger(__name__)

PLATFORM_REGISTRY['youtube.account'] = {'module': 'cyllo_youtube', 'connect_method': 'action_get_authorization_url'}


class SocialMediaPost(models.Model):
    """
    Inherits the social.media.post model to handle posts for different
    social media platforms.
    """
    _inherit = 'social.media.post'

    post_on_youtube = fields.Boolean(string="Post in Youtube")
    youtube_channel_id = fields.Many2one('youtube.channel',
                                         string="Youtube Channels",
                                         help="Youtube connected accounts")
    youtube_video_number = fields.Char(string="Youtube Id",
                                       help="Unique id of video in youtube")
    posted_on_youtube = fields.Boolean(string="Posted on Youtube", readonly=True,
                                       help="Whether this post was actually published to YouTube.")
    youtube_likes_count = fields.Integer(string="Youtube Likes", readonly=True)
    youtube_comments_count = fields.Integer(string="Youtube Comments", readonly=True)
    youtube_views_count = fields.Integer(string="Youtube Views", readonly=True)

    def _get_platform_dashboard_tiles(self):
        tiles = super()._get_platform_dashboard_tiles()
        channels = self.env['youtube.channel'].search([('youtube_account_id.state', '=', 'sync')])
        if not channels:
            return tiles
        channel_ids = channels.ids
        all_posts = self.search([
            ('youtube_channel_id', 'in', channel_ids),
            ('state', '=', 'post'),
        ])
        posts_by_channel = defaultdict(lambda: self.browse())
        for post in all_posts:
            posts_by_channel[post.youtube_channel_id.id] |= post
        audience_stats = self._get_audience_batch_stats('youtube.channel', channel_ids)
        for channel in channels:
            posts = posts_by_channel.get(channel.id, self.browse())
            subscribers = self.get_youtube_channel_subscribers(channel.id)
            stats = audience_stats.get(channel.id, {})
            baseline = stats.get('baseline')
            if baseline is None:
                baseline = subscribers
            tiles.append({
                'id': channel.id,
                'account_name': channel.name,
                'platform': 'youtube.channel',
                'total_posts': len(posts),
                'total_likes': sum(posts.mapped('youtube_likes_count')),
                'total_comments': 0,
                'total_audience': subscribers,
                'account_image': False,
                'audience_baseline': baseline,
                'audience_delta': subscribers - baseline,
                'audience_history': stats.get('history', []),
            })
        return tiles

    def _get_recent_post_account_info(self, post):
        if post.posted_on_youtube and post.youtube_channel_id:
            return post.youtube_channel_id.name, False
        return super()._get_recent_post_account_info(post)

    def _get_calendar_platform_icon(self, post):
        if post.posted_on_youtube:
            return 'ri-youtube-fill'
        return super()._get_calendar_platform_icon(post)

    def _get_platform_permalink(self, platform_key):
        if platform_key == 'youtube.channel' and self.posted_on_youtube and self.youtube_video_number:
            return f"https://www.youtube.com/watch?v={self.youtube_video_number}"
        return super()._get_platform_permalink(platform_key)

    @api.model
    def get_connected_accounts(self):
        accounts = super().get_connected_accounts()
        for channel in self.env['youtube.channel'].search(
                [('youtube_account_id.state', '=', 'sync'), ('is_active', '=', True)]):
            accounts.append({
                'platform': 'youtube.channel',
                'id': channel.id,
                'name': channel.name,
                'avatar_url': ('/web/image/youtube.channel/%s/channel_image' % channel.id)
                              if channel.channel_image else False,
            })
        return accounts

    @api.onchange('post_on_youtube')
    def _onchange_post_on_youtube(self):
        """
        Function to disable other social media when YouTube is turned on
        """
        if self.post_on_youtube:
            self.mode = 'video'
            if hasattr(self, "post_on_facebook"):
                self.post_on_facebook = False
            if hasattr(self, "post_on_instagram"):
                self.post_on_instagram = False

    @api.onchange('mode')
    def _onchange_mode(self):
        """
        Function to disable other social media when mode is "video" AND
        YouTube is the platform actually selected - Facebook/Instagram also
        support Video mode (Reels/video posts) in their own right, so
        switching to Video mode by itself must not force them off.
        """
        res = super(SocialMediaPost, self)._onchange_mode()
        if self.mode == 'video' and self.post_on_youtube:
            if hasattr(self, 'post_on_instagram'):
                self.post_on_instagram = False
            if hasattr(self, 'post_on_facebook'):
                self.post_on_facebook = False
        if self.mode != 'video' and hasattr(self, 'post_on_youtube'):
            self.post_on_youtube = False
        return res

    def action_post(self):
        """Function to post the media"""
        try:
            if self.post_on_youtube and self.mode == 'video' and not self.youtube_channel_id:
                _logger.warning("YouTube action_post: post=%s has post_on_youtube=True but no "
                                "youtube_channel_id set", self.id)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No YouTube channel selected to post to."),
                        'type': 'warning',
                    },
                }
            for channel in self.youtube_channel_id.sudo():
                if self.post_on_youtube and self.mode == 'video':
                    if self.state == 'draft':
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(
                                    "Please Upload a video for posting"),
                                'type': 'warning',
                            },
                        }
                    account = channel.youtube_account_id
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": self.youtube_video_number,
                        "status": {
                            "privacyStatus": "public",
                            "embeddable": True,
                        },
                        "snippet": {
                            "title": self.name,
                            "description": self.description,
                            "categoryId": "22"
                        },
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=status,snippet"
                    response = requests.put(update_url, headers=headers, json=updated_metadata, timeout=30)
                    if response.status_code != 200:
                        _logger.error("YouTube video update failed (%s): %s",
                                      response.status_code, response.text)
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': _(
                                    "Failed to update the video on YouTube (%s). "
                                    "Check your connection/credentials and try again."
                                ) % response.status_code,
                                'type': 'warning',
                            },
                        }
                    res_json = response.json()
                    post_image_url = res_json['snippet']['thumbnails']['high']['url']
                    self.write({
                        'posted_image_url': post_image_url,
                        'posted_on_youtube': True,
                        'youtube_video_number': res_json.get('id'),
                    })
            return super().action_post()
        except Exception as e:
            _logger.exception("YouTube action_post failed for post id=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are "
                        "accurate and ensure that your device is connected to "
                        "the internet"),
                    'type': 'warning',
                },
            }

    def get_youtube_account(self):
        """Function to return the access token and details"""
        return {
            'key': self.youtube_channel_id.sudo().youtube_account_id.access_token,
            'details': self.read()[0]
        }

    @api.model
    def get_youtube_feed_data(self, channel_id=None, pageToken=None):
        """Live browse of the connected YouTube channel's own uploaded videos
        (YouTube's own content, not tied to any social.media.post record)."""
        try:
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
                if not channel.exists():
                    return {"data": [], "nextPageToken": None}
                yt_account = channel.youtube_account_id
            else:
                yt_account = self.env['youtube.account'].sudo().get_default_youtube_account()
                if not yt_account or not yt_account.channel_ids:
                    return {"data": [], "nextPageToken": None}
                channel = yt_account.channel_ids[0]

            channel_id_number = channel.youtube_number
            access_token = yt_account.access_token

            channel_url = (
                f"https://www.googleapis.com/youtube/v3/channels"
                f"?part=contentDetails,snippet"
                f"&id={channel_id_number}"
                f"&access_token={access_token}"
            )

            channel_res = requests.get(channel_url, timeout=30).json()
            uploads_playlist_id = channel_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            channel_thumb = channel_res["items"][0]["snippet"]["thumbnails"]["default"]["url"]
            playlist_url = (
                f"https://www.googleapis.com/youtube/v3/playlistItems"
                f"?part=snippet"
                f"&playlistId={uploads_playlist_id}"
                f"&maxResults=5"
                f"&access_token={access_token}"
            )
            if pageToken:
                playlist_url += f"&pageToken={pageToken}"

            playlist_res = requests.get(playlist_url, timeout=30).json()
            video_items = []
            video_ids = []

            for item in playlist_res.get("items", []):
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]
                video_ids.append(video_id)
                video_items.append({
                    "id": video_id,
                    "youtube_number": video_id,
                    "publishedAt": snippet["publishedAt"],
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "channelTitle": snippet.get("channelTitle", ""),
                    "thumbnails": snippet.get("thumbnails", {}),
                    "channelThumb": channel_thumb,
                })
            if video_ids:
                stats_url = (
                    f"https://www.googleapis.com/youtube/v3/videos"
                    f"?part=statistics"
                    f"&id={','.join(video_ids)}"
                    f"&access_token={access_token}"
                )
                stats_res = requests.get(stats_url, timeout=30).json()
                stats_map = {item["id"]: item["statistics"] for item in stats_res.get("items", [])}

                for video in video_items:
                    video["statistics"] = stats_map.get(video["id"], {})
            return {
                "data": video_items or [],
                "nextPageToken": playlist_res.get("nextPageToken"),
            }

        except Exception as e:
            _logger.exception("YouTube get_youtube_feed_data failed for channel_id=%s", channel_id)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": f"YouTube Feed Error: {str(e)}",
                    "type": "warning",
                },
            }

    @api.model
    def get_youtube_channel_subscribers(self, channel_id):
        """Live subscriber count for one channel, for the dashboard's
        follower cards - youtube.channel has no stored followers_count
        field (unlike the FB/IG account models), so this is fetched fresh
        rather than read off a cached field."""
        channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
        if not channel.exists():
            return 0
        try:
            account = channel.youtube_account_id
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            access_token = account.access_token
            channel_url = (
                f"https://www.googleapis.com/youtube/v3/channels"
                f"?part=statistics"
                f"&id={channel.youtube_number}"
                f"&access_token={access_token}"
            )
            items = requests.get(channel_url, timeout=10).json().get('items', [])
            if not items:
                return 0
            return int(items[0].get('statistics', {}).get('subscriberCount', 0))
        except Exception as e:
            _logger.warning("Could not fetch subscriber count for YouTube channel %s: %s", channel_id, e)
            return 0

    @api.model
    def get_youtube_moderated_comments(self, channel_id, status, page_token=None):
        """Live, owner-only fetch of a channel's held-for-review or
        likely-spam comment queue. Requires the channel owner's own token
        (youtube.force-ssl scope, already part of the connect flow) - never
        writes to Odoo."""
        try:
            channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
            account = channel.youtube_account_id
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet&allThreadsRelatedToChannelId={channel.youtube_number}"
                f"&moderationStatus={status}&maxResults=20"
                f"&access_token={account.access_token}"
            )
            if page_token:
                url += f"&pageToken={page_token}"
            res = requests.get(url, timeout=10).json()
            if res.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': res['error'].get('message', ''), 'type': 'warning'},
                }
            items = []
            for item in res.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                items.append({
                    'id': item['id'],
                    'item_kind': 'comment_thread',
                    'author_name': snippet.get('authorDisplayName'),
                    'author_avatar_url': snippet.get('authorProfileImageUrl'),
                    'text': snippet.get('textOriginal'),
                    'created_at': self.env['social.stream.column']._parse_date(snippet.get('publishedAt')),
                    'like_count': snippet.get('likeCount', 0),
                    'can_remove': True,
                    'can_reply': True,
                    'reply_count': item.get('snippet', {}).get('totalReplyCount', 0),
                    'replies': [],
                })
            return {'items': items, 'cursor': res.get('nextPageToken')}
        except Exception as e:
            _logger.exception("YouTube get_youtube_moderated_comments failed for channel_id=%s", channel_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': f"YouTube Moderation Error: {str(e)}", 'type': 'warning'},
            }

    @api.model
    def get_youtube_channel_playlists(self, channel_id):
        """List a channel's playlists - feeds the Add-a-Stream flyout's
        playlist picker for the Playlist stream type."""
        try:
            channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
            account = channel.youtube_account_id
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            url = (
                f"https://www.googleapis.com/youtube/v3/playlists"
                f"?part=snippet&channelId={channel.youtube_number}&maxResults=50"
                f"&access_token={account.access_token}"
            )
            res = requests.get(url, timeout=10).json()
            return [
                {'id': item['id'], 'title': item['snippet'].get('title', '')}
                for item in res.get('items', [])
            ]
        except Exception as e:
            _logger.exception("YouTube get_youtube_channel_playlists failed for channel_id=%s", channel_id)
            return []

    @api.model
    def get_youtube_playlist_items(self, channel_id, playlist_id, page_token=None):
        """Live fetch of a chosen playlist's videos. Never writes to Odoo."""
        try:
            channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
            account = channel.youtube_account_id
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            url = (
                f"https://www.googleapis.com/youtube/v3/playlistItems"
                f"?part=snippet,contentDetails&playlistId={playlist_id}&maxResults=10"
                f"&access_token={account.access_token}"
            )
            if page_token:
                url += f"&pageToken={page_token}"
            res = requests.get(url, timeout=10).json()
            if res.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': res['error'].get('message', ''), 'type': 'warning'},
                }
            video_ids = [item['contentDetails']['videoId'] for item in res.get('items', [])
                        if item.get('contentDetails', {}).get('videoId')]
            stats_map = self._yt_fetch_stats(video_ids, account.access_token)
            items = []
            for item in res.get('items', []):
                video_id = item.get('contentDetails', {}).get('videoId')
                if not video_id:
                    continue
                items.append(self._yt_video_to_item(video_id, item['snippet'], stats_map.get(video_id, {})))
            return {'items': items, 'cursor': res.get('nextPageToken')}
        except Exception as e:
            _logger.exception("YouTube get_youtube_playlist_items failed for playlist_id=%s", playlist_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': f"YouTube Playlist Error: {str(e)}", 'type': 'warning'},
            }

    @api.model
    def get_youtube_search(self, channel_id, query, order='date', page_token=None):
        """General public YouTube search (not limited to this channel's own
        uploads) - channel_id only picks whose token/quota to spend. Never
        writes to Odoo."""
        try:
            channel = self.env['youtube.channel'].sudo().browse(int(channel_id))
            account = channel.youtube_account_id
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet&type=video&maxResults=10"
                f"&q={requests.utils.quote(query)}&order={order}"
                f"&access_token={account.access_token}"
            )
            if page_token:
                url += f"&pageToken={page_token}"
            res = requests.get(url, timeout=10).json()
            if res.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': res['error'].get('message', ''), 'type': 'warning'},
                }
            video_ids = [item['id']['videoId'] for item in res.get('items', [])
                        if item.get('id', {}).get('videoId')]
            stats_map = self._yt_fetch_stats(video_ids, account.access_token)
            items = []
            for item in res.get('items', []):
                video_id = item.get('id', {}).get('videoId')
                if not video_id:
                    continue
                items.append(self._yt_video_to_item(video_id, item['snippet'], stats_map.get(video_id, {})))
            return {'items': items, 'cursor': res.get('nextPageToken')}
        except Exception as e:
            _logger.exception("YouTube get_youtube_search failed for channel_id=%s, query=%s", channel_id, query)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': f"YouTube Search Error: {str(e)}", 'type': 'warning'},
            }

    def _yt_fetch_stats(self, video_ids, access_token):
        if not video_ids:
            return {}
        stats_url = (
            f"https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails"
            f"&id={','.join(video_ids)}&access_token={access_token}"
        )
        stats_res = requests.get(stats_url, timeout=10).json()
        return {item['id']: item for item in stats_res.get('items', [])}

    def _yt_video_to_item(self, video_id, snippet, stats):
        statistics = stats.get('statistics', {})
        duration = stats.get('contentDetails', {}).get('duration', False)
        thumbnails = snippet.get('thumbnails', {})
        thumb = thumbnails.get('medium') or thumbnails.get('high') or thumbnails.get('default') or {}
        return {
            'id': video_id,
            'item_kind': 'post',
            'author_name': snippet.get('channelTitle', ''),
            'author_avatar_url': False,
            'text': snippet.get('title', ''),
            'thumbnail_url': thumb.get('url'),
            'duration': duration,
            'permalink': f'https://www.youtube.com/watch?v={video_id}',
            'posted_date': self.env['social.stream.column']._parse_date(snippet.get('publishedAt')),
            'like_count': int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else 0,
            'dislike_count': int(statistics.get('dislikeCount', 0)) if statistics.get('dislikeCount') else 0,
            'comment_count': int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else 0,
            'view_count': int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else 0,
        }

    def create_lead_youtube(self, comment_data, title=None):
        """Convert a YouTube comment author into a res.partner/crm.lead."""
        partner = self.env['res.partner'].search([('unique_yt_number', '=', comment_data['userid'])])
        lead = self.env['crm.lead'].search([('unique_yt_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_yt_number': comment_data['userid'],
                'youtube_account_id': self.youtube_channel_id.youtube_account_id.id,
                'post_id': self.id,
            })
        if lead:
            values = {
                'lead': lead.id,
            }
        else:
            values = {
                'name': self.name if self.name else title,
                'type': 'lead',
                'user_id': self.env.user.id,
                'partner_id': partner.id,
                'contact_name': partner.name,
                'lead': False,
                'unique_yt_comment_number': comment_data['id'],
                'campaign_id': self.campaign_id.id,
            }
        return values

    def action_youtube_comments(self):
        """Action to view YouTube comments associated with the post."""
        action = self.env.ref('cyllo_youtube.action_youtube_comment').read()[0]
        return action

    @api.model
    def get_youtube_comments(self, video_id, page_token=None, channel_id=None):
        """Fetch YouTube comments (paginated)."""
        try:
            yt_account = None
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                if not channel.exists():
                    return {"comments": [], "nextPageToken": None, "error": "Channel not found"}
                yt_account = channel.youtube_account_id
            else:
                yt_account = self.env['youtube.channel'].sudo().set_default_account_from_channel()
            access_token = yt_account.access_token
            comments_url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet"
                f"&videoId={video_id}"
                f"&maxResults=10"
                f"&access_token={access_token}"
            )
            if page_token:
                comments_url += f"&pageToken={page_token}"

            comments_res = requests.get(comments_url, timeout=30).json()
            comment_details_list = []

            for item in comments_res.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]

                partner = self.env['res.partner'].sudo().search(
                    [('unique_yt_number', '=', snippet.get('authorChannelId', {}).get('value'))],
                    limit=1
                )

                comment_details = {
                    "id": item["id"],
                    "username": snippet.get("authorDisplayName"),
                    "author_profile_img": snippet.get("authorProfileImageUrl"),
                    "userid": snippet.get("authorChannelId", {}).get("value"),
                    "text": snippet.get("textOriginal"),
                    "publishedAt": self.env['social.stream.column']._parse_date(snippet.get("publishedAt")),
                    "likeCount": snippet.get("likeCount", 0),
                    "partner_id": partner.id if partner else False,
                    "replies": [],
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                }

                comment_details_list.append(comment_details)

            return {
                "comments": comment_details_list,
                "nextPageToken": comments_res.get("nextPageToken")
            }

        except Exception as e:
            _logger.exception("YouTube get_youtube_comments failed for video_id=%s", video_id)
            return {"comments": [], "nextPageToken": None, "error": str(e)}

    @api.model
    def get_youtube_comment_replies(self, comment_id, page_token=None, channel_id=None):
        """Lazy, paginated fetch of one comment's replies - only called when
        a user actually expands a comment's "N replies", instead of every
        comment's replies being embedded upfront with the comment itself.
        YouTube's replies.list is flat (no further reply-to-reply nesting)."""
        try:
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                if not channel.exists():
                    return {"replies": [], "nextPageToken": None, "error": "Channel not found"}
                yt_account = channel.youtube_account_id
            else:
                yt_account = self.env['youtube.channel'].sudo().set_default_account_from_channel()
            access_token = yt_account.access_token
            replies_url = (
                f"https://www.googleapis.com/youtube/v3/comments"
                f"?part=snippet"
                f"&parentId={comment_id}"
                f"&maxResults=10"
                f"&access_token={access_token}"
            )
            if page_token:
                replies_url += f"&pageToken={page_token}"

            res = requests.get(replies_url, timeout=10).json()
            if res.get("error"):
                return {"replies": [], "nextPageToken": None, "error": res["error"].get("message", "Failed to load replies.")}
            replies = []
            for rec in res.get("items", []):
                r_snippet = rec["snippet"]
                replies.append({
                    "id": rec.get("id"),
                    "author": r_snippet.get("authorDisplayName"),
                    "author_profile_img": r_snippet.get("authorProfileImageUrl"),
                    "userid": r_snippet.get("authorChannelId", {}).get("value"),
                    "text": r_snippet.get("textOriginal"),
                    "publishedAt": self.env['social.stream.column']._parse_date(r_snippet.get("publishedAt")),
                    "likeCount": r_snippet.get("likeCount", 0),
                })
            return {"replies": replies, "nextPageToken": res.get("nextPageToken")}
        except Exception as e:
            _logger.exception("YouTube get_youtube_comment_replies failed for comment_id=%s", comment_id)
            return {"replies": [], "nextPageToken": None, "error": str(e)}

    @api.model
    def post_youtube_comments(self, active_id, comment, channel_id=None):
        """Function to post comments to a YouTube video."""
        try:
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                account = channel.youtube_account_id
            else:
                account = self.env['youtube.channel'].sudo().set_default_account_from_channel()
            if not account:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No YouTube account available to post comments",
                        'type': 'warning',
                    },
                }
            if not account.token_expiry_date or account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()

            url = 'https://youtube.googleapis.com/youtube/v3/commentThreads?part=snippet'
            headers = {
                'Authorization': f'Bearer {account.access_token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {
                'snippet': {
                    'videoId': active_id,
                    'topLevelComment': {
                        'snippet': {'textOriginal': comment}
                    }
                }
            }
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()
            if result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': result['error'].get('message', _("Failed to post comment.")),
                        'type': 'warning',
                    },
                }
            return result

        except Exception as e:
            _logger.exception("YouTube post_youtube_comments failed for active_id=%s", active_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Error posting comment: {str(e)}",
                    'type': 'warning',
                },
            }

    def action_social_media_comments(self):
        """Action to view social media comments associated with the post."""
        if self.posted_on_youtube:
            return self.action_youtube_comments()
        return super().action_social_media_comments()

    @api.model
    def post_youtube_reply(self, active_id, yt_comment_id, reply, channel_id=None):
        """Function to post replies to YouTube comments associated with the post."""
        try:
            if channel_id:
                channel = self.env['youtube.channel'].sudo().browse(channel_id)
                account = channel.youtube_account_id
            else:
                account = self.env['youtube.channel'].sudo().set_default_account_from_channel()
            if not account:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No YouTube account linked to this post.",
                        'type': 'warning',
                    },
                }
            if not account.token_expiry_date:
                account.action_refresh_access_token()
            elif account.token_expiry_date <= datetime.datetime.now():
                account.action_refresh_access_token()
            url = 'https://youtube.googleapis.com/youtube/v3/comments'
            params = {
                'part': 'snippet',
            }
            headers = {
                'Authorization': 'Bearer ' + account.access_token,
                'Accept': 'application/json',
            }
            payload = {
                'snippet': {
                    'parentId': yt_comment_id,
                    'textOriginal': reply
                }
            }
            response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
            result = response.json()
            if result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': result['error'].get('message', _("Failed to post reply.")),
                        'type': 'warning',
                    },
                }
            return result
        except Exception as e:
            _logger.exception("YouTube post_youtube_reply failed for yt_comment_id=%s", yt_comment_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device is "
                        "connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_compute_likes_count_all(self):
        """Function to synchronize likes/comments/views for YouTube posts."""
        try:
            posts_yt = self.env['social.media.post'].search(
                [('youtube_video_number', '!=', False)])
            for post in posts_yt:
                account = post.youtube_channel_id.sudo().youtube_account_id
                if not account.token_expiry_date:
                    account.action_refresh_access_token()
                elif account.token_expiry_date <= datetime.datetime.now():
                    account.action_refresh_access_token()
                if post.posted_on_youtube:
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": post.youtube_video_number,
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics"
                    response = requests.put(update_url, headers=headers, json=updated_metadata, timeout=30)
                    url = "https://www.googleapis.com/youtube/v3/commentThreads"
                    params = {
                        'part': 'snippet,replies',
                        'textFormat': 'plainText',
                        'access_token': account.access_token,
                        'videoId': post.youtube_video_number,
                        'maxResults': 20
                    }
                    comments_result = requests.get(url, params=params, timeout=30)
                    values = {'youtube_likes_count': 0, 'youtube_comments_count': 0, 'youtube_views_count': 0}
                    if comments_result.status_code == 200 and comments_result.json().get('items'):
                        values['youtube_comments_count'] = len(comments_result.json().get('items'))
                    res_json = response.json()
                    if res_json.get('statistics', {}).get('likeCount'):
                        values['youtube_likes_count'] = int(res_json['statistics']['likeCount'])
                    if res_json.get('statistics', {}).get('commentCount'):
                        values['youtube_comments_count'] = int(res_json['statistics']['commentCount'])
                    if res_json.get('statistics', {}).get('viewCount'):
                        values['youtube_views_count'] = int(res_json['statistics']['viewCount'])
                    post.write(values)

            return super().action_compute_likes_count_all()
        except Exception:
            _logger.exception("YouTube action_compute_likes_count_all failed")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device is "
                        "connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_compute_likes_count(self):
        """Compute the number of likes on the post for YouTube."""
        try:
            for post in self:
                if post.posted_on_youtube:
                    account = post.youtube_channel_id.sudo().youtube_account_id
                    if not account.token_expiry_date:
                        account.action_refresh_access_token()
                    elif account.token_expiry_date <= datetime.datetime.now():
                        account.action_refresh_access_token()
                    headers = {
                        'Authorization': f'Bearer {account.access_token}',
                        'Accept': 'application/json',
                    }
                    updated_metadata = {
                        "id": post.youtube_video_number,
                    }
                    update_url = "https://www.googleapis.com/youtube/v3/videos?part=statistics"
                    response = requests.put(update_url, headers=headers, json=updated_metadata, timeout=30)
                    url = "https://www.googleapis.com/youtube/v3/commentThreads"
                    params = {
                        'part': 'snippet,replies',
                        'textFormat': 'plainText',
                        'access_token': account.access_token,
                        'videoId': post.youtube_video_number,
                        'maxResults': 20
                    }
                    comments_result = requests.get(url, params=params, timeout=30)
                    values = {'youtube_likes_count': 0, 'youtube_comments_count': 0, 'youtube_views_count': 0}
                    if comments_result.status_code == 200 and comments_result.json().get('items'):
                        values['youtube_comments_count'] = len(comments_result.json().get('items'))
                    res_json = response.json()
                    if res_json.get('statistics', {}).get('likeCount'):
                        values['youtube_likes_count'] = int(res_json['statistics']['likeCount'])
                    if res_json.get('statistics', {}).get('viewCount'):
                        values['youtube_views_count'] = int(res_json['statistics']['viewCount'])
                    post.write(values)
                return {
                    'likes_count': post.youtube_likes_count,
                    'comments_count': post.youtube_comments_count,
                    'views_count': post.youtube_views_count,
                }
        except Exception:
            _logger.exception("YouTube action_compute_likes_count failed for post ids=%s", self.ids)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device is "
                        "connected to the internet"),
                    'type': 'warning',
                },
            }
