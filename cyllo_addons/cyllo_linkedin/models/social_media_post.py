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

from odoo.addons.cyllo_social_media_marketing.models.social_media_post import PLATFORM_REGISTRY

_logger = logging.getLogger(__name__)

PLATFORM_REGISTRY['linkedin.account'] = {
    'module': 'cyllo_linkedin',
    'connect_method': 'action_connect_linkedin',
    'returns_id': True,
}


class SocialMediaPost(models.Model):
    """Class to define the fields and functions for social media posts."""
    _inherit = ['social.media.post']


    linkedin_organization_ids = fields.Many2many('linkedin.organization',
                                                 string="LinkedIn Pages",
                                                 help="Specific LinkedIn organization pages to post to.")
    linkedin_posted_org_ids = fields.Many2many(
        'linkedin.organization', relation='social_media_post_linkedin_posted_org_rel',
        string="LinkedIn Pages Already Posted", copy=False,
        help="Which of linkedin_organization_ids already got a successful post "
             "- lets a retry (after a different page failed) skip pages that "
             "already succeeded instead of posting to them a second time.")
    linkedin_post_urn = fields.Char(copy=False, readonly=True,
                                    help="The id LinkedIn returned for the published post - "
                                         "lets Open on LinkedIn link straight to it.")
    linkedin_content_type = fields.Selection([
        ('text', 'Text Only'),
        ('image', 'Image'),
        ('poll', 'Poll'),
    ], string="LinkedIn Content Type", default='text',
        help="Type of content to post on LinkedIn.")
    linkedin_poll_question = fields.Char(string="Poll Question",
                                         help="Question for the LinkedIn poll.")
    linkedin_poll_option_1 = fields.Char(string="Option 1")
    linkedin_poll_option_2 = fields.Char(string="Option 2")
    linkedin_poll_option_3 = fields.Char(string="Option 3 (optional)")
    linkedin_poll_option_4 = fields.Char(string="Option 4 (optional)")
    linkedin_poll_duration = fields.Selection([
        ('ONE_DAY', '1 Day'),
        ('THREE_DAYS', '3 Days'),
        ('SEVEN_DAYS', '7 Days'),
        ('FOURTEEN_DAYS', '14 Days'),
    ], string="Poll Duration", default='THREE_DAYS')

    _MODE_TO_LINKEDIN_CONTENT_TYPE = {'photo': 'image', 'content_only': 'text', 'poll': 'poll'}

    @api.onchange('mode')
    def _onchange_mode_linkedin(self):
        content_type = self._MODE_TO_LINKEDIN_CONTENT_TYPE.get(self.mode)
        if content_type:
            self.linkedin_content_type = content_type

    def _get_platform_dashboard_tiles(self):
        tiles = super()._get_platform_dashboard_tiles()
        orgs = self.env['linkedin.organization'].search([('state', '=', 'active')])
        if not orgs:
            return tiles
        org_ids = orgs.ids
        org_id_set = set(org_ids)
        all_posts = self.search([('linkedin_organization_ids', 'in', org_ids), ('state', '=', 'post')])
        posts_by_org = defaultdict(lambda: self.browse())
        for post in all_posts:
            for org_rec in post.linkedin_organization_ids:
                if org_rec.id in org_id_set:
                    posts_by_org[org_rec.id] |= post
        audience_stats = self._get_audience_batch_stats('linkedin.organization', org_ids)
        for org in orgs:
            posts = posts_by_org.get(org.id, self.browse())
            stats = audience_stats.get(org.id, {})
            baseline = stats.get('baseline')
            if baseline is None:
                baseline = org.followers_count
            tiles.append({
                'id': org.account_id.id,
                'account_name': org.name,
                'platform': 'linkedin.account',
                'total_posts': len(posts),
                'total_likes': sum(getattr(post, 'linkedin_likes_count', 0) for post in posts),
                'total_comments': sum(getattr(post, 'linkedin_comments_count', 0) for post in posts),
                'total_audience': org.followers_count,
                'account_image': org.logo_url or False,
                'audience_baseline': baseline,
                'audience_delta': org.followers_count - baseline,
                'audience_history': stats.get('history', []),
            })
        return tiles

    def _get_recent_post_account_info(self, post):
        if post.posted_on_linkedin and post.linkedin_organization_ids:
            org = post.linkedin_organization_ids[0]
            return org.name, org.logo_url or False
        return super()._get_recent_post_account_info(post)

    def _get_calendar_platform_icon(self, post):
        if post.posted_on_linkedin:
            return 'ri-linkedin-fill'
        return super()._get_calendar_platform_icon(post)

    def _get_platform_permalink(self, platform_key):
        if platform_key == 'linkedin.account' and self.posted_on_linkedin and self.linkedin_post_urn:
            return f"https://www.linkedin.com/feed/update/{self.linkedin_post_urn}"
        return super()._get_platform_permalink(platform_key)

    @api.model
    def get_connected_accounts(self):
        """ One tile per managed PAGE, not per OAuth connection - one
        LinkedIn login can admin several pages, and a post is published as a
        specific page (linkedin_organization_ids), not "the account" itself. """
        accounts = super().get_connected_accounts()
        for org in self.env['linkedin.organization'].search([('state', '=', 'active')]):
            accounts.append({
                'platform': 'linkedin.organization',
                'id': org.id,
                'name': org.name,
                'avatar_url': org.logo_url or False,
            })
        return accounts

    def _reset_platform_retry_state(self):
        super()._reset_platform_retry_state()
        self.write({'linkedin_posted_org_ids': [(5, 0, 0)]})

    def action_post(self):
        """Function to post to LinkedIn."""
        failed_posts = self.browse()

        for post in self:
            linkedin_success = True
            if post.posted_on_linkedin and not post.linkedin_organization_ids:
                _logger.warning("LinkedIn post=%s has posted_on_linkedin=True but no "
                                "linkedin_organization_ids selected", post.id)
                linkedin_success = False
            elif post.posted_on_linkedin:
                orgs_to_try = post.linkedin_organization_ids.sudo() - post.linkedin_posted_org_ids.sudo()
                for org in orgs_to_try:
                    account = org.account_id
                    if not account.linkedin_access_token or not org.org_urn:
                        _logger.warning(f"LinkedIn organization {org.name} missing token or URN.")
                        linkedin_success = False
                        continue

                    url = 'https://api.linkedin.com/v2/ugcPosts'
                    headers = {
                        'Authorization': f'Bearer {account.linkedin_access_token}',
                        'X-Restli-Protocol-Version': '2.0.0',
                        'Content-Type': 'application/json',
                    }

                    owner_urn = org.org_urn
                    _logger.info(f"Posting to LinkedIn with author URN: {owner_urn}")

                    payload = {
                        "author": owner_urn,
                        "lifecycleState": "PUBLISHED",
                        "specificContent": {
                            "com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {
                                    "text": post.description
                                },
                                "shareMediaCategory": "NONE"
                            }
                        },
                        "visibility": {
                            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                        }
                    }

                    if post.mode == 'url' and post.post_url:
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                            "status": "READY",
                            "originalUrl": post.post_url,
                            "title": { "text": post.name }
                        }]

                    try:
                        content_type = post.linkedin_content_type or 'text'
                        if content_type == 'image':
                            response = self._post_linkedin_image(post, org, account, headers)
                        elif content_type == 'poll':
                            response = self._post_linkedin_poll(post, org, account, headers)
                        else:
                            response = self._post_linkedin_text(post, org, headers)

                        restli_id = response.headers.get('x-restli-id')
                        success_codes = [200, 201]
                        if response.status_code in success_codes:
                            result = response.json() if response.text else {}
                            post_id = result.get('id') or restli_id
                            self._message_log(body=_("Successfully posted to LinkedIn (%s)") % org.name)
                            post.write({'linkedin_posted_org_ids': [(4, org.id)], 'linkedin_post_urn': post_id})
                        else:
                            linkedin_success = False
                            error_msg = response.text
                            _logger.error(f"LinkedIn API error ({response.status_code}): {error_msg}")
                            self._message_log(body=_(
                                "Failed to post to LinkedIn (%s).\n"
                                "URN used: %s\n"
                                "Error: %s\n\n"
                                "TIP: If this is an organization page, ensure you have the 'w_organization_social' permission."
                            ) % (org.name, owner_urn, error_msg))
                    except Exception as e:
                        linkedin_success = False
                        _logger.exception("LinkedIn post exception")
                        self._message_log(body=_(f"Exception while posting to LinkedIn: {str(e)}"))

            if not linkedin_success:
                _logger.warning("LinkedIn post encountered errors.")
                failed_posts += post

        succeeded = self - failed_posts
        result = super(SocialMediaPost, succeeded).action_post() if succeeded else None
        if failed_posts:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Failed to post to LinkedIn for: %s") % ', '.join(failed_posts.mapped('name')),
                    'type': 'danger',
                },
            }
        return result

    def _post_linkedin_text(self, post, org, headers):
        """Helper method to post text-only content to LinkedIn."""
        url = 'https://api.linkedin.com/v2/ugcPosts'
        payload = {
            "author": org.org_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.description
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if post.mode == 'url' and post.post_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"][
                "shareMediaCategory"] = "ARTICLE"
            payload["specificContent"]["com.linkedin.ugc.ShareContent"][
                "media"] = [{
                "status": "READY",
                "originalUrl": post.post_url,
                "title": {"text": post.name}
            }]

        _logger.info("Posting LinkedIn Text/Article: %s", payload)
        return requests.post(url, headers=headers, json=payload, timeout=60)

    def _post_linkedin_image(self, post, org, account, headers):
        """Helper method to post images to LinkedIn."""
        images = post.ir_attachment_ids.filtered(lambda a: (a.mimetype or '').startswith('image/'))
        if not images:
            return self._post_linkedin_text(post, org, headers)
        media_assets = []
        for img in images:
            register_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": org.org_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            reg_res = requests.post(register_url, headers=headers,
                                    json=register_payload, timeout=30)
            if not reg_res.ok:
                return reg_res

            reg_data = reg_res.json()
            upload_url = reg_data.get('value', {}).get('uploadMechanism',
                                                       {}).get(
                'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest',
                {}).get('uploadUrl')
            asset_urn = reg_data.get('value', {}).get('asset')

            import base64
            image_content = base64.b64decode(img.datas)
            upload_headers = {'Authorization': headers['Authorization']}
            upload_res = requests.put(upload_url, headers=upload_headers,
                                      data=image_content, timeout=120)
            if not upload_res.ok:
                return upload_res

            media_assets.append({
                "status": "READY",
                "media": asset_urn,
                "title": {"text": img.name or "Image"}
            })

        url = 'https://api.linkedin.com/v2/ugcPosts'
        post_payload = {
            "author": org.org_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.description
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": media_assets
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        return requests.post(url, headers=headers, json=post_payload,
                             timeout=60)

    def _post_linkedin_poll(self, post, org, account, headers):
        """Helper method to post a poll to LinkedIn.
        Requires modern /rest/posts endpoint and LinkedIn-Version header.
        """
        url = 'https://api.linkedin.com/rest/posts'
        rest_headers = dict(headers)
        rest_headers.update({
            'LinkedIn-Version': '202602',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        })
        options = []
        for opt in [post.linkedin_poll_option_1, post.linkedin_poll_option_2,
                    post.linkedin_poll_option_3, post.linkedin_poll_option_4]:
            if opt and opt.strip():
                options.append({"text": opt.strip()})

        if len(options) < 2:
            raise ValueError("A poll must have at least 2 options.")
        duration = post.linkedin_poll_duration or 'THREE_DAYS'
        payload = {
            "author": org.org_urn,
            "commentary": post.description,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "content": {
                "poll": {
                    "question": post.linkedin_poll_question or post.description,
                    "options": options,
                    "settings": {
                        "duration": duration
                    }
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        _logger.info("Posting LinkedIn Poll: %s", payload)
        return requests.post(url, headers=rest_headers, json=payload,
                             timeout=60)

