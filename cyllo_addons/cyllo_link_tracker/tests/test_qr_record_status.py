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

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQrRecordStatus(TransactionCase):
    """Tests for the qr.record.status SQL view model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env['ir.actions.report'].search(
            [('model', '=', 'res.partner')], limit=1,
        )
        if not cls.report:
            cls.report = cls.env['ir.actions.report'].create({
                'name': 'Test Partner Report',
                'model': 'res.partner',
                'report_type': 'qweb-pdf',
                'report_name': 'cyllo_link_tracker.test_partner_report',
            })

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Status Test Partner A',
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'Status Test Partner B',
        })

        cls.token = cls.env['qr.download.token'].create({
            'report_id': cls.report.id,
            'track_analytics': True,
        })

    # ── Basic aggregation ─────────────────────────────────────────

    def test_status_row_appears_after_scan(self):
        """A qr.record.status row should appear once a scan event exists."""
        # Before any scans there should be no rows for our token
        statuses_before = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
        ])
        self.assertFalse(statuses_before)

        # Create a scan event
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': fields.Datetime.now(),
        })

        statuses_after = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        self.assertTrue(statuses_after)
        self.assertEqual(statuses_after.scan_count, 1)
        self.assertTrue(statuses_after.is_scanned)

    def test_scan_count_aggregation(self):
        """Multiple scans on the same (token, record_id) should aggregate."""
        for _ in range(3):
            self.env['qr.scan.event'].create({
                'token_id': self.token.id,
                'record_id': self.partner_a.id,
                'scanned_at': fields.Datetime.now(),
            })

        status = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        self.assertEqual(status.scan_count, 3)

    def test_last_scanned_at_picks_max(self):
        """last_scanned_at should reflect the MAX(scanned_at) from events."""
        earlier = fields.Datetime.now() - timedelta(hours=5)
        later = fields.Datetime.now()

        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': earlier,
        })
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': later,
        })

        status = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        self.assertEqual(status.last_scanned_at, later)

    # ── Multi-record separation ───────────────────────────────────

    def test_separate_rows_per_record(self):
        """Different record_ids under the same token get separate rows."""
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': fields.Datetime.now(),
        })
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_b.id,
            'scanned_at': fields.Datetime.now(),
        })

        statuses = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
        ])
        record_ids = statuses.mapped('record_id')
        self.assertIn(self.partner_a.id, record_ids)
        self.assertIn(self.partner_b.id, record_ids)

    # ── Reflects token fields ─────────────────────────────────────

    def test_track_analytics_flag_reflected(self):
        """track_analytics from the token should appear on the status row."""
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': fields.Datetime.now(),
        })
        status = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        self.assertTrue(status.track_analytics)

    def test_report_name_populated(self):
        """report_name should come from the ir.actions.report name."""
        self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': fields.Datetime.now(),
        })
        status = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        self.assertTrue(status.report_name)

    # ── Read-only enforcement ─────────────────────────────────────

    def test_read_only_no_create(self):
        """qr.record.status is a SQL view — direct create must fail."""
        with self.assertRaises(Exception):
            self.env['qr.record.status'].create({
                'token_id': self.token.id,
                'record_id': self.partner_a.id,
                'scan_count': 1,
            })

    def test_record_name_from_reference(self):
        """record_name should come from scan event record_reference."""
        event = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner_a.id,
            'scanned_at': fields.Datetime.now(),
        })
        self.env.flush_all()
        status = self.env['qr.record.status'].search([
            ('token_id', '=', self.token.id),
            ('record_id', '=', self.partner_a.id),
        ])
        # record_name comes from se.record_reference in the SQL view
        self.assertEqual(status.record_name, event.record_reference)
