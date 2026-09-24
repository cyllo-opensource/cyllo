# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import api, fields, models


class QrDownloadTokenTracker(models.Model):
    """
    Extension of qr.download.token to provide computed helper fields
    used by the cyllo_link_tracker QR Overview and Record QR Status pages.
    """
    _inherit = 'qr.download.token'

    # ── Computed: is this token effectively "tracked" (enabled + at least 1 scan) ─
    is_scanned = fields.Boolean(
        string='Has Been Scanned',
        compute='_compute_is_scanned',
        store=True,
        help="True when this QR token has at least one recorded scan event.",
    )
    last_scanned_at = fields.Datetime(
        string='Last Scanned',
        compute='_compute_is_scanned',
        store=True,
        help="Timestamp of the most recent scan event for this token.",
    )
    scan_event_ids = fields.One2many(
        'qr.scan.event', 'token_id', string='Scan Events',
    )
    record_status_ids = fields.One2many(
        'qr.record.status', 'token_id', string='Record Status',
        help="SQL view showing scan status per record for this token."
    )
    report_model = fields.Char(
        string='Report Model',
        related='report_id.model',
        readonly=True,
    )
    tracking_status = fields.Selection(
        selection=[
            ('tracked_scanned', 'Tracked & Scanned'),
            ('tracked_unscanned', 'Tracked — Not Yet Scanned'),
            ('not_tracked', 'Not Tracked'),
        ],
        string='Tracking Status',
        compute='_compute_tracking_status',
        store=True,
    )

    @api.depends('scan_event_ids', 'scan_event_ids.scanned_at', 'scan_count')
    def _compute_is_scanned(self):
        for rec in self:
            events = rec.scan_event_ids.sorted('scanned_at', reverse=True)
            rec.is_scanned = bool(events)
            rec.last_scanned_at = events[0].scanned_at if events else False

    @api.depends('track_analytics', 'is_scanned')
    def _compute_tracking_status(self):
        for rec in self:
            if not rec.track_analytics:
                rec.tracking_status = 'not_tracked'
            elif rec.is_scanned:
                rec.tracking_status = 'tracked_scanned'
            else:
                rec.tracking_status = 'tracked_unscanned'


class QrScanEventTracker(models.Model):
    """
    Extension of qr.scan.event with extra helpers for the Record QR Status.
    """
    _inherit = 'qr.scan.event'

    report_model = fields.Char(
        string='Report Model',
        related='report_id.model',
        store=True,
        readonly=True,
    )
    record_reference = fields.Char(
        string='Record Reference',
        compute='_compute_record_reference',
        store=True,
    )

    @api.depends('record_id', 'report_model')
    def _compute_record_reference(self):
        for rec in self:
            if rec.record_id and rec.report_model:
                try:
                    record = self.env[rec.report_model].sudo().browse(rec.record_id)
                    rec.record_reference = record.display_name if record.exists() else f"ID: {rec.record_id}"
                except Exception:
                    rec.record_reference = f"ID: {rec.record_id}"
            else:
                rec.record_reference = 'Unknown'
