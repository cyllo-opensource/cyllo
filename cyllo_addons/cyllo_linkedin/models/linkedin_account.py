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
import re
import secrets
import urllib.parse
from datetime import datetime

import requests
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from werkzeug.urls import url_encode, url_join

_logger = logging.getLogger(__name__)


class LinkedInAccount(models.Model):
    """
    Model representing a Social Media LinkedIn Account.
    """
    _name = "linkedin.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media LinkedIn Account"

    name = fields.Char(string="Name", required=True)
    username = fields.Char(string="Username",
                           help="Optional. Enter to autofill LinkedIn login page.")
    linkedin_access_token = fields.Char(string='Access Token',
                                        help='Access token for your linkedin app',
                                        groups='cyllo_social_media_marketing.group_social_media_administrator')
    state = fields.Selection(
        [('not connected', 'Not Connected'), ('connected', 'Connected')],
        required=True, default='not connected', tracking=True)
    linkedin_profile_image_url = fields.Char(string='Logo URL',
                                             help='LinkedIn Organization Logo URL')
    oauth_nonce = fields.Char(readonly=True, copy=False,
                              help="One-time random token proving the OAuth callback for this account "
                                   "was actually triggered by us - the old 'smm_<account_id>' state was "
                                   "just the account id with a prefix, letting any logged-in user rebind "
                                   "any account's LinkedIn identity by guessing its id (the callback "
                                   "writes via sudo(), bypassing normal ACLs). Cleared once consumed.")
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")
    last_sync_orgs = fields.Datetime(string='Last Orgs Sync',
                                     help='Last time organizations were synced from LinkedIn')
    is_default = fields.Boolean(string="Is Default",
                                compute="_compute_is_default", store=False)
    org_ids = fields.One2many(
        'linkedin.organization',
        'account_id',
        string='Organization Pages',
        help='LinkedIn organization pages linked to this account.',
    )
    oauth_provider_id = fields.Many2one(
        'auth.oauth.provider', string="OAuth Provider",
        default=lambda self: self.env.ref('cyllo_linkedin.provider_linkedin', raise_if_not_found=False),
    )
    client_id = fields.Char(related='oauth_provider_id.client_id', readonly=False,
                            groups='cyllo_social_media_marketing.group_social_media_administrator')
    client_secret = fields.Char(related='oauth_provider_id.client_secret', readonly=False,
                                groups='cyllo_social_media_marketing.group_social_media_administrator')

    def _compute_is_default(self):
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_linkedin_account.default_account_id'
        )
        for rec in self:
            rec.is_default = str(rec.id) == str(default_id)

    @api.model_create_single
    def create(self, vals):
        """Override to handle manual access token connection."""
        if vals.get('linkedin_access_token'):
            vals['state'] = 'connected'

        record = super(LinkedInAccount, self).create(vals)

        if record.sudo().linkedin_access_token:
            try:
                record.action_sync_organizations()
            except Exception as e:
                _logger.error(
                    f"Failed to sync organizations for manual account {record.name}: {e}")

        return record

    @api.model
    def get_linkedin_auth_url(self, account_id=False, username=False, client_id=False, client_secret=False):
        linkedin_auth_provider = self.env.ref(
            'cyllo_linkedin.provider_linkedin'
        ).sudo()
        if client_id or client_secret:
            linkedin_auth_provider.write({
                'client_id': client_id or linkedin_auth_provider.client_id,
                'client_secret': client_secret or linkedin_auth_provider.client_secret,
            })
        if not linkedin_auth_provider.client_id or not linkedin_auth_provider.client_secret:
            raise ValidationError(_(
                'LinkedIn Access Credentials are empty!\n'
                'Please fill them in the Auth Provider form.'
            ))
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        redirect_uri = url_join(base_url, '/linkedin/redirect')
        nonce = secrets.token_urlsafe(32)
        if account_id:
            self.browse(account_id).oauth_nonce = nonce
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'cyllo_linkedin.pending_new_account_nonce', nonce)
        state = nonce
        params = {
            'response_type': 'code',
            'client_id': linkedin_auth_provider.client_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': (
                'openid profile email '
                'w_member_social '
                'r_organization_social '
                'rw_organization_admin '
                'w_organization_social'
            ),
        }
        if username:
            params['login_hint'] = username
        elif account_id:
            account = self.browse(account_id)
            if account.exists() and account.username:
                params['login_hint'] = account.username

        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(
                params),
            'target': 'self',
        }

    def action_connect_linkedin(self):
        """Connect LinkedIn account via OAuth only."""
        self.ensure_one()
        return self.get_linkedin_auth_url(account_id=self.id)

    def action_disconnect(self):
        """ Function to disconnect the LinkedIn account. """
        self.org_ids.write({'state': 'inactive'})
        self.write({
            'state': 'not connected',
            'linkedin_access_token': False,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'social_linkedin_account.default_account_id', None
        )

    def action_sync_organizations(self):
        """Create/update linkedin.organization records. Debounced to 30 mins."""
        self.ensure_one()
        self = self.sudo()
        if not self.linkedin_access_token:
            return []

        if self.last_sync_orgs and (
                datetime.now() - self.last_sync_orgs).total_seconds() < 30:
            _logger.info(
                f"Skipping organization sync for {self.name} (last sync was {self.last_sync_orgs})")
            return self.env['linkedin.organization'].search(
                [('account_id', '=', self.id), ('state', '=', 'active')])

        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        identity_records = []
        try:
            user_res = requests.get('https://api.linkedin.com/v2/userinfo',
                                    headers=headers, timeout=30)
            if user_res.ok:
                ui = user_res.json()
                person_sub = ui.get('sub')
                if person_sub:
                    person_urn = f"urn:li:person:{person_sub}"
                    person_name = ui.get('name', self.name)
                    person_logo = ui.get('picture')

                    existing_person = self.env['linkedin.organization'].search([
                        ('org_urn', '=', person_urn),
                        ('account_id', '=', self.id)
                    ], limit=1)

                    vals = {
                        'name': person_name,
                        'logo_url': person_logo,
                        'type': 'person',
                        'state': 'active',
                    }
                    if existing_person:
                        existing_person.write(vals)
                        identity_records.append(existing_person)
                    else:
                        vals.update(
                            {'org_urn': person_urn, 'account_id': self.id})
                        new_person = self.env['linkedin.organization'].create(
                            vals)
                        identity_records.append(new_person)

            acl_url = 'https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee'
            acl_res = requests.get(acl_url, headers=headers, timeout=30)
            if acl_res.ok:
                acl_elements = acl_res.json().get('elements', [])
                for acl in acl_elements:
                    org_urn = acl.get('organizationalTarget')
                    if not org_urn or 'urn:li:organization:' not in org_urn:
                        continue

                    org_id_num = org_urn.split(':')[-1]
                    org_name = self.name
                    org_logo = False

                    try:
                        org_detail_url = (
                            f'https://api.linkedin.com/v2/organizations/{org_id_num}'
                            f'?projection=(localizedName,logoV2(original~:playableStreams,cropped~:playableStreams))'
                        )
                        org_det_res = requests.get(org_detail_url,
                                                   headers=headers, timeout=30)
                        if org_det_res.ok:
                            org_det = org_det_res.json()
                            org_name = org_det.get('localizedName', org_name)
                            logo_v2 = org_det.get('logoV2')

                            if isinstance(logo_v2, dict):
                                for field in ['original~', 'cropped~']:
                                    expanded = logo_v2.get(field, {})
                                    streams = expanded.get('elements', [])
                                    if streams:
                                        identifiers = streams[0].get(
                                            'identifiers', [])
                                        if identifiers:
                                            org_logo = identifiers[0].get(
                                                'identifier')
                                            break

                                if not org_logo:
                                    logo_urn = logo_v2.get(
                                        'original') or logo_v2.get('cropped')
                                    if logo_urn and isinstance(logo_urn,
                                                               str) and logo_urn.startswith(
                                            'urn:li:digitalmediaAsset:'):
                                        image_id = logo_urn.split(':')[-1]
                                        img_res = requests.get(
                                            f"https://api.linkedin.com/v2/images/{image_id}",
                                            headers=headers, timeout=30)
                                        if img_res.ok:
                                            org_logo = img_res.json().get(
                                                'downloadUrl')

                        existing_org = self.env['linkedin.organization'].search(
                            [
                                ('org_urn', '=', org_urn),
                                ('account_id', '=', self.id)
                            ], limit=1)
                        vals = {
                            'name': org_name,
                            'logo_url': org_logo,
                            'type': 'organization',
                            'state': 'active',
                        }
                        if existing_org:
                            existing_org.write(vals)
                            identity_records.append(existing_org)
                            existing_org.action_fetch_audience()
                        else:
                            vals.update(
                                {'org_urn': org_urn, 'account_id': self.id})
                            new_org = self.env['linkedin.organization'].create(
                                vals)
                            identity_records.append(new_org)
                            new_org.action_fetch_audience()
                    except Exception as e:
                        _logger.error(f"Error syncing org {org_urn}: {e}")
        except Exception as e:
            _logger.error(f'Error in action_sync_organizations: {e}')
        self.write({'last_sync_orgs': datetime.now()})
        return identity_records

    def action_fetch_linkedin_feeds(self, start=0, count=15):
        """Fetch LinkedIn feeds for all managed org pages. Auto-syncs orgs first."""

        self.ensure_one()
        self = self.sudo()
        if not self.linkedin_access_token:
            raise ValidationError(_("Please connect to LinkedIn first."))

        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        legacy_headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}'}
        try:
            user_res = requests.get('https://api.linkedin.com/v2/userinfo',
                                    headers=headers, timeout=30)
            if user_res.ok:
                ui = user_res.json()
                pic = ui.get('picture')
                if pic:
                    self.write({'linkedin_profile_image_url': pic})
        except Exception as e:
            _logger.warning(f'Could not refresh personal picture: {e}')
        identity_records = self.action_sync_organizations()
        all_urns = []
        for ident in identity_records:
            if ident.type == 'person':
                continue
            all_urns.append(
                (ident.org_urn, ident.name, ident.logo_url, ident.id))
        if not all_urns:
            _logger.info(
                f'No linked organizations found for account {self.name}. Skipping feed fetch.')
            return {
                'has_more': False,
                'total_created': 0,
                'notification': {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Info'),
                        'message': _(
                            'No LinkedIn organizations found to sync.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            }
        _logger.info(
            f'Fetching feeds for: {[u[0] for u in all_urns]} (start={start}, count={count})')
        total_created = 0
        has_more = False
        for fetch_urn, fetch_name, fetch_pic, org_id in all_urns:
            try:
                res = self._fetch_feeds_for_urn(fetch_urn, fetch_name,
                                                fetch_pic, legacy_headers,
                                                org_id=org_id, start=start,
                                                count=count)
                total_created += res.get('created_count', 0)
                if res.get('has_more'):
                    has_more = True
            except Exception as e:
                _logger.error(f'Error fetching feeds for {fetch_urn}: {e}')

        return {
            'has_more': has_more,
            'total_created': total_created,
            'notification': {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        f'{total_created} LinkedIn feeds synced across {len(all_urns)} account(s).'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        }

    def _fetch_feeds_for_urn(self, owner_urn, author_name, profile_pic_url,
                             legacy_headers, org_id=False, start=0, count=15):
        """Fetch and store feeds for a single LinkedIn URN using the modern Posts API. Returns count of new records created."""
        rest_headers = dict(legacy_headers)
        rest_headers.update({
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202602',
        })
        params = {
            'q': 'author',
            'author': owner_urn,
            'count': count,
            'start': start,
        }
        url = 'https://api.linkedin.com/rest/posts'
        _logger.info(
            f'Fetching LinkedIn Posts for {owner_urn}: GET {url} (count={count})')
        try:
            response = requests.get(url, params=params, headers=rest_headers,
                                    timeout=30)
            _logger.info(f'LinkedIn Posts API Response: {response.status_code}')
            if not response.ok:
                _logger.error(
                    f'LinkedIn Posts API failed: {response.status_code} - {response.text[:300]}')
                return {'created_count': 0, 'has_more': False}

            data = response.json()
            elements = data.get('elements', [])
            if not elements:
                return {'created_count': 0, 'has_more': False}
            paging = data.get('paging', {})
            links = paging.get('links', [])
            has_more = any(link.get('rel') == 'next' for link in links)
            if not has_more and 'total' in paging and 'start' in paging and 'count' in paging:
                has_more = (paging['start'] + paging['count']) < paging['total']
            created_count = 0
            for element in elements:
                storage_urn = element.get('id')
                if not storage_urn:
                    continue
                activity_urn = storage_urn
                existing_feed = False
                should_refresh_actions = True
                if existing_feed and existing_feed.last_sync_social_actions:
                    now = datetime.now()
                    diff_hours = (
                                             now - existing_feed.last_sync_social_actions).total_seconds() / 30
                    post_age_days = (
                                now - existing_feed.posted_date).days if existing_feed.posted_date else 0

                    if post_age_days < 1:
                        should_refresh_actions = diff_hours >= 1
                    elif post_age_days < 7:
                        should_refresh_actions = diff_hours >= 6
                    else:
                        should_refresh_actions = diff_hours >= 24

                likes_count = existing_feed.likes_count if existing_feed else 0
                comments_count = existing_feed.comments_count if existing_feed else 0

                if should_refresh_actions:
                    try:
                        action_res = requests.get(
                            f'https://api.linkedin.com/v2/socialActions/{activity_urn}',
                            headers=legacy_headers,
                            timeout=20
                        )
                        if action_res.ok:
                            ad = action_res.json()
                            likes_count = ad.get('likesSummary', {}).get(
                                'totalLikes', 0)
                            comments_count = ad.get('commentsSummary', {}).get(
                                'aggregatedTotalComments',
                                ad.get('commentsSummary', {}).get(
                                    'totalComments', 0)
                            )
                    except Exception as e:
                        _logger.debug('Could not refresh likes/comments for %s: %s', activity_urn, e)

                text_content = element.get('commentary', '')
                image_url = False
                carousel_images = []
                video_url = False
                video_thumbnail_url = False
                is_poll = False
                poll_question = False
                poll_options_json = False
                poll_duration = False
                poll_total_votes = 0
                content = element.get('content', {})
                if content:
                    def resolve_image_urn(urn):
                        if not urn or 'urn:li:image:' not in urn:
                            return None
                        try:
                            encoded = urllib.parse.quote(urn, safe='')
                            r = requests.get(
                                f'https://api.linkedin.com/rest/images/{encoded}',
                                headers=rest_headers,
                                timeout=15
                            )
                            if r.ok:
                                d = r.json()
                                return d.get('downloadUrl') or d.get('thumbnail')
                        except Exception as e:
                            _logger.debug(f'Could not resolve image URN {urn}: {e}')
                        return None
                    media = content.get('media', {})
                    if media:
                        direct = (media.get('downloadUrl')
                                  or media.get('thumbnail')
                                  or media.get('thumbnailUrl'))
                        if direct:
                            image_url = direct
                        else:
                            image_url = resolve_image_urn(media.get('id', ''))
                    multi_image = content.get('multiImage', {})
                    if multi_image:
                        raw_images = multi_image.get('images', [])
                        for img in raw_images:
                            url = (img.get('downloadUrl')
                                   or img.get('thumbnailUrl')
                                   or resolve_image_urn(img.get('id', '')))
                            if url:
                                carousel_images.append(url)
                        if carousel_images and not image_url:
                            image_url = carousel_images[0]
                    video_data = content.get('video', {})
                    if video_data:
                        video_urn = video_data.get('id', '')
                        if video_urn and 'urn:li:video:' in video_urn:
                            try:
                                encoded = urllib.parse.quote(video_urn, safe='')
                                v_res = requests.get(
                                    f'https://api.linkedin.com/rest/videos/{encoded}',
                                    headers=rest_headers,
                                    timeout=20
                                )
                                if v_res.ok:
                                    v_data = v_res.json()
                                    streams = v_data.get('progressiveStreams', [])
                                    if streams:
                                        best = max(
                                            streams,
                                            key=lambda s: s.get('bitRate', 0),
                                            default=streams[0]
                                        )
                                        video_url = best.get('streamingLocations', [{}])[0].get('url')
                                    thumbnails = v_data.get('thumbnails', [])
                                    if thumbnails:
                                        video_thumbnail_url = thumbnails[0].get('url')
                                    if video_thumbnail_url and not image_url:
                                        image_url = video_thumbnail_url
                            except Exception as ve:
                                _logger.debug(f'Could not resolve video URN {video_urn}: {ve}')
                    if not image_url:
                        article = content.get('article', {})
                        if article:
                            thumb = article.get('thumbnail', {})
                            image_url = (
                                thumb.get('downloadUrl')
                                or thumb.get('thumbnailUrl')
                                or article.get('thumbnailUrl')
                            )
                    poll_data = content.get('poll', {})
                    if poll_data:
                        is_poll = True
                        poll_question = poll_data.get('question', '')
                        options = poll_data.get('options', [])
                        import json as _json
                        poll_options_json = _json.dumps([
                            {'text': o.get('text', ''),
                             'voteCount': o.get('voteCount', 0)}
                            for o in options
                        ])
                        poll_duration = poll_data.get('settings', {}).get(
                            'duration', '')
                        poll_total_votes = poll_data.get('uniqueVotersCount', 0)

                first_pub = element.get('publishedAt') or element.get(
                    'createdAt')
                created_time = first_pub / 1000 if first_pub else 0
                posted_datetime = datetime.fromtimestamp(
                    created_time) if created_time else fields.Datetime.now()

                import json as _json_vals
                vals = {
                    'description': text_content or 'No description',
                    'posted_date': posted_datetime,
                    'author_name': author_name,
                    'linkedin_account_id': self.id,
                    'linkedin_org_id': org_id,
                    'posted_on_linkedin': True,
                    'linkedin_post_urn': storage_urn,
                    'posted_image_url': image_url,
                    'profile_image_url': profile_pic_url,
                    'author_link_url': f'https://www.linkedin.com/feed/update/{storage_urn}',
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'last_sync_social_actions': datetime.now() if should_refresh_actions else (
                        existing_feed.last_sync_social_actions if existing_feed else False),
                    'is_poll': is_poll,
                    'poll_question': poll_question,
                    'poll_options': poll_options_json,
                    'poll_duration': poll_duration,
                    'poll_total_votes': poll_total_votes,
                    'carousel_images_json': _json_vals.dumps(carousel_images) if carousel_images else False,
                    'video_url': video_url,
                    'video_thumbnail_url': video_thumbnail_url,
                }

                created_count += 1

            return {'created_count': created_count, 'has_more': has_more}

        except Exception as e:
            _logger.exception(
                f"Exception in _fetch_feeds_for_urn for {owner_urn}: {e}")
            return {'created_count': 0, 'has_more': False}

    def action_fetch_feed_comments(self, parent_urn):
        """Fetch all comments for a specific LinkedIn post or comment using V2 API."""

        self.ensure_one()
        self = self.sudo()
        parent_urn = parent_urn.strip() if parent_urn else ""
        _logger.info(
            f"START LinkedIn comment fetch (V2). Parent URN: '{parent_urn}'")
        if not self.linkedin_access_token:
            _logger.warning("LinkedIn access token missing.")
            return []
        parent_urn_encoded = urllib.parse.quote(parent_urn)
        v2_url = f"https://api.linkedin.com/v2/socialActions/{parent_urn_encoded}/comments?projection=(elements*(id,message,created,actor~,commentsSummary(aggregatedTotalComments,totalComments)))"
        try:
            _logger.info(f"V2 Request: GET {v2_url}")
            v2_res = requests.get(v2_url, headers={
                'Authorization': f'Bearer {self.linkedin_access_token}'},
                                  timeout=30)
            _logger.info(f"V2 Response: {v2_res.status_code}")
            if v2_res.ok:
                v2_data = v2_res.json()
                v2_comments = []
                for element in v2_data.get('elements', []):
                    actor_data = element.get('actor~', {})
                    author_name = actor_data.get('localizedFirstName', '')
                    if actor_data.get('localizedLastName'):
                        author_name += ' ' + actor_data['localizedLastName']
                    if not author_name:
                        author_name = actor_data.get('localizedName',
                                                     'LinkedIn User')
                    created_at_ms = element.get('created', {}).get('time', 0)
                    created_datetime = datetime.fromtimestamp(
                        created_at_ms / 1000.0).strftime(
                        '%Y-%m-%d %H:%M:%S') if created_at_ms else ""
                    comment_id = element.get('id')
                    _logger.debug(f"V2 Raw Comment ID: {comment_id}")
                    parent_match = re.search(
                        r'urn:li:comment:\((urn:li:activity:\d+),', parent_urn)
                    if comment_id and str(comment_id).startswith(
                            'urn:li:comment:'):
                        full_urn = comment_id
                    elif parent_match and comment_id:
                        activity_urn = parent_match.group(1)
                        full_urn = f"urn:li:comment:({activity_urn},{comment_id})"
                    elif comment_id and 'activity' in parent_urn:
                        full_urn = f"urn:li:comment:({parent_urn},{comment_id})"
                    else:
                        full_urn = comment_id
                    comments_summary = element.get('commentsSummary', {})
                    reply_count = comments_summary.get(
                        'aggregatedTotalComments',
                        comments_summary.get('totalComments', 0))
                    v2_comments.append({
                        'id': full_urn,
                        'text': element.get('message', {}).get('text', ''),
                        'author_name': author_name,
                        'created_at': created_datetime,
                        'comments_count': reply_count,
                        'likes_count': 0,
                    })
                v2_comments.sort(key=lambda x: x['created_at'], reverse=True)

                if 'activity' in parent_urn:
                    self._sync_linkedin_comment_count(parent_urn,
                                                      len(v2_comments))
                return v2_comments
            else:
                _logger.error(
                    f"V2 Fetch Failed: {v2_res.status_code} - {v2_res.text[:200]}")
                return []

        except Exception as e:
            _logger.error(
                f"Critical error in LinkedIn comment fetch (V2): {str(e)}",
                exc_info=True)
            return []

    def action_post_linkedin_comment(self, post_urn, message):
        """Post a top-level comment to a LinkedIn post via V2 API."""
        self.ensure_one()
        self = self.sudo()
        import urllib.parse
        if not self.linkedin_access_token or not self.org_ids:
            return {
                'error': 'LinkedIn account not connected or no identities found.'}
        post_urn_encoded = urllib.parse.quote(post_urn)
        v2_url = f"https://api.linkedin.com/v2/socialActions/{post_urn_encoded}/comments"
        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        actor = False
        active_orgs = self.org_ids.filtered(lambda i: i.state == 'active')
        if active_orgs:
            actor = active_orgs[0].org_urn
        elif self.org_ids:
            actor = self.org_ids[0].org_urn
        if not actor:
            return {'error': 'Could not resolve author URN for posting.'}
        body = {
            "actor": actor,
            "message": {
                "text": message
            }
        }
        try:
            _logger.info(f"V2 POST Request: {v2_url} | Body: {body}")
            res = requests.post(v2_url, json=body, headers=headers, timeout=30)
            _logger.info(
                f"V2 POST Response: {res.status_code} - {res.text[:200]}")
            if res.status_code in (200, 201):
                return res.json()
            else:
                return {'error': res.text}
        except Exception as e:
            _logger.error(f"LinkedIn V2 Post Exception: {str(e)}",
                          exc_info=True)
            return {'error': str(e)}

    def _sync_linkedin_comment_count(self, post_urn, count):
        """Helper to keep the feed record count in sync with live comments popup."""
        feed = False
        if feed:
            _logger.debug(f"Syncing comment count for feed {feed.id}: {count}")
            feed.write({'comments_count': count})

    def action_delete_linkedin_post(self, post_urn):
        """Delete a LinkedIn post via v2/ugcPosts endpoint."""
        self.ensure_one()
        self = self.sudo()
        if not self.linkedin_access_token:
            return {'error': 'LinkedIn account not connected.'}
        _logger.info(f"Deleting LinkedIn Post. URN: {post_urn}")
        headers = {
            'Authorization': f'Bearer {self.linkedin_access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }
        post_id = post_urn.split(':')[-1]
        success = False
        last_error = "Deletion failed."

        for prefix in ['urn:li:ugcPost:', 'urn:li:share:']:
            target_urn = urllib.parse.quote(prefix + post_id)
            url = f"https://api.linkedin.com/v2/ugcPosts/{target_urn}"

            try:
                res = requests.delete(url, headers=headers, timeout=30)
                if res.status_code in (200, 204):
                    _logger.info(f"SUCCESS: Deleted {prefix}{post_id}")
                    success = True
                elif res.status_code != 404:
                    last_error = f"Failed ({res.status_code}): {res.text[:200]}"
            except Exception as e:
                _logger.warning(f"Delete exception for {url}: {e}")
                last_error = str(e)
        if success:
            return True
        return {'error': last_error}

