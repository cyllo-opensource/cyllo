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
import uuid
from odoo import api, fields, models


class QrDownloadToken(models.Model):
    _name = 'qr.download.token'
    _description = 'QR Code PDF Download Token'

    name = fields.Char(string="Name", compute="_compute_name")
    token = fields.Char(string='Token', required=True, copy=False, default=lambda self: str(uuid.uuid4()), index=True)
    report_id = fields.Many2one('ir.actions.report', string='Report', required=True, ondelete='cascade')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)
    expires_at = fields.Datetime(string='Expires At')
    max_scans = fields.Integer(string='Max Scans', default=0, help="0 means unlimited scans")
    scan_count = fields.Integer(string='Scan Count', default=0)
    require_auth = fields.Boolean(string='Require Authentication', default=False)
    track_analytics = fields.Boolean(string='Track Analytics', default=True)

    @api.depends('report_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Token for {rec.report_id.name or 'Report'}"

    def is_valid(self):
        """Check if the token is still valid for downloading the PDF."""
        self.ensure_one()
        if self.expires_at and fields.Datetime.now() > self.expires_at:
            return False
        if self.max_scans > 0 and self.scan_count >= self.max_scans:
            return False
        return True


class QrScanEvent(models.Model):
    _name = 'qr.scan.event'
    _description = 'QR Code Scan Event Analytics'

    token_id = fields.Many2one('qr.download.token', string='Token', ondelete='cascade')
    report_id = fields.Many2one('ir.actions.report', string='Report', related='token_id.report_id', store=True)
    record_id = fields.Integer(string='Record ID', index=True)
    scanned_at = fields.Datetime(string='Scanned At', default=fields.Datetime.now)
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Text(string='User Agent')
    record_ref = fields.Char(string='Record Reference', compute='_compute_record_ref')

    @api.depends('record_id', 'report_id.model')
    def _compute_record_ref(self):
        for rec in self:
            if rec.record_id and rec.report_id and rec.report_id.model:
                try:
                    record = self.env[rec.report_id.model].sudo().browse(rec.record_id)
                    rec.record_ref = record.display_name if record.exists() else f"ID: {rec.record_id}"
                except Exception:
                    rec.record_ref = f"ID: {rec.record_id}"
            else:
                rec.record_ref = "Unknown"
