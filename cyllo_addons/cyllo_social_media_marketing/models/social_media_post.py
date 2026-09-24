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
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

PLATFORM_REGISTRY = {
    'social.fb.account': {'module': 'cyllo_facebook', 'connect_method': 'action_connect'},
    'social.insta.account': {'module': 'cyllo_instagram', 'connect_method': 'action_connect_instagram'},
}

AUTO_PUBLISH_MAX_RETRIES = 5


class SocialMediaPost(models.Model):
    """Class to define the fields and functions for social media posts."""
    _name = "social.media.post"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Post"

    name = fields.Char(string="Reference", required=True, help="Reference for the social media post.")
    active = fields.Boolean(string='Archive', default=True, help="Check this to activate the social media post.")
    description = fields.Text(string="Content", required=True, help="Content of the social media post.")
    company_id = fields.Many2one(string="Related Company", comodel_name='res.company',
                                 default=lambda self: self.env.company.id, required=True, index=True,
                                 help="The company associated with the social media post.")
    posted_date = fields.Datetime(string="Date of Posting", copy=False,
                                  help="While draft/queued: the date and time to auto-publish this post. "
                                       "Once posted: the date and time it was actually published.")
    user_id = fields.Many2one('res.users', string="Created User", required=True,
                              default=lambda self: self.env.user, index=True, ondelete='cascade',
                              help="User who created the social media post.")
    ir_attachment_ids = fields.Many2many('ir.attachment', string="Add Media",
                                         help="Media files attached to the post.")
    state = fields.Selection([('draft', 'Draft'), ('queue', 'On-Queue'), ('post', 'Posted'),
                              ('delete', 'Deleted')], default='draft', copy=False,
                             help="State of the social media post.")
    mode = fields.Selection([('photo', 'Photo'), ('video', 'Video'), ('url', 'URL'),
                             ('content_only', 'Content Only'), ('poll', 'Poll')],
                            default='photo', copy=False, help="Mode of the social media post.")
    has_selected_platform = fields.Boolean(default=False, copy=False,
                                           help="Whether at least one account is chosen.")
    post_url = fields.Char(string="URL of Post", help="URL attachment of the post.")
    campaign_id = fields.Many2one('utm.campaign', string="Campaign",
                                  help="Marketing campaign this post belongs to.")
    posted_on_linkedin = fields.Boolean(string="Post in LinkedIn",
                                        help="Enable this to post this post in LinkedIn")
    posted_image_url = fields.Char(string="Posted Image Url", readonly=True,
                                   help="The media URL returned by the platform after publishing.")
    auto_publish_retry_count = fields.Integer(default=0, copy=False, readonly=True,
                                              help="How many times the auto-publish cron has retried this "
                                                   "post after a failure. Reset to 0 on (re)schedule. After "
                                                   "AUTO_PUBLISH_MAX_RETRIES failures the cron stops retrying "
                                                   "and pulls the post back to draft instead of retrying "
                                                   "forever every 15 minutes.")

    @api.onchange('mode')
    def _onchange_mode(self):
        """Function to select account on the basis of mode"""
        self.ir_attachment_ids = [(5, 0, 0)]
        if self.mode == 'content_only' and hasattr(self, 'post_on_instagram'):
            self.post_on_instagram = False

    def _has_selected_platform(self):
        """True if at least one post_on_<platform>/posted_on_<platform> flag is set."""
        return any([
            getattr(self, 'post_on_facebook', False),
            getattr(self, 'post_on_instagram', False),
            getattr(self, 'posted_on_linkedin', False),
            getattr(self, 'post_on_youtube', False),
        ])


    def action_post(self):
        """Common function for posting to social media. You can override this function in your modules.
        Runs LAST in the platform override chain (each platform's own
        action_post calls super() at the end) - safe to gate here since none
        of them do any real API work when their own post_on_<platform> is
        False, so blocking at this point has zero partial-post side effects."""
        if not self._has_selected_platform():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Select at least one platform to post to."),
                    'type': 'warning',
                },
            }
        self.write({
            'posted_date': fields.Datetime.now(),
            'state': 'post',
        })

    def action_open_schedule_wizard(self):
        """Open the "pick a date" modal instead of scheduling inline - the
        form no longer shows an editable date field pre-schedule, the modal
        is the only way to set one."""
        self.ensure_one()
        context = {'default_post_id': self.id}
        if self.posted_date:
            context['default_scheduled_date'] = self.posted_date
        return {
            'type': 'ir.actions.act_window',
            'name': _("Schedule Post"),
            'res_model': 'social.media.post.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_schedule(self):
        """Queue the post to be auto-published later by _cron_publish_scheduled_posts."""
        if not self._has_selected_platform():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Select at least one platform to post to."),
                    'type': 'warning',
                },
            }
        if not self.posted_date:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Pick a date and time to schedule this post."),
                    'type': 'warning',
                },
            }
        if self.posted_date <= fields.Datetime.now():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Scheduled date/time must be in the future."),
                    'type': 'warning',
                },
            }
        self.write({'state': 'queue', 'auto_publish_retry_count': 0})
        self._reset_platform_retry_state()
        cron = self.env.ref(
            'cyllo_social_media_marketing.ir_cron_publish_scheduled_posts', raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger(at=self.posted_date)

    def action_cancel_schedule(self):
        """Pull a queued post back to draft so its content/schedule can be edited again."""
        self.write({'state': 'draft'})
        self._reset_platform_retry_state()

    def _reset_platform_retry_state(self):
        """Stub - platforms that track which of their accounts already got a
        successful post this attempt (to make a retry skip them, avoiding a
        duplicate post) override this to clear that tracking whenever the
        post is (re)scheduled or pulled back to draft - a fresh scheduling
        attempt should retry every account, not just the ones that failed
        last time. Overrides must call super() first."""
        return

    @api.model
    def _cron_publish_scheduled_posts(self):
        """Publish every queued post whose posted_date (used here as the scheduled
        date/time) has arrived. One post's failure (platform API error, missing
        token, ...) must not block the rest, so each is posted and logged
        independently. action_post() overwrites posted_date with the actual
        publish time once it succeeds.

        A post that fails stays in 'queue' (whether action_post raised, or
        returned a failure notification without reaching state='post') so
        it's retried on the next run - but only up to AUTO_PUBLISH_MAX_RETRIES
        times, after which it's pulled back to draft instead of retrying
        forever every 15 minutes with no end in sight."""
        due_posts = self.search([
            ('state', '=', 'queue'),
            ('posted_date', '!=', False),
            ('posted_date', '<=', fields.Datetime.now()),
        ])
        for post in due_posts:
            try:
                post.action_post()
            except Exception:
                _logger.exception("Failed to auto-publish scheduled social media post %s", post.id)
            if post.state == 'post':
                continue
            post.auto_publish_retry_count += 1
            if post.auto_publish_retry_count >= AUTO_PUBLISH_MAX_RETRIES:
                post.message_post(body=_(
                    "Auto-publish gave up after %d failed attempts - pulled back to Draft. "
                    "Fix the issue (check the platform connection/token) and reschedule."
                ) % post.auto_publish_retry_count)
                post.write({'state': 'draft', 'auto_publish_retry_count': 0})
            else:
                _logger.warning(
                    "Auto-publish attempt %d/%d failed for social media post %s, will retry.",
                    post.auto_publish_retry_count, AUTO_PUBLISH_MAX_RETRIES, post.id)

    def action_social_media_comments(self):
        """Placeholder function for handling social media comments. Overridden per platform."""
        return

    def action_compute_likes_count_all(self):
        """Refresh like/comment counts from the live platform. Overridden per platform."""
        return True

    def action_compute_likes_count(self):
        """Refresh and return like/comment counts for one post. Overridden per platform."""
        return {'likes_count': 0, 'comments_count': 0}

    def _get_audience_batch_stats(self, platform, account_ids):
        """ Single batched query covering every account's audience baseline
        AND history at once (was 2 DB round-trips per account, i.e. 2N
        searches for N accounts, via two now-removed per-account helpers).
        Every platform dashboard tile builder needs both pieces for the SAME
        set of accounts at the same time, and (platform, account_res_id,
        snapshot_date) is unique per social.media.snapshot row, so a single
        search ordered oldest-first gives us everything needed for both: the
        first row seen for an account is its baseline (earliest snapshot),
        and whichever rows fall within the last 30 days are its history -
        computed here in Python from that one already-fetched recordset
        instead of 2 more searches per account.

        Returns {account_id: {'baseline': int_or_None, 'history': [...]}} -
        'baseline' is None (not the platform's current follower count) when
        an account has no snapshot at all yet; callers should fall back to
        their own current-count value in that case. 'history' defaults to []
        when an account has no snapshot in the last 30 days. """
        if not account_ids:
            return {}
        since = fields.Date.context_today(self) - timedelta(days=30)
        snapshots = self.env['social.media.snapshot'].search([
            ('platform', '=', platform),
            ('account_res_id', 'in', account_ids),
        ], order='snapshot_date asc')
        stats = {account_id: {'baseline': None, 'history': []} for account_id in account_ids}
        for snapshot in snapshots:
            entry = stats.get(snapshot.account_res_id)
            if entry is None:
                continue
            if entry['baseline'] is None:
                entry['baseline'] = snapshot.followers_count
            if snapshot.snapshot_date >= since:
                entry['history'].append({
                    'date': snapshot.snapshot_date.strftime('%b %d'),
                    'followers_count': snapshot.followers_count,
                })
        return stats

    def get_dashboard_data(self):
        dashboard_data = self._get_platform_dashboard_tiles()
        recent_posts = self.search([('state', '=', 'post')], order='posted_date desc, id desc', limit=50)
        return {
            'dashboard_data': dashboard_data,
            'posts': [self._serialize_recent_post(post) for post in recent_posts],
            'campaigns': self._get_campaign_summary(),
        }

    def _get_campaign_summary(self):
        """Top campaigns by post count, for the Dashboard's own summary section -
        full detail lives in the dedicated Campaigns view."""
        campaigns = self.env['utm.campaign'].search([('social_post_ids', '!=', False)])
        data = [{
            'id': c.id,
            'name': c.name,
            'total_posts': c.social_post_count,
            'total_engagements': c.social_total_engagements,
            'leads_created': c.social_leads_created,
            'leads_converted': c.social_leads_converted,
        } for c in campaigns]
        data.sort(key=lambda d: d['total_posts'], reverse=True)
        return data[:8]

    def _get_platform_dashboard_tiles(self):
        """ Stub - each installed platform module's own social.media.post
        override appends its own connected accounts' dashboard tile(s) here,
        calling super() first. No platform-specific code belongs in this
        base module; a platform simply contributes nothing if its module
        isn't installed. """
        return []

    def _get_display_image_url(self, post):
        """ posted_image_url is frozen at publish time as a FULLY-QUALIFIED
        external URL (needed then, so the platform's own servers could fetch
        it) - if web.base.url changes afterward (a dev tunnel rotating, a
        domain migration), that stored URL points nowhere forever. The
        post's own attachment never moves, so prefer a plain relative path
        to it for our OWN in-app display (Dashboard, Calendar) - only for an
        actual IMAGE attachment (a video attachment can't render via
        /web/image, and a platform like YouTube already writes back its own
        permanent, platform-hosted thumbnail into posted_image_url anyway). """
        attachment = post.ir_attachment_ids.filtered(lambda a: (a.mimetype or '').startswith('image/'))[:1]
        return f'/web/image/{attachment.id}' if attachment else post.posted_image_url

    def _serialize_recent_post(self, post):
        """Build the dict the dashboard's Recent Posts cards render - picks the
        connected account's own name/dp for whichever platform this post went to,
        since posts can target multiple accounts per platform (no single
        "the" account to read a name/picture off of directly)."""
        account_name, account_image = self._get_recent_post_account_info(post)
        return {
            'id': post.id,
            'description': post.description,
            'posted_date': post.posted_date,
            'mode': post.mode,
            'posted_image_url': self._get_display_image_url(post),
            'posted_on_facebook': getattr(post, 'posted_on_facebook', False),
            'posted_on_ig': getattr(post, 'posted_on_ig', False),
            'posted_on_youtube': getattr(post, 'posted_on_youtube', False),
            'posted_on_linkedin': post.posted_on_linkedin,
            'account_name': account_name,
            'account_image': account_image,
            'user_name': post.user_id.name,
            'likes_count': (getattr(post, 'fb_likes_count', 0) + getattr(post, 'ig_likes_count', 0)
                            + getattr(post, 'youtube_likes_count', 0) + getattr(post, 'linkedin_likes_count', 0)),
            'comments_count': (getattr(post, 'fb_comments_count', 0) + getattr(post, 'ig_comments_count', 0)
                               + getattr(post, 'youtube_comments_count', 0)
                               + getattr(post, 'linkedin_comments_count', 0)),
            'views_count': getattr(post, 'youtube_views_count', 0),
        }

    def _get_recent_post_account_info(self, post):
        """ Stub - each installed platform module overrides this, checking
        its own posted_on_<platform> flag and falling back to super() when
        it doesn't match. Returns (account_name, account_image). """
        return False, False

    def _get_platform_permalink(self, platform_key):
        """ Stub - each platform's own social.media.post override returns the
        real URL of this post on the platform it was published to (or False)
        when platform_key matches its own account model string (the same key
        streamPlatforms/get_connected_accounts use, e.g. 'social.fb.account')
        - a post can go to several platforms at once, so the caller must say
        which one it means instead of leaving it to whichever override
        happens to run first. Falls back to super() when the key doesn't
        match. """
        return False

    def action_open_on_platform(self, platform_key):
        """ Open the real, live post on the given platform (identified the
        same way streamPlatforms/get_connected_accounts key their entries),
        in a new tab. """
        self.ensure_one()
        url = self._get_platform_permalink(platform_key)
        if not url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'message': _("Couldn't find a link for this post."), 'type': 'warning'},
            }
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def _get_calendar_platform_icon(self, post):
        """ Stub - each installed platform module overrides this, checking
        its own posted_on_<platform> flag and falling back to super() when
        it doesn't match. Feeds the Content Calendar's own event card
        (see social_media_post_calendar.js/.xml). """
        return 'ri-global-line'

    calendar_account_name = fields.Char(compute='_compute_calendar_display')
    calendar_account_image = fields.Char(compute='_compute_calendar_display')
    calendar_platform_icon = fields.Char(compute='_compute_calendar_display')
    calendar_image_url = fields.Char(compute='_compute_calendar_display')

    def _compute_calendar_display(self):
        for post in self:
            account_name, account_image = self._get_recent_post_account_info(post)
            post.calendar_account_name = account_name or post.user_id.name
            post.calendar_account_image = account_image or False
            post.calendar_platform_icon = self._get_calendar_platform_icon(post)
            post.calendar_image_url = self._get_display_image_url(post)

    def action_create_connect(self, data, platform):
        if platform not in self.env:
            _logger.warning("action_create_connect: platform '%s' has no matching model installed", platform)
            return False
        account = self.env[platform].sudo().create(data)
        entry = PLATFORM_REGISTRY.get(platform)
        if entry:
            getattr(account, entry['connect_method'])()
            if entry.get('returns_id'):
                return account.id
        return False

    @api.model
    def get_connected_accounts(self):
        """ Every connected account across every installed platform module -
        feeds the post composer's own "Choose Accounts" tile picker (each
        entry's id must be a real id in whatever model post_platform_account_fields
        says post_on_<platform> data actually links to). Stub - each installed
        platform module's own override appends its own connected accounts
        here, calling super() first. """
        return []

    @api.model
    def get_streamable_accounts(self):
        """ Accounts offered by the Streams board's own Add-a-Stream flyout -
        identical to get_connected_accounts() for every platform EXCEPT
        where one OAuth connection can independently stream several distinct
        pages (LinkedIn: one linkedin.account can own several
        linkedin.organization pages, each streamable on its own), which
        overrides this to list those pages instead of the connection
        itself. Default: same list as the post composer sees. """
        return self.get_connected_accounts()

    def get_model(self, model=None):
        if not model or model == 'any':
            modules = self.env['ir.module.module'].sudo().search([
                ('name', 'in', [entry['module'] for entry in PLATFORM_REGISTRY.values()]),
                ('state', '=', 'installed')
            ])
            return bool(modules)
        entry = PLATFORM_REGISTRY.get(model)
        name = entry['module'] if entry else model
        module = self.env['ir.module.module'].sudo().search([('name', '=', name), ('state', '=', 'installed')])
        return bool(module)

    @api.model
    def share_post_to_discuss(self, **kwargs):
        """Share a Streams post with another Odoo user via Discuss - opens
        (or reuses) a direct-message channel with them and posts the post's
        text + permalink. Generic across all 4 platforms since it's purely
        internal to Odoo, no platform API involved."""
        try:
            user_id = kwargs.get('user_id')
            text = kwargs.get('text') or ''
            permalink = kwargs.get('permalink') or ''
            partner = self.env['res.users'].browse(int(user_id)).partner_id
            channel_info = self.env['discuss.channel'].channel_get([partner.id])
            channel = self.env['discuss.channel'].browse(channel_info['id'])
            body = Markup("<p>%s</p>") % text if text else Markup("")
            if permalink:
                body += Markup('<p><a href="%s" target="_blank">%s</a></p>') % (permalink, permalink)
            channel.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_comment')
            return {'success': True}
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Could not send the message. Please try again."),
                    'type': 'warning',
                },
            }
