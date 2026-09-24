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
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError

STREAM_TYPES_BY_PLATFORM = {
    'social.fb.account': ['posts', 'comments', 'mentions', 'unpublished'],
    'social.insta.account': ['posts', 'comments', 'hashtag_recent', 'hashtag_trending'],
    'youtube.channel': ['videos', 'comments', 'moderate', 'likely_spam', 'search', 'playlist'],
    'linkedin.organization': ['posts', 'comments'],
}
ALL_STREAM_TYPES = sorted({stream_type for types in STREAM_TYPES_BY_PLATFORM.values() for stream_type in types})

CONNECTED_STATE_FIELD = {
    'social.fb.account': ('state', {'connected'}),
    'social.insta.account': ('state', {'connected'}),
    'linkedin.organization': ('state', {'active'}),
    'youtube.channel': ('is_active', {True}),
}


class SocialStreamColumn(models.Model):
    """ One column of a Streams board: one connected account, watched via one
    stream type (posts, comments, hashtag search, moderation queue, ...).
    Purely a saved live-fetch configuration - fetch_stream_data() always reads
    straight from the platform API and never stores platform content here or
    on social.media.post. """
    _name = "social.stream.column"
    _description = "Social Stream Column"
    _order = "sequence, id"

    board_id = fields.Many2one('social.stream.board', string="Board", required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    platform = fields.Selection([
        ('social.fb.account', 'Facebook'),
        ('social.insta.account', 'Instagram'),
        ('youtube.channel', 'YouTube'),
        ('linkedin.organization', 'LinkedIn'),
    ], required=True)
    account_res_id = fields.Integer(string="Account", required=True,
                                    help="Id of the record in the model named by 'platform'.")
    account_display_name = fields.Char(string="Account Name")
    account_avatar_url = fields.Char(string="Account Avatar")
    stream_type = fields.Selection([(stream_type, stream_type) for stream_type in ALL_STREAM_TYPES], required=True)
    config = fields.Text(default='{}', help="JSON blob for stream-specific parameters "
                                            "(hashtag, search query, playlist id, sort order, ...).")

    @api.constrains('platform', 'stream_type')
    def _check_stream_type_valid_for_platform(self):
        for column in self:
            if column.stream_type not in STREAM_TYPES_BY_PLATFORM.get(column.platform, []):
                raise UserError(_("The stream type \"%s\" isn't available for this platform.") % column.stream_type)

    def get_config(self):
        self.ensure_one()
        try:
            return json.loads(self.config or '{}')
        except ValueError:
            return {}

    def _account_is_connected(self):
        """ True unless we have a concrete reason to believe the account
        backing this column is disconnected. A platform with no
        CONNECTED_STATE_FIELD entry defaults to visible (we simply don't
        know how to check it), but a platform whose model isn't in self.env
        at all means the module that used to provide it was uninstalled -
        that column can never work again, so it must hide. """
        self.ensure_one()
        if self.platform not in self.env:
            return False
        field_name, connected_values = CONNECTED_STATE_FIELD.get(self.platform, (None, None))
        if not field_name:
            return True
        account = self.env[self.platform].browse(self.account_res_id).exists()
        if not account:
            return False
        return account[field_name] in connected_values

    def _to_dict(self):
        self.ensure_one()
        return {
            'id': self.id,
            'sequence': self.sequence,
            'platform': self.platform,
            'account_res_id': self.account_res_id,
            'account_display_name': self.account_display_name,
            'account_avatar_url': self.account_avatar_url,
            'stream_type': self.stream_type,
            'config': self.get_config(),
        }

    @api.model
    def create_column(self, board_id, platform, account_res_id, stream_type,
                      account_display_name=False, account_avatar_url=False, config=None):
        board = self.env['social.stream.board'].browse(int(board_id))
        max_sequence = max(board.column_ids.mapped('sequence') or [0])
        column = self.create({
            'board_id': board.id,
            'platform': platform,
            'account_res_id': int(account_res_id),
            'account_display_name': account_display_name,
            'account_avatar_url': account_avatar_url,
            'stream_type': stream_type,
            'sequence': max_sequence + 10,
            'config': json.dumps(config or {}),
        })
        return column._to_dict()

    @api.model
    def action_reorder_columns(self, ordered_ids):
        for index, column_id in enumerate(ordered_ids):
            self.browse(column_id).write({'sequence': (index + 1) * 10})
        return True

    def fetch_stream_data(self, cursor=None):
        """ Single dispatch entry point the frontend calls for every column,
        regardless of platform/stream type - routes to the matching
        _fetch_<stream_type>() override contributed by the platform module. """
        self.ensure_one()
        self._refresh_account_avatar()
        handler = getattr(self, '_fetch_%s' % self.stream_type, None)
        if not handler:
            raise UserError(_("This stream type isn't available - is the matching platform module installed?"))
        return handler(cursor=cursor)

    def _refresh_account_avatar(self):
        """ account_avatar_url is a snapshot taken once, when the column was
        created - fine for platforms serving a stable/local image URL, but
        Facebook/Instagram's Graph API avatar URLs are temporary CDN links
        that expire after a while, so without this a column's header photo
        eventually breaks and never recovers on its own. Stub - each
        platform module overrides to resync from its own account model's
        current avatar field (itself kept fresh by the daily audience-
        snapshot cron, so this needs no extra API call of its own). """
        return

    def _normalize_envelope(self, items, cursor=None, meta=None):
        return {'items': items, 'cursor': cursor or None, 'meta': meta or {}}

    def _existing_lead_id(self, unique_field_name, comment_id):
        """ Id of the crm.lead already created from this exact comment (via
        create_lead/_ig/_youtube), if any - lets the frontend show "View
        Lead" instead of "Create Lead" without a round trip. """
        if not comment_id:
            return False
        lead = self.env['crm.lead'].sudo().search([(unique_field_name, '=', comment_id)], limit=1)
        return lead.id if lead else False

    def _parse_date(self, value):
        """ Normalize any platform's date string (ISO-with-offset, ISO-Z, ...)
        to Odoo's own datetime string format, so the frontend's single
        deserializeDateTime-based formatter works for every platform without
        per-format branching. """
        if not value:
            return value
        try:
            from dateutil import parser as date_parser
            return date_parser.parse(str(value)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return value

    def _fetch_posts(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_videos(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_comments(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_mentions(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_unpublished(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_hashtag_recent(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_hashtag_trending(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_moderate(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_likely_spam(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_search(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))

    def _fetch_playlist(self, cursor=None):
        raise UserError(_("Not implemented for this platform."))
