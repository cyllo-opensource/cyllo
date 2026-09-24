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

from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AssetBooking(models.Model):
    _name = 'asset.booking'
    _order = 'date_from'

    asset_id = fields.Many2one(
        'asset.asset',
        required=True,
        help='Asset associated with this booking.'
    )
    booking_type = fields.Selection(
        [
            ('maintenance', 'Maintenance'),
            ('lease', 'Lease'),
            ('rental', 'Rental'),
        ],
        required=True,
        help='Type of booking created for the asset.'
    )
    date_from = fields.Datetime(
        required=True,
        help='Start date and time of the booking.'
    )
    date_to = fields.Datetime(
        required=True,
        help='End date and time of the booking.'
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        help='Current status of the booking.'
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help='Company responsible for this booking.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        help='Customer or contact linked to the booking.'
    )
    res_model = fields.Char(
        index=True,
        help='Technical model name of the related document.'
    )
    res_id = fields.Integer(
        index=True,
        help='Record ID of the related document.'
    )

    def _get_buffered_end(self, asset, date_to):
        """Return date_to extended by asset buffer"""
        if not asset.buffer_duration:
            return date_to
        if asset.buffer_period == 'hour':
            return date_to + timedelta(hours=asset.buffer_duration)
        elif asset.buffer_period == 'day':
            return date_to + timedelta(days=asset.buffer_duration)
        elif asset.buffer_period == 'week':
            return date_to + timedelta(weeks=asset.buffer_duration)

        return date_to

    def _check_overlap(self, asset_id, date_from, date_to, exclude_id=False):
        """Validate that the asset is available during the selected
        date range, including the configured cooldown period."""
        asset = self.env['asset.asset'].browse(asset_id)
        buffered_date_to = self._get_buffered_end(asset, date_to)
        domain = [('asset_id', '=', asset_id), ('state', 'in', ['draft', 'confirmed']),
                  ('date_from', '<', buffered_date_to), ('date_to', '>', date_from), ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        if self.search_count(domain):
            raise ValidationError(_('Asset is not available due to cooldown period.'))

    @api.model
    def create_or_update_booking(self, *, asset, date_from, date_to,
                                 booking_type, partner=None, res_model=None, res_id=None):
        """Create a new booking or update an existing booking linked
        to the provided business document."""
        booking = self.search([('res_model', '=', res_model), ('res_id', '=', res_id), ], limit=1)
        self._check_overlap(
            asset.id, date_from, date_to,
            exclude_id=booking.id if booking else False
        )
        vals = {
            'asset_id': asset.id,
            'booking_type': booking_type,
            'date_from': date_from,
            'date_to': date_to,
            'partner_id': partner.id if partner else False,
            'res_model': res_model,
            'res_id': res_id,
            'state': 'draft',
        }
        return booking.write(vals) and booking if booking else self.create(vals)
