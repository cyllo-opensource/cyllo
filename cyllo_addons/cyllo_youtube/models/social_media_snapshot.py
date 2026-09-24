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


class SocialMediaSnapshot(models.Model):
    _inherit = 'social.media.snapshot'

    def _capture_platform_snapshots(self, today):
        """ YouTube's subscriber count isn't a stored field on youtube.channel
        (no action_fetch_audience to call), so it doesn't fit the base
        module's TRACKED_PLATFORMS dict - fetched live instead. """
        super()._capture_platform_snapshots(today)
        channels = self.env['youtube.channel'].search([('youtube_account_id.state', '=', 'sync')])
        for channel in channels:
            followers_count = self.env['social.media.post'].get_youtube_channel_subscribers(channel.id)
            self._upsert_snapshot('youtube.channel', channel.id, channel.name, today, followers_count)
