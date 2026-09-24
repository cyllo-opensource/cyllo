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
from odoo import fields, models, api

TRACKED_PLATFORMS = {
    'social.fb.account': 'facebook_page_name',
    'social.insta.account': 'facebook_insta_page_name',
}


class SocialMediaSnapshot(models.Model):
    """ One row per connected account per day, capturing the audience size
    at that point in time. Needed because account models only ever hold the
    latest follower count, not a history, so trend charts have no data to
    plot without this. """
    _name = "social.media.snapshot"
    _description = "Social Media Snapshot"
    _order = "snapshot_date desc"

    platform = fields.Selection([
        ('social.fb.account', 'Facebook'),
        ('social.insta.account', 'Instagram'),
        ('youtube.channel', 'YouTube'),
        ('linkedin.organization', 'LinkedIn'),
    ], required=True)
    account_res_id = fields.Integer(string="Account", required=True,
                                    help="Id of the record in the model named by 'platform'.")
    account_name = fields.Char(required=True)
    snapshot_date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    followers_count = fields.Integer(default=0)

    _sql_constraints = [
        ('snapshot_unique', 'unique(platform, account_res_id, snapshot_date)',
         'Only one snapshot per account per day is allowed.'),
    ]

    @api.model
    def action_capture_audience_snapshots(self):
        """ Public entry point so the dashboard's manual refresh button can call
        the same logic the cron uses (private methods are blocked from RPC). """
        return self._cron_capture_audience_snapshots()

    @api.model
    def _cron_capture_audience_snapshots(self):
        """ Refresh each connected account's follower count and log today's snapshot.
        Called daily by ir.cron; safe to run more than once a day (upserts on the
        platform/account/date unique key). """
        today = fields.Date.context_today(self)
        for platform, name_field in TRACKED_PLATFORMS.items():
            if platform not in self.env:
                continue
            accounts = self.env[platform].search([('state', '=', 'connected')])
            for account in accounts:
                account.action_fetch_audience()
                self._upsert_snapshot(platform, account.id, account[name_field], today, account.followers_count)

        self._capture_platform_snapshots(today)

    def _upsert_snapshot(self, platform, account_res_id, account_name, today, followers_count):
        """ Shared write-or-create used by every platform's snapshot capture -
        upserts on the platform/account/date unique key. """
        existing = self.search([
            ('platform', '=', platform),
            ('account_res_id', '=', account_res_id),
            ('snapshot_date', '=', today),
        ], limit=1)
        vals = {
            'platform': platform,
            'account_res_id': account_res_id,
            'account_name': account_name,
            'snapshot_date': today,
            'followers_count': followers_count,
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)

    def _capture_platform_snapshots(self, today):
        """ Stub - platforms whose audience data isn't covered by
        TRACKED_PLATFORMS (no stored followers_count/action_fetch_audience on
        the account model itself, e.g. YouTube's live-fetched subscriber
        count) override this, calling super() first. """
        return
