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
import json
import logging
from collections import defaultdict

import requests
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SocialMediaPost(models.Model):
    """
    Inherits the social.media.post model to handle posts for different
    social media platforms.
    """
    _inherit = 'social.media.post'

    facebook_attachment_id = fields.Many2one(
        'ir.attachment', compute="_compute_facebook_attachment_id", string="Facebook Attachment to Post",
        help="The attachment ID related to the Facebook post.")
    facebook_attachment_ids = fields.Many2many(
        'ir.attachment', compute="_compute_facebook_attachment_id", string="Facebook Attachments to Post",
        help="All image attachments to post - more than one is published as a Facebook photo album/multi-photo post.")
    post_on_facebook = fields.Boolean(string="Post in Facebook", help="Enable this to post this post in facebook")
    fb_account_ids = fields.Many2many('social.fb.account', string="Facebook Accounts",
                                      help="Facebook connected accounts")
    fb_posted_account_ids = fields.Many2many(
        'social.fb.account', relation='social_media_post_fb_posted_account_rel',
        string="Facebook Accounts Already Posted", copy=False,
        help="Which of fb_account_ids already got a successful post - lets a "
             "retry (after a different account failed) skip accounts that "
             "already succeeded instead of posting to them a second time.")
    fb_media_number = fields.Char(string="Facebook Media ID", help="Unique id in facebook")
    posted_on_facebook = fields.Boolean(string="Posted in Facebook", readonly=True,
                                        help="Whether this post was actually published to Facebook.")
    fb_likes_count = fields.Integer(string="Facebook Likes", readonly=True)
    fb_comments_count = fields.Integer(string="Facebook Comments", readonly=True)

    def _compute_facebook_attachment_id(self):
        """Computes the attachment ID(s) for Facebook posts."""
        for post in self:
            images = self.env['ir.attachment']
            for attachment in post.ir_attachment_ids:
                safe_image = attachment.get_social_safe_image()
                if safe_image:
                    images |= safe_image
            images.write({'public': True})
            post.facebook_attachment_id = images[:1]
            post.facebook_attachment_ids = images

    def _get_platform_dashboard_tiles(self):
        tiles = super()._get_platform_dashboard_tiles()
        accounts = self.env['social.fb.account'].search([('state', '=', 'connected')])
        if not accounts:
            return tiles
        account_ids = accounts.ids
        account_id_set = set(account_ids)
        all_posts = self.search([('fb_account_ids', 'in', account_ids), ('state', '=', 'post')])
        posts_by_account = defaultdict(lambda: self.browse())
        for post in all_posts:
            for acc in post.fb_account_ids:
                if acc.id in account_id_set:
                    posts_by_account[acc.id] |= post
        audience_stats = self._get_audience_batch_stats('social.fb.account', account_ids)
        for account in accounts:
            posts = posts_by_account.get(account.id, self.browse())
            stats = audience_stats.get(account.id, {})
            baseline = stats.get('baseline')
            if baseline is None:
                baseline = account.followers_count
            tiles.append({
                'id': account.id,
                'account_name': account.facebook_page_name,
                'platform': 'social.fb.account',
                'total_posts': len(posts),
                'total_likes': sum(posts.mapped('fb_likes_count')),
                'total_comments': sum(posts.mapped('fb_comments_count')),
                'total_audience': account.followers_count,
                'account_image': account.profile_picture_url or False,
                'audience_baseline': baseline,
                'audience_delta': account.followers_count - baseline,
                'audience_history': stats.get('history', []),
            })
        return tiles

    def _get_recent_post_account_info(self, post):
        if post.posted_on_facebook and post.fb_account_ids:
            account = post.fb_account_ids[0]
            return account.facebook_page_name, account.profile_picture_url or False
        return super()._get_recent_post_account_info(post)

    def _get_calendar_platform_icon(self, post):
        if post.posted_on_facebook:
            return 'ri-facebook-fill'
        return super()._get_calendar_platform_icon(post)

    def _get_platform_permalink(self, platform_key):
        if platform_key == 'social.fb.account' and self.posted_on_facebook \
                and self.fb_media_number and '_' in self.fb_media_number:
            page_id, post_id = self.fb_media_number.split('_', 1)
            return f"https://www.facebook.com/{page_id}/posts/{post_id}"
        return super()._get_platform_permalink(platform_key)

    @api.model
    def get_connected_accounts(self):
        accounts = super().get_connected_accounts()
        for account in self.env['social.fb.account'].search([('state', '=', 'connected')]):
            accounts.append({
                'platform': 'social.fb.account',
                'id': account.id,
                'name': account.facebook_page_name,
                'avatar_url': account.profile_picture_url or False,
            })
        return accounts

    def _post_facebook_single_account(self, account):
        """Post to exactly one Facebook account. Returns None on success
        (writes fb_media_number/posted_image_url/posted_on_facebook/
        fb_posted_account_ids itself), or an error message string on
        failure - never raises, so one account's failure can't stop the
        rest of the loop in action_post from being attempted."""
        try:
            _logger.info("Facebook action_post: posting to account=%s page_id=%s",
                         account.id, account.facebook_page_number)
            if self.mode == 'photo' and not self.facebook_attachment_id:
                _logger.warning("Facebook action_post: post=%s aborted, attachment mode with no "
                                "jpg/jpeg/png attachment", self.id)
                return _("Attachment is empty or given attachment doesnt support. "
                         "Add a jpg/jpeg/png format attachment")
            page_id = account.facebook_page_number
            if self.mode == 'photo' and len(self.facebook_attachment_ids) > 1:
                photo_ids = []
                for img in self.facebook_attachment_ids:
                    upload_res = requests.post(
                        f"{account.facebook_base_url}/{page_id}/photos",
                        data={
                            'access_token': account.facebook_access_token,
                            'url': img.fb_public_url,
                            'published': 'false',
                        },
                        timeout=30,
                    )
                    upload_result = upload_res.json()
                    if not upload_result.get('id'):
                        _logger.warning("Facebook action_post: multi-photo upload failed for attachment=%s: %s",
                                        img.id, upload_result)
                        return (upload_result.get('error', {}).get('message')
                                if upload_result.get('error') else _("Failed to upload one of the photos."))
                    photo_ids.append(upload_result['id'])
                graph_url = f"{account.facebook_base_url}/{page_id}/feed"
                payload = {
                    'access_token': account.facebook_access_token,
                    'message': self.description or '',
                }
                for idx, photo_id in enumerate(photo_ids):
                    payload[f'attached_media[{idx}]'] = json.dumps({'media_fbid': photo_id})
                post_image_url = self.facebook_attachment_ids[0].fb_public_url
            elif self.mode == 'photo':
                graph_url = f"{account.facebook_base_url}/{page_id}/photos"
                payload = {
                    'access_token': account.facebook_access_token,
                    'url': self.facebook_attachment_id.fb_public_url,
                    'caption': self.description or '',
                    'published': 'true',
                }
                post_image_url = self.facebook_attachment_id.fb_public_url
            elif self.mode == 'content_only':
                graph_url = f"{account.facebook_base_url}/{page_id}/feed"
                payload = {
                    'access_token': account.facebook_access_token,
                    'message': self.description,
                }
                post_image_url = False
            else:
                graph_url = f"{account.facebook_base_url}/{page_id}/feed"
                payload = {
                    'access_token': account.facebook_access_token,
                    'message': self.description if self.description else "",
                    'link': self.post_url,
                }
                post_image_url = self.post_url
            if self.mode == 'photo':
                self.env.cr.commit()
            response = requests.post(graph_url, data=payload, timeout=30)
            _logger.info("Facebook action_post: %s POST status=%s body=%s",
                         graph_url, response.status_code, response.text[:1000])
            self._message_log(body=_('Facebook POST (%s) to page %s: %s') % (
                response.status_code, page_id, response.text[:500]))
            if response.json().get('error'):
                _logger.warning("Facebook action_post: POST returned error: %s",
                                response.json().get('error'))
                return response.json()['error'].get('message') or _("Unknown Facebook API error.")
            result = response.json()
            if 'id' not in result:
                _logger.warning("Facebook action_post: response had no 'id', response=%s", result)
                return _('Facebook did not return a post id — the post may not have been published.')
            fb_media_number = result.get('post_id') or result['id']
            _logger.info("Facebook action_post: published successfully, fb_media_number=%s", fb_media_number)
            self.write({
                'fb_media_number': fb_media_number,
                'posted_image_url': post_image_url,
                'posted_on_facebook': True,
                'fb_posted_account_ids': [(4, account.id)],
            })
            return None
        except Exception:
            _logger.exception("Facebook action_post: unhandled exception for post=%s account=%s",
                              self.id, account.id)
            return _("Check the internet connection.")

    def _reset_platform_retry_state(self):
        super()._reset_platform_retry_state()
        self.write({'fb_posted_account_ids': [(5, 0, 0)]})

    def action_post(self):
        """Posts content to the specified Facebook account(s)."""
        _logger.info("Facebook action_post: post=%s mode=%s accounts=%s post_on_facebook=%s",
                     self.id, self.mode, self.fb_account_ids.ids, self.post_on_facebook)
        if not self.post_on_facebook:
            return super().action_post()
        if not self.fb_account_ids:
            _logger.warning("Facebook action_post: post=%s has post_on_facebook=True but no "
                            "fb_account_ids selected", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("No Facebook account selected to post to."),
                    'type': 'warning',
                },
            }
        errors = []
        for account in self.fb_account_ids.sudo():
            if account in self.fb_posted_account_ids:
                continue
            error = self._post_facebook_single_account(account)
            if error:
                errors.append(_("%s: %s") % (account.facebook_page_name, error))
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

    @api.model
    def get_feed_data(self, account_res_id=None, **kwargs):
        """Live browse of a Facebook Page's own feed - reads straight from the
        Graph API, never stores anything in Odoo. Defaults to the configured
        default Page when account_res_id isn't given (legacy Timeline callers)."""
        try:
            load_more_url = kwargs.get('loadMore')
            if account_res_id:
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_fb_account.default_fb_account_id'
                )
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(default_id))
            page_id = fb_account_id.facebook_page_number
            page_access_token = fb_account_id.facebook_access_token
            url = fb_account_id.facebook_base_url
            feeds_api = (
                f"{url}/{page_id}/feed?"
                f"fields=created_time,from,id,message,"
                f"attachments{{media,type,subattachments{{media,type}}}},"
                f"likes.summary(true),"
                f"comments.summary(true){{id,message,from,comments.summary(true)}}&"
                f"limit=5&"
                f"access_token={page_access_token}"
            )
            if load_more_url:
                feeds_api = load_more_url
            res = requests.get(feeds_api, timeout=30).json()

            data = []
            for post in res.get('data', []):
                fb_media_number = post.get('id')
                if not fb_media_number:
                    continue
                post_image_url = False
                post_image_urls = []
                attachments = post.get('attachments', {}).get('data', [])
                if attachments:
                    subattachments = attachments[0].get('subattachments', {}).get('data', [])
                    if subattachments:
                        for sub in subattachments:
                            sub_media = sub.get('media', {})
                            if sub_media and sub_media.get('image'):
                                post_image_urls.append(sub_media['image'].get('src'))
                        post_image_url = post_image_urls[0] if post_image_urls else False
                    else:
                        media = attachments[0].get('media', {})
                        if media and media.get('image'):
                            post_image_url = media['image'].get('src')
                author_name = post.get('from', {}).get('name', 'Facebook Page')
                author_link = (
                    f"https://www.facebook.com/{fb_media_number.split('_')[0]}/posts/{fb_media_number.split('_')[1]}"
                    if '_' in fb_media_number else f"https://www.facebook.com/{fb_media_number}")
                posted_date = post.get('created_time')
                if posted_date:
                    try:
                        from dateutil import parser as date_parser
                        posted_date = date_parser.parse(posted_date).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
                data.append({
                    'id': fb_media_number,
                    'description': post.get('message', ''),
                    'author_name': author_name,
                    'author_link_url': author_link,
                    'posted_date': posted_date,
                    'posted_image_url': post_image_url,
                    'posted_image_urls': post_image_urls if len(post_image_urls) > 1 else False,
                    'profile_image_url': fb_account_id.profile_picture_url or False,
                    'likes_count': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'comments_count': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                })

            return {'data': data, 'paging': res.get('paging', {})}
        except Exception:
            _logger.exception("Facebook get_feed_data failed for account_res_id=%s", account_res_id)
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
    def get_facebook_mentions(self, account_res_id, cursor=None):
        """Live, read-only fetch of content the Page has been tagged in
        ('Mentions' stream). Needs pages_read_user_content on the page token -
        never writes to Odoo."""
        try:
            account = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            if cursor:
                url = cursor
            else:
                url = (
                    f"{account.facebook_base_url}/{account.facebook_page_number}/tagged"
                    f"?fields=created_time,from,id,message,permalink_url"
                    f"&limit=10&access_token={account.facebook_access_token}"
                )
            res = requests.get(url, timeout=10).json()
            if res.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(res.get('error')['message']), 'type': 'warning'},
                }
            items = []
            for post in res.get('data', []):
                items.append({
                    'id': post.get('id'),
                    'item_kind': 'post',
                    'author_name': post.get('from', {}).get('name', 'Facebook'),
                    'author_avatar_url': account.profile_picture_url or False,
                    'text': post.get('message', ''),
                    'permalink': post.get('permalink_url'),
                    'posted_date': self.env['social.stream.column']._parse_date(post.get('created_time')),
                })
            return {'items': items, 'cursor': res.get('paging', {}).get('next')}
        except Exception:
            _logger.exception("Facebook get_facebook_mentions failed for account_res_id=%s", account_res_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that your "
                                 "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def get_facebook_unpublished_posts(self, account_res_id, cursor=None):
        """Live, read-only fetch of the Page's unpublished/scheduled posts.
        Needs pages_read_engagement/pages_manage_posts on the page token -
        never writes to Odoo."""
        try:
            account = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            if cursor:
                url = cursor
            else:
                url = (
                    f"{account.facebook_base_url}/{account.facebook_page_number}/promotable_posts"
                    f"?is_published=false&fields=created_time,message,id"
                    f"&limit=10&access_token={account.facebook_access_token}"
                )
            res = requests.get(url, timeout=10).json()
            if res.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(res.get('error')['message']), 'type': 'warning'},
                }
            items = []
            for post in res.get('data', []):
                items.append({
                    'id': post.get('id'),
                    'item_kind': 'post',
                    'author_name': account.facebook_page_name,
                    'author_avatar_url': account.profile_picture_url or False,
                    'text': post.get('message', ''),
                    'posted_date': self.env['social.stream.column']._parse_date(post.get('created_time')),
                })
            return {'items': items, 'cursor': res.get('paging', {}).get('next')}
        except Exception:
            _logger.exception("Facebook get_facebook_unpublished_posts failed for account_res_id=%s", account_res_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that your "
                                 "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_facebook_comments(self):
        """Action to view Facebook comments associated with the post."""
        action = self.env.ref('cyllo_facebook.action_facebook_comment').read()[0]
        return action

    def create_lead(self, comment_data, title=None):
        """Convert a Facebook comment author into a res.partner/crm.lead."""
        partner = self.env['res.partner'].search(
            [('unique_fb_number', '=', comment_data['userid'])])
        lead = self.env['crm.lead'].search([('unique_fb_comment_number', '=', comment_data['id'])])
        if not partner:
            partner = self.env['res.partner'].create({
                'name': comment_data['username'],
                'unique_fb_number': comment_data['userid'],
                'fb_account_id': self.fb_account_ids[:1].id,
                'post_id': self.id,
            })
        values = {
            'name': self.name if self.name else title,
            'type': 'lead',
            'user_id': self.env.user.id,
            'partner_id': partner.id,
            'contact_name': partner.name,
            'lead': False,
            'unique_fb_comment_number': comment_data['id'],
            'campaign_id': self.campaign_id.id,
        } if not lead else {'lead': lead.id}
        return values

    def action_fetch_data_from_feed(self):
        """Fetch commenter contacts for the default Facebook account's posts."""
        try:
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            fb_account_id = self.env['social.fb.account'].sudo().browse(int(default_id))
            comments_result = self.get_comments_data(self.fb_media_number, None)
            if comments_result.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(comments_result.get('error')['message']),
                        'type': 'warning',
                    },
                }
            access_token = fb_account_id.facebook_access_token
            partners = self.env['res.partner'].search([]).mapped('unique_fb_number')
            partner_count = 0
            for comment in comments_result['data']:
                user_id = comment['from']['id']
                url = (
                    f"{fb_account_id.facebook_base_url}/{user_id}?fields=id,name,picture&access_token="
                    f"{access_token}")
                user = requests.get(url, timeout=30).json()
                image_url = user['picture']['data']['url']
                image = base64.b64encode(
                    requests.get(image_url, timeout=30).content).decode('utf-8')
                if user['id'] not in partners:
                    self.env['res.partner'].create({
                        'name': user['name'],
                        'unique_fb_number': user['id'],
                        'post_id': self.id,
                        'fb_account_id': fb_account_id.id,
                        'image_1920': image
                    })
                    partner_count += 1
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
        except Exception:
            _logger.exception("Facebook action_fetch_data_from_feed failed for post=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def get_comments_data(self, post_media_id, next_url, account_res_id=None):
        """Function to retrieve comments data from a Facebook post."""
        try:
            if account_res_id:
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_fb_account.default_fb_account_id'
                )
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(default_id))
            page_access_token = fb_account_id.facebook_access_token
            url = fb_account_id.facebook_base_url

            if next_url:
                comments_url = next_url
            else:
                comments_url = (
                    f"{url}/{post_media_id}/comments"
                    f"?fields=can_remove,like_count,message,from,created_time"
                    f"&limit=5&access_token={page_access_token}"
                )

            comments_result = requests.get(comments_url, timeout=10).json()
            for comment in comments_result.get('data', []):
                count_res = requests.get(
                    f"{url}/{comment['id']}?fields=comments.summary(true).limit(1)"
                    f"&access_token={page_access_token}",
                    timeout=10,
                ).json()
                comment['reply_count'] = count_res.get('comments', {}).get('summary', {}).get('total_count', 0)
            return comments_result
        except Exception:
            _logger.exception("Facebook get_comments_data failed for post_media_id=%s account_res_id=%s",
                              post_media_id, account_res_id)
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
    def get_facebook_comments(self, **kwargs):
        post_media_id = kwargs.get('feed')
        next_url = kwargs.get('nextUrl', None)
        comments_result = self.get_comments_data(post_media_id, next_url, account_res_id=kwargs.get('account_res_id'))
        if comments_result.get('error'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(comments_result.get('error')['message']),
                    'type': 'warning',
                },
            }
        if comments_result.get('data'):
            comment_details_list = []
            for comment in comments_result['data']:
                comment_details = {
                    'id': comment['id'],
                    'type': "fb",
                    'username': comment.get('from', {}).get('name', 'Facebook User'),
                    'userid': comment.get('from', {}).get('id', '0'),
                    'text': comment.get('message', ''),
                    'like_count': comment.get('like_count', 0),
                    'can_remove': comment.get('can_remove', False),
                    'created_time': self.env['social.stream.column']._parse_date(comment.get('created_time')),
                    'reply_count': comment.get('reply_count', 0),
                    'partner_id': 0,
                }
                comment_details_list.append(comment_details)
            return {
                'data': comment_details_list,
                'paging': comments_result.get("paging", None),
            }
        return []

    @api.model
    def get_facebook_comment_replies(self, **kwargs):
        """Lazy, paginated fetch of one comment's replies - only called when
        a user actually expands a comment's "N replies", instead of every
        comment's replies being fetched upfront with the comment itself."""
        comment_id = kwargs.get('comment_id')
        cursor = kwargs.get('cursor')
        account_res_id = kwargs.get('account_res_id')
        try:
            if account_res_id:
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_fb_account.default_fb_account_id'
                )
                fb_account_id = self.env['social.fb.account'].sudo().browse(int(default_id))
            page_access_token = fb_account_id.facebook_access_token
            if cursor:
                replies_url = cursor
            else:
                replies_url = (
                    f"{fb_account_id.facebook_base_url}/{comment_id}/comments"
                    f"?fields=can_remove,message,from,created_time,like_count,"
                    f"comments.limit(5){{can_remove,message,from,created_time,like_count}}"
                    f"&limit=5&access_token={page_access_token}"
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
            _logger.exception("Facebook get_facebook_comment_replies failed, kwargs=%s", kwargs)
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
    def post_facebook_comments(self, **kwargs):
        try:
            media_id = kwargs.get('feed')
            comment = kwargs.get('comment')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            account = self.env['social.fb.account'].sudo().browse(int(default_id))
            graph_url = account.facebook_base_url
            url = f"{graph_url}/{media_id}/comments"
            params = {
                'message': comment,
                'access_token': account.facebook_access_token
            }
            response = requests.post(url, data=params, timeout=30)
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
            details = requests.get(
                f"{account.facebook_base_url}/{response.get('id')}?fields=id,message,from,created_time,like_count&access_token={account.facebook_access_token}",
                timeout=30,
            ).json()
            return details
        except Exception:
            _logger.exception("Facebook post_facebook_comments failed, kwargs=%s", kwargs)
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

    @api.model
    def delete_facebook_comment(self, **kwargs):
        """Function to delete a Facebook comment or reply via the Graph API."""
        try:
            comment_id = kwargs.get('comment_id')
            if not self.env.user.has_group('cyllo_social_media_marketing.group_social_media_user'):
                return {'error': 'Permission Denied'}

            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            account = self.env['social.fb.account'].sudo().browse(int(default_id))
            graph_url = f"{account.facebook_base_url}/{comment_id}?access_token={account.facebook_access_token}"

            response = requests.delete(graph_url, timeout=30)
            response_data = response.json()

            if response_data.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response_data.get('error')['message']),
                        'type': 'warning',
                    },
                }
            return {'success': True}
        except Exception:
            _logger.exception("Facebook delete_facebook_comment failed, kwargs=%s", kwargs)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Failed to delete the comment. Please ensure your device "
                        "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_social_media_comments(self):
        """Action to view social media comments associated with the post."""
        if self.posted_on_facebook:
            return self.action_facebook_comments()
        return super().action_social_media_comments()

    @api.model
    def post_facebook_reply(self, **kwargs):
        """Function to post replies to Facebook comments associated with the post."""
        try:
            comment_id = kwargs.get('comment')
            reply = kwargs.get('reply')
            default_id = self.env['ir.config_parameter'].sudo().get_param(
                'social_fb_account.default_fb_account_id'
            )
            account = self.env['social.fb.account'].sudo().browse(int(default_id))
            access_token = account.facebook_access_token
            graph_url = f'{account.facebook_base_url}/{comment_id}/comments?access_token={access_token}'
            params = {'message': reply}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(graph_url, params=params, headers=headers, timeout=30)
            response_data = response.json()
            if response_data.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response_data.get('error')['message']),
                        'type': 'warning',
                    },
                }
            details_url = f"{account.facebook_base_url}/{response_data.get('id')}"
            details_params = {
                "fields": "id,message,from,created_time,like_count",
                "access_token": access_token,
            }
            details = requests.get(details_url, params=details_params, timeout=30).json()
            return details
        except Exception:
            _logger.exception("Facebook post_facebook_reply failed, kwargs=%s", kwargs)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your device"
                        " is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def post_facebook_like(self, **kwargs):
        """Like a Facebook post via the Graph API (POST /{post-id}/likes) -
        needs pages_manage_engagement on the page token."""
        try:
            post_id = kwargs.get('post_id')
            account_res_id = kwargs.get('account_res_id')
            if account_res_id:
                account = self.env['social.fb.account'].sudo().browse(int(account_res_id))
            else:
                default_id = self.env['ir.config_parameter'].sudo().get_param(
                    'social_fb_account.default_fb_account_id'
                )
                account = self.env['social.fb.account'].sudo().browse(int(default_id))
            url = f"{account.facebook_base_url}/{post_id}/likes"
            response = requests.post(url, data={'access_token': account.facebook_access_token}, timeout=30).json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _(response.get('error')['message']),
                        'type': 'warning',
                    },
                }
            return {'success': True}
        except Exception:
            _logger.exception("Facebook post_facebook_like failed, kwargs=%s", kwargs)
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

    def action_compute_likes_count_all(self):
        posts_fb = self.env['social.media.post'].search(
            [('fb_media_number', '!=', False)])
        try:
            for post in posts_fb:
                account = post.fb_account_ids.sudo()[:1]
                access_token = account.facebook_access_token
                if post.fb_media_number and post.posted_on_facebook:
                    graph_url = f"{account.facebook_base_url}/{post.fb_media_number}/likes?access_token={access_token}"
                    response = requests.get(graph_url, timeout=30).json()
                    graph_url = (
                        f"{account.facebook_base_url}/{post.fb_media_number}/comments?access_token="
                        f"{access_token}")
                    data = requests.get(graph_url, timeout=30).json()
                    post.write({
                        'fb_likes_count': len(response.get('data')) if response.get('data') else 0,
                        'fb_comments_count': len(data.get('data')) if data.get('data') else 0,
                    })
            return super().action_compute_likes_count_all()
        except Exception:
            _logger.exception("Facebook action_compute_likes_count_all failed for post=%s", self.id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }

    @api.model
    def action_compute_fb_likes_count(self, **kwargs):
        """Function to compute the count of likes associated with the post."""
        try:
            feed_id = kwargs.get('feed')
            if feed_id:
                posts = self.search([('fb_media_number', '=', feed_id)], limit=1)
            else:
                posts = self.search([('fb_media_number', '!=', False)])
            for post in posts:
                account = post.fb_account_ids.sudo()[:1]
                access_token = account.facebook_access_token
                if post.fb_media_number and post.posted_on_facebook:
                    graph_url = (
                        f"{account.facebook_base_url}/{post.fb_media_number}?fields=likes.summary(true)"
                        f"&access_token={access_token}")
                    likes = requests.get(graph_url, timeout=30).json()
                    graph_url = (
                        f"{account.facebook_base_url}/{post.fb_media_number}/comments"
                        f"?summary=true&filter=stream&access_token={access_token}"
                    )
                    comments = requests.get(graph_url, timeout=30).json()
                    post.write({
                        'fb_likes_count': int(
                            likes.get("likes", {}).get("summary", {}).get("total_count", 0))
                            if likes.get('likes') else 0,
                        'fb_comments_count': int(
                            comments.get("summary", {}).get("total_count", 0))
                            if comments.get('data') else 0,
                    })
        except Exception:
            _logger.exception("Facebook action_compute_fb_likes_count failed, kwargs=%s", kwargs)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Please verify that the provided credentials are accurate and ensure that your "
                        "device is connected to the internet"),
                    'type': 'warning',
                },
            }
