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
import datetime
import json
import logging
import time
from collections import defaultdict

import requests
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

IMAGE_MIMETYPES = ('image/jpeg', 'image/png')
VIDEO_MIMETYPES = ('video/mp4', 'video/quicktime')
VIDEO_STATUS_POLL_INTERVAL = 3
VIDEO_STATUS_POLL_ATTEMPTS = 40


class SocialMediaPost(models.Model):
    """
        Inherits the social.media.post model to handle posts for differentsocial media platforms.
    """
    _inherit = 'social.media.post'

    instagram_attachment_id = fields.Many2one('ir.attachment', compute="_compute_instagram_attachment_id")
    instagram_attachment_ids = fields.Many2many(
        'ir.attachment', compute="_compute_instagram_attachment_id", string="Instagram Attachments to Post",
        help="All image attachments to post - more than one is published as an Instagram carousel post.")
    post_on_instagram = fields.Boolean(string="Post in Instagram")
    insta_account_ids = fields.Many2many('social.insta.account', string="Instagram Accounts",
                                         help="Instagram connected accounts")
    ig_posted_account_ids = fields.Many2many(
        'social.insta.account', relation='social_media_post_ig_posted_account_rel',
        string="Instagram Accounts Already Posted", copy=False,
        help="Which of insta_account_ids already got a successful post - lets "
             "a retry (after a different account failed) skip accounts that "
             "already succeeded instead of posting to them a second time.")
    ig_media_number = fields.Char(string="Instagram Media ID", help="Unique identifier for Instagram media")
    posted_on_ig = fields.Boolean(string="Posted on Instagram", readonly=True,
                                  help="Whether this post was actually published to Instagram.")
    ig_likes_count = fields.Integer(string="Instagram Likes", readonly=True)
    ig_comments_count = fields.Integer(string="Instagram Comments", readonly=True)

    def _compute_instagram_attachment_id(self):
        """
        Computes the attachment ID(s) for Instagram posts.
        """
        for post in self:
            media_all = self.env['ir.attachment']
            for attachment in post.ir_attachment_ids:
                if attachment.mimetype in VIDEO_MIMETYPES:
                    media_all |= attachment
                else:
                    safe_image = attachment.get_social_safe_image()
                    if safe_image:
                        media_all |= safe_image
            media_all.write({'public': True})
            post.instagram_attachment_id = media_all[:1]
            post.instagram_attachment_ids = media_all

    def _get_platform_dashboard_tiles(self):
        tiles = super()._get_platform_dashboard_tiles()
        accounts = self.env['social.insta.account'].search([('state', '=', 'connected')])
        if not accounts:
            return tiles
        account_ids = accounts.ids
        account_id_set = set(account_ids)
        all_posts = self.search([('insta_account_ids', 'in', account_ids), ('state', '=', 'post')])
        posts_by_account = defaultdict(lambda: self.browse())
        for post in all_posts:
            for acc in post.insta_account_ids:
                if acc.id in account_id_set:
                    posts_by_account[acc.id] |= post
        audience_stats = self._get_audience_batch_stats('social.insta.account', account_ids)
        for account in accounts:
            posts = posts_by_account.get(account.id, self.browse())
            stats = audience_stats.get(account.id, {})
            baseline = stats.get('baseline')
            if baseline is None:
                baseline = account.followers_count
            tiles.append({
                'id': account.id,
                'account_name': account.facebook_insta_page_name,
                'platform': 'social.insta.account',
                'total_posts': len(posts),
                'total_likes': sum(posts.mapped('ig_likes_count')),
                'total_comments': sum(posts.mapped('ig_comments_count')),
                'total_audience': account.followers_count,
                'account_image': account.profile_picture_url or False,
                'audience_baseline': baseline,
                'audience_delta': account.followers_count - baseline,
                'audience_history': stats.get('history', []),
            })
        return tiles

    def _get_recent_post_account_info(self, post):
        if post.posted_on_ig and post.insta_account_ids:
            account = post.insta_account_ids[0]
            return account.facebook_insta_page_name, account.profile_picture_url or False
        return super()._get_recent_post_account_info(post)

    def _get_calendar_platform_icon(self, post):
        if post.posted_on_ig:
            return 'ri-instagram-line'
        return super()._get_calendar_platform_icon(post)

    def _get_platform_permalink(self, platform_key):
        if platform_key == 'social.insta.account' and self.posted_on_ig \
                and self.ig_media_number and self.insta_account_ids:
            account = self.insta_account_ids[0]
            try:
                url = (f"{account.instagram_base_url}/{self.ig_media_number}"
                       f"?fields=permalink&access_token={account.instagram_access_token}")
                res = requests.get(url, timeout=15).json()
                if res.get('permalink'):
                    return res['permalink']
            except Exception:
                _logger.exception("Instagram _get_platform_permalink failed for post=%s", self.id)
        return super()._get_platform_permalink(platform_key)

    @api.model
    def get_connected_accounts(self):
        accounts = super().get_connected_accounts()
        for account in self.env['social.insta.account'].search([('state', '=', 'connected')]):
            accounts.append({
                'platform': 'social.insta.account',
                'id': account.id,
                'name': account.facebook_insta_page_name,
                'avatar_url': account.profile_picture_url or False,
            })
        return accounts

    def _post_instagram_carousel(self, account, instagram_business_account, images, access_token):
        """Publish multiple images as an Instagram carousel post: one child
        container per image (is_carousel_item=true), then a parent
        media_type=CAROUSEL container referencing all children, then publish
        - same return contract as _post_instagram_single_account (None on
        success, error message string on failure)."""
        media_url = f'{account.instagram_base_url}/{instagram_business_account}/media'
        child_ids = []
        for img in images:
            child_res = requests.post(media_url, data={
                'image_url': img.public_url,
                'is_carousel_item': 'true',
                'access_token': access_token,
            }, timeout=30)
            child_result = json.loads(child_res.text)
            if 'id' not in child_result:
                return (child_result.get('error', {}).get('message') if child_result.get('error')
                        else _('Failed to create one of the Instagram carousel items.'))
            child_ids.append(child_result['id'])

        self.env.cr.commit()
        parent_res = requests.post(media_url, data={
            'media_type': 'CAROUSEL',
            'children': ','.join(child_ids),
            'caption': self.description or '',
            'access_token': access_token,
        }, timeout=30)
        parent_result = json.loads(parent_res.text)
        if 'id' not in parent_result:
            return (parent_result.get('error', {}).get('message') if parent_result.get('error')
                    else _('Failed to create the Instagram carousel container.'))

        publish_url = f'{account.instagram_base_url}/{instagram_business_account}/media_publish'
        publish_res = requests.post(publish_url, data={
            'creation_id': parent_result['id'],
            'access_token': access_token,
        }, timeout=30)
        publish_result = json.loads(publish_res.text)
        if publish_result.get('error'):
            return publish_result['error'].get('message') or _("Unknown Instagram API error.")
        self.write({
            'posted_image_url': images[0].public_url,
            'posted_on_ig': True,
            'ig_media_number': publish_result['id'],
            'ig_posted_account_ids': [(4, account.id)],
        })
        return None

    def _post_instagram_single_account(self, account):
        """Post to exactly one Instagram account (2-step container-then-publish
        flow). Returns None on success (writes posted_image_url/posted_on_ig/
        ig_media_number/ig_posted_account_ids itself), or an error message
        string on failure - never raises for per-account API failures, so one
        account's failure can't stop the rest of the loop in action_post from
        being attempted. A ValidationError about the post's OWN content
        (wrong attachment mimetype) is not per-account and is raised by the
        caller instead, before this is ever called."""
        page_id = account.facebook_insta_page_number
        access_token = account.instagram_access_token
        business_account = (f'{account.instagram_base_url}/{page_id}?fields=instagram_business_account'
                            f'&access_token={access_token}')
        res = requests.get(business_account, timeout=30).json()
        if res.get('error'):
            return res['error'].get('message') or _("Unknown Instagram API error.")
        instagram_business_account = res['instagram_business_account']['id']
        post_url = f'{account.instagram_base_url}/{instagram_business_account}/media'

        carousel_images = (
            self.instagram_attachment_ids.filtered(lambda a: a.mimetype in IMAGE_MIMETYPES)
            if self.mode == 'photo' else self.env['ir.attachment']
        )
        if len(carousel_images) > 1:
            return self._post_instagram_carousel(account, instagram_business_account, carousel_images, access_token)

        is_video = False
        if self.mode in ('photo', 'video'):
            is_video = self.instagram_attachment_id.mimetype in VIDEO_MIMETYPES
            if is_video:
                payload = {
                    'video_url': self.instagram_attachment_id.public_url,
                    'media_type': 'REELS',
                    'caption': self.description,
                    'access_token': access_token
                }
            else:
                payload = {
                    'image_url': self.instagram_attachment_id.public_url,
                    'caption': self.description,
                    'access_token': access_token
                }
            post_image_url = self.instagram_attachment_id.public_url
        else:
            payload = {
                'image_url': self.post_url,
                'caption': self.description if self.description else "",
                'access_token': access_token
            }
            post_image_url = self.post_url
        if self.mode in ('photo', 'video'):
            self.env.cr.commit()
        r = requests.post(post_url, data=payload, timeout=30)
        result = json.loads(r.text)
        if 'id' not in result:
            return (result.get('error', {}).get('message') if result.get('error')
                    else _('Failed to create Instagram media container.'))
        creation_id = result['id']
        if is_video:
            status_url = f'{account.instagram_base_url}/{creation_id}'
            for _attempt in range(VIDEO_STATUS_POLL_ATTEMPTS):
                status_result = requests.get(status_url, params={
                    'fields': 'status_code',
                    'access_token': access_token,
                }, timeout=30).json()
                status_code = status_result.get('status_code')
                if status_code == 'FINISHED':
                    break
                if status_code == 'ERROR':
                    return _('Instagram failed to process the video.')
                time.sleep(VIDEO_STATUS_POLL_INTERVAL)
            else:
                return _('Timed out waiting for Instagram to finish processing the video.')
        publish_url = f'{account.instagram_base_url}/{instagram_business_account}/media_publish'
        second_payload = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        image_publish = requests.post(publish_url, data=second_payload, timeout=30)
        publish_result = json.loads(image_publish.text)
        if publish_result.get('error'):
            return publish_result['error'].get('message') or _("Unknown Instagram API error.")
        ig_media_number = publish_result['id']
        self.write({
            'posted_image_url': post_image_url,
            'posted_on_ig': True,
            'ig_media_number': ig_media_number,
            'ig_posted_account_ids': [(4, account.id)],
        })
        return None

    def _reset_platform_retry_state(self):
        super()._reset_platform_retry_state()
        self.write({'ig_posted_account_ids': [(5, 0, 0)]})

    def action_post(self):
        """
        Inherited to post the Message and attached image in Social Post to Instagram Publishing image to instagram is
        a two-step process.
        1. Create a Container, which means uploading the image and message. It will return a container ID.
        2. Publishing the Container. In this step, the container ID returned in the previous
        step will be published.
        So that the image and message will be visible on the Instagram account
        """
        try:
            if self.post_on_instagram and self.company_id and not self.insta_account_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No Instagram account selected to post to."),
                        'type': 'warning',
                    },
                }
            errors = []
            for account in self.insta_account_ids.sudo():
                if account in self.ig_posted_account_ids:
                    continue
                if self.company_id and self.post_on_instagram:
                    error = self._post_instagram_single_account(account)
                    if error:
                        errors.append(_("%s: %s") % (account.facebook_insta_page_name, error))
                elif (self.mode in ('photo', 'video') and self.company_id and self.ir_attachment_ids and
                      not self.instagram_attachment_id):
                    raise ValidationError(_('Only .jpg/.png images or .mp4/.mov videos can be posted on '
                                             'Instagram.'))
            if errors:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "\n".join(errors),
                        'type': 'warning',
                    },
                }
            return super().action_post()
        except ValidationError as ve:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': ve.args[0] if ve.args else str(ve),
                    'type': 'warning',
                },
            }
        except Exception:
            _logger.exception("Instagram action_post failed for post id=%s", self.id)
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

    @api.model
    def get_insta_feed_data(self, account_res_id=None, **kwargs):
        """Live browse of a connected Instagram account's own media library
        (Instagram's own content, not tied to any social.media.post record).
        Defaults to the configured default account when account_res_id isn't
        given (legacy Timeline callers)."""
        try:
            load_more_url = kwargs.get('loadMore')
            if account_res_id:
                insta_account_id = self.env['social.insta.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_insta_account.default_insta_account_id'
                )
                insta_account_id = self.env['social.insta.account'].sudo().browse(int(default_id))
            ig_user_id = insta_account_id.instagram_business_account_number
            access_token = insta_account_id.instagram_access_token

            user_info_url = f"https://graph.facebook.com/v20.0/{ig_user_id}?fields=profile_picture_url,username&access_token={access_token}"
            user_info = requests.get(user_info_url, timeout=30).json()
            profile_pic = user_info.get("profile_picture_url", "")

            feeds_api = (
                f"https://graph.facebook.com/v20.0/{ig_user_id}/media?"
                f"fields=id,caption,media_type,media_url,permalink,timestamp,username,"
                f"like_count,comments_count,children{{media_url,media_type}}&"
                f"limit=5&access_token={access_token}"
            )
            if load_more_url:
                feeds_api = load_more_url

            res = requests.get(feeds_api, timeout=30).json()
            for post in res.get("data", []):
                post["profile_picture_url"] = profile_pic

            return res

        except Exception as e:
            _logger.exception("Instagram get_insta_feed_data failed for account_res_id=%s", account_res_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f"Instagram Feed Error: {str(e)}",
                    'type': 'warning',
                },
            }

    @api.model
    def get_instagram_hashtag_media(self, account_res_id, hashtag, kind, cursor=None):
        """Live, read-only fetch of public media tagged with a hashtag.
        kind = 'recent' or 'top'. Two-step Graph API flow: resolve the hashtag
        text to an id via ig_hashtag_search (this step counts against Meta's
        30-unique-hashtags-per-account-per-7-days cap), then fetch
        recent_media/top_media for that id. Never writes to Odoo."""
        try:
            account = self.env['social.insta.account'].sudo().browse(int(account_res_id))
            ig_user_id = account.instagram_business_account_number
            access_token = account.instagram_access_token
            if cursor:
                media_url = cursor
            else:
                search_url = (
                    f"{account.instagram_base_url}/ig_hashtag_search"
                    f"?user_id={ig_user_id}&q={hashtag}&access_token={access_token}"
                )
                search_res = requests.get(search_url, timeout=10).json()
                if search_res.get('error'):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'message': _(search_res.get('error')['message']), 'type': 'warning'},
                    }
                hashtag_data = search_res.get('data', [])
                if not hashtag_data:
                    return {'items': [], 'cursor': None}
                hashtag_id = hashtag_data[0]['id']
                edge = 'recent_media' if kind == 'recent' else 'top_media'
                media_url = (
                    f"{account.instagram_base_url}/{hashtag_id}/{edge}"
                    f"?user_id={ig_user_id}"
                    f"&fields=id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"
                    f"&access_token={access_token}"
                )
            media_res = requests.get(media_url, timeout=10).json()
            if media_res.get('error'):
                error = media_res.get('error', {})
                message = error.get('message', '')
                if error.get('code') == 4 or 'limit' in message.lower():
                    message = _("Instagram's hashtag search limit (30 unique hashtags per account every "
                                "7 days) has been reached for this account.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': message, 'type': 'warning'},
                }
            items = []
            for media in media_res.get('data', []):
                is_video = media.get('media_type') == 'VIDEO'
                items.append({
                    'id': media.get('id'),
                    'item_kind': 'post',
                    'author_name': account.facebook_insta_page_name,
                    'author_avatar_url': account.profile_picture_url or False,
                    'text': media.get('caption', ''),
                    'image_url': media.get('media_url') if not is_video else False,
                    'video_url': media.get('media_url') if is_video else False,
                    'permalink': media.get('permalink'),
                    'posted_date': self.env['social.stream.column']._parse_date(media.get('timestamp')),
                    'like_count': media.get('like_count', 0),
                    'comment_count': media.get('comments_count', 0),
                })
            return {'items': items, 'cursor': media_res.get('paging', {}).get('next')}
        except Exception:
            _logger.exception("Instagram get_instagram_hashtag_media failed for account_res_id=%s, hashtag=%s",
                               account_res_id, hashtag)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that your "
                                 "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_fetch_data_from_ig_feed(self):
        """Fetch commenter contacts for this Instagram post."""
        try:
            comments_result = self.get_ig_comments_data(self.ig_media_number, self.insta_account_ids[:1], None)
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            access_token = self.insta_account_ids[:1].sudo().instagram_access_token
            partners = self.env['res.partner'].search([]).mapped(
                'unique_ig_number')
            partner_count = 0
            if comments_result.get('comments'):
                for comment in comments_result['comments']['data']:
                    url = (
                        f"{self.insta_account_ids[:1].instagram_base_url}/{comment['id']}?fields=id,from"
                        f"&access_token={access_token}")
                    comment_details = requests.get(url, timeout=30).json()
                    user_id = comment_details['from']['id']
                    url = (f"{self.insta_account_ids[:1].instagram_base_url}/{user_id}"
                           f"?fields=id,name&access_token={access_token}")
                    user = requests.get(url, timeout=30).json()
                    if user.get('id') and user['id'] not in partners:
                        partner_count += 1
                        self.env['res.partner'].create({
                            'name': user['name'],
                            'unique_ig_number': user['id'],
                            'insta_account_id': self.insta_account_ids[:1].id,
                            'post_id': self.id,
                        })
                        partners.append(user['id'])
                if partner_count == 0:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("No new contacts to save"),
                            'type': 'warning',
                        },
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _("%s new contact saved",
                                         ', '.join(str(partner_count))),
                            'type': 'success',
                        },
                    }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No new contacts to save"),
                        'type': 'warning',
                    },
                }
        except Exception:
            _logger.exception("Instagram action_fetch_data_from_ig_feed failed for post id=%s", self.id)
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

    def create_lead_ig(self, comment_data, title=None):
        """Convert an Instagram comment author into a res.partner/crm.lead."""
        partner = self.env['res.partner'].search(
            [('unique_ig_number', '=', comment_data['from']['id'])])
        lead = self.env['crm.lead'].search(
            [('unique_ig_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_ig_number': comment_data['from']['id'],
                'insta_account_id': self.insta_account_ids[:1].id,
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
                'unique_ig_comment_number': comment_data['id'],
                'campaign_id': self.campaign_id.id,
            }
        return values

    @api.model
    def get_ig_comments_data(self, feed, account, next_url):
        """Get Instagram comments associated with a media id."""
        try:
            account = account.sudo()
            if next_url:
                ig_comments_url = next_url
            else:
                ig_comments_url = \
                    (
                        f'{account.instagram_base_url}/{feed}/comments'
                        f'??fields=like_count,replies,message,from,created_time'
                        f'&limit=5&access_token={account.instagram_access_token}'
                    )

            comments_result = requests.get(ig_comments_url, timeout=30).json()

            return comments_result
        except Exception:
            _logger.exception("Instagram get_ig_comments_data failed for feed=%s", feed)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_instagram_comments(self):
        """Action to view Instagram comments associated with the post."""
        action = \
            self.env.ref('cyllo_instagram.action_instagram_comment').read()[0]
        return action

    @api.model
    def get_instagram_comments(self, **kwargs):
        """
        Function to fetch comment details of a post which will be displayed on clicking the Comments icon.
        """
        feed_id = kwargs.get('feed')
        next_url = kwargs.get('nextUrl', None)
        if kwargs.get('account_res_id'):
            account = self.env['social.insta.account'].sudo().browse(int(kwargs['account_res_id']))
        else:
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            account = self.env['social.insta.account'].sudo().browse(int(default_id))
        try:
            comments_result = self.get_ig_comments_data(feed_id, account, next_url)
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            comment_details_list = []
            if comments_result.get('data'):
                for comment in comments_result['data']:
                    comment_details_url = (
                        f'{account.instagram_base_url}/{comment["id"]}?fields=id,username,text,'
                        f'like_count,from,hidden,media,parent_id,timestamp'
                        f'&access_token={account.instagram_access_token}')
                    comment_details_result = requests.get(
                        comment_details_url, timeout=30).json()
                    partner_temp = self.env['res.partner'].sudo().search(
                        [('unique_fb_number', '=',
                          comment_details_result['from']['id'])])
                    reply_count_result = requests.get(
                        f'{account.instagram_base_url}/{comment["id"]}?fields=replies{{id}}&limit=50'
                        f'&access_token={account.instagram_access_token}', timeout=30).json()
                    comment_details_result.update(
                        {'timestamp': datetime.datetime.strptime(
                            comment_details_result['timestamp'],
                            '%Y-%m-%dT%H:%M:%S+0000').date(),
                         'partner_id': partner_temp.id  if partner_temp else None,
                         'reply_count': len(reply_count_result.get('replies', {}).get('data', [])),
                         'reply': [],
                         })
                    comment_details_list.append(comment_details_result)
            return {
                'data': comment_details_list,
                'paging': comments_result.get("paging", None),
            }
        except Exception:
            _logger.exception("Instagram get_instagram_comments failed for feed=%s", feed_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def get_instagram_comment_replies(self, **kwargs):
        """Lazy, paginated fetch of one comment's replies via Instagram's own
        /replies edge - only called when a user actually expands a comment's
        "N replies", instead of every comment's replies being resolved one
        HTTP request per reply upfront."""
        comment_id = kwargs.get('comment_id')
        cursor = kwargs.get('cursor')
        account_res_id = kwargs.get('account_res_id')
        try:
            if account_res_id:
                account = self.env['social.insta.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_insta_account.default_insta_account_id'
                )
                account = self.env['social.insta.account'].sudo().browse(int(default_id))
            if cursor:
                replies_url = cursor
            else:
                replies_url = (
                    f'{account.instagram_base_url}/{comment_id}/replies'
                    f'?fields=id,username,text,timestamp,like_count,from'
                    f'&limit=10&access_token={account.instagram_access_token}'
                )
            replies_result = requests.get(replies_url, timeout=10).json()
            if replies_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(replies_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            return {
                'data': replies_result.get('data', []),
                'paging': replies_result.get('paging'),
            }
        except Exception:
            _logger.exception("Instagram get_instagram_comment_replies failed for comment_id=%s", comment_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def post_instagram_comments(self, **kwargs):
        """Function to post comments to an Instagram post."""
        try:
            media_id = kwargs.get('feed')
            comment = kwargs.get('comment')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            account = self.env['social.insta.account'].sudo().browse(int(default_id))
            graph_url = f'{account.instagram_base_url}/'
            url = graph_url + media_id + '/comments'
            param = dict()
            param['message'] = comment
            param['access_token'] = account.instagram_access_token
            response = requests.post(url, params=param, timeout=30)
            response = response.json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response.get('error')['message']),
                        'type': 'warning',
                    },
                }

            reply_details_url = (
                f'{account.instagram_base_url}/{response["id"]}?fields=id,username,text,'
                f'timestamp&access_token={account.instagram_access_token}')
            details = requests.get(reply_details_url, timeout=30).json()
            return details
        except Exception:
            _logger.exception("Instagram post_instagram_comments failed for feed=%s", media_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_social_media_comments(self):
        """Action to view social media comments associated with the post."""
        if self.posted_on_ig:
            return self.action_instagram_comments()
        return super().action_social_media_comments()

    @api.model
    def post_instagram_reply(self, **kwargs):
        """Function to post replies to Instagram comments associated with the post."""
        try:
            comment_id = kwargs.get('comment')
            reply = kwargs.get('reply')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_insta_account.default_insta_account_id'
            )
            account = self.env['social.insta.account'].sudo().browse(int(default_id))
            graph_url = f'{account.instagram_base_url}/'
            url = graph_url + comment_id + '/replies?'
            param = dict()
            param['message'] = reply
            param['access_token'] = account.instagram_access_token
            response = requests.post(url, params=param, timeout=30)
            response = response.json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response.get('error')['message']),
                        'type': 'warning',
                    },
                }
            reply_details_url = (
                f'{account.instagram_base_url}/{response["id"]}?fields=id,username,text,'
                f'timestamp&access_token={account.instagram_access_token}')
            details = requests.get(reply_details_url, timeout=30).json()
            return details
        except Exception:
            _logger.exception("Instagram post_instagram_reply failed for comment_id=%s", comment_id)
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
        """Function to compute like and comment count of Instagram posts."""
        posts_ig = self.env['social.media.post'].search(
            [('ig_media_number', '!=', False)])
        try:
            for post in posts_ig:
                if post.posted_on_ig:
                    graph_url = 'https://graph.facebook.com/v18.0/'
                    media_id = post.ig_media_number
                    url = (
                            graph_url + media_id + '?fields=like_count,comments_count,' 'comments&access_token=%s'
                            % post.insta_account_ids[:1].sudo().instagram_access_token)
                    response = requests.get(url, timeout=30).json()
                    post.write({
                        'ig_likes_count': response.get('like_count', 0),
                        'ig_comments_count': len(response.get('comments', {}).get('data', [])),
                    })
            return super().action_compute_likes_count_all()
        except Exception:
            _logger.exception("Instagram action_compute_likes_count_all failed")
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
        """Compute the number of likes on the post for Instagram."""
        try:
            for post in self:
                if post.posted_on_ig:
                    graph_url = 'https://graph.facebook.com/v18.0/'
                    media_id = post.ig_media_number
                    url = (
                            graph_url + media_id + '?fields=like_count,comments_count,comments&access_token=%s' %
                            post.insta_account_ids[:1].sudo().instagram_access_token)
                    response = requests.get(url, timeout=30).json()
                    post.write({
                        'ig_likes_count': response.get('like_count', 0),
                        'ig_comments_count': len(response.get('comments', {}).get('data', [])),
                    })
                return {
                    'likes_count': post.ig_likes_count,
                    'comments_count': post.ig_comments_count,
                }
        except Exception:
            _logger.exception("Instagram action_compute_likes_count failed for post ids=%s", self.ids)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are "
                        "accurate and ensure that your device is connected to"
                        " the internet"),
                    'type': 'warning',
                },
            }
