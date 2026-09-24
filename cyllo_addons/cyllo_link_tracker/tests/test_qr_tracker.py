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

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQrDownloadTokenTracker(TransactionCase):
    """Tests for the qr.download.token computed fields added by
    cyllo_link_tracker: is_scanned, last_scanned_at, tracking_status,
    report_model, and scan_event_ids."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Grab an existing report to link tokens against.
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

        # A test partner to act as "the printed record"
        cls.partner = cls.env['res.partner'].create({
            'name': 'Link Tracker Test Partner',
        })

        # QR token with analytics ON
        cls.token_tracked = cls.env['qr.download.token'].create({
            'report_id': cls.report.id,
            'track_analytics': True,
        })

        # QR token with analytics OFF
        cls.token_untracked = cls.env['qr.download.token'].create({
            'report_id': cls.report.id,
            'track_analytics': False,
        })

    # ── is_scanned / last_scanned_at ──────────────────────────────

    def test_is_scanned_false_when_no_events(self):
        """Token with no scan events should have is_scanned=False."""
        self.assertFalse(self.token_tracked.is_scanned)
        self.assertFalse(self.token_tracked.last_scanned_at)

    def test_is_scanned_true_after_scan_event(self):
        """Creating a scan event should flip is_scanned to True."""
        self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
            'scanned_at': fields.Datetime.now(),
        })
        self.token_tracked.invalidate_recordset()
        self.assertTrue(self.token_tracked.is_scanned)

    def test_last_scanned_at_picks_most_recent(self):
        """last_scanned_at should be the timestamp of the latest scan."""
        earlier = fields.Datetime.now() - timedelta(hours=3)
        later = fields.Datetime.now()
        self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
            'scanned_at': earlier,
        })
        self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
            'scanned_at': later,
        })
        self.token_tracked.invalidate_recordset()
        self.assertEqual(self.token_tracked.last_scanned_at, later)

    # ── tracking_status ───────────────────────────────────────────

    def test_tracking_status_not_tracked(self):
        """Token with track_analytics=False → 'not_tracked'."""
        self.assertEqual(self.token_untracked.tracking_status, 'not_tracked')

    def test_tracking_status_tracked_unscanned(self):
        """Tracked token with zero scans → 'tracked_unscanned'."""
        self.assertEqual(
            self.token_tracked.tracking_status, 'tracked_unscanned',
        )

    def test_tracking_status_tracked_scanned(self):
        """Tracked token with ≥1 scan → 'tracked_scanned'."""
        self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
            'scanned_at': fields.Datetime.now(),
        })
        self.token_tracked.invalidate_recordset()
        self.assertEqual(
            self.token_tracked.tracking_status, 'tracked_scanned',
        )

    def test_tracking_status_changes_when_analytics_toggled(self):
        """Toggling track_analytics should update tracking_status."""
        self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
            'scanned_at': fields.Datetime.now(),
        })
        self.token_tracked.invalidate_recordset()
        self.assertEqual(
            self.token_tracked.tracking_status, 'tracked_scanned',
        )

        # Turn analytics OFF
        self.token_tracked.write({'track_analytics': False})
        self.assertEqual(self.token_tracked.tracking_status, 'not_tracked')

        # Turn analytics back ON — token still has events
        self.token_tracked.write({'track_analytics': True})
        self.assertEqual(
            self.token_tracked.tracking_status, 'tracked_scanned',
        )

    # ── report_model (related field) ──────────────────────────────

    def test_report_model_value(self):
        """report_model should reflect the linked ir.actions.report.model."""
        self.assertEqual(
            self.token_tracked.report_model, self.report.model,
        )

    # ── scan_event_ids One2many ───────────────────────────────────

    def test_scan_event_ids_populated(self):
        """scan_event_ids should contain all scan events for the token."""
        ev1 = self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
        })
        ev2 = self.env['qr.scan.event'].create({
            'token_id': self.token_tracked.id,
            'record_id': self.partner.id,
        })
        self.token_tracked.invalidate_recordset()
        self.assertEqual(
            self.token_tracked.scan_event_ids, ev1 | ev2,
        )


@tagged('post_install', '-at_install')
class TestQrScanEventTracker(TransactionCase):
    """Tests for the qr.scan.event computed fields added by
    cyllo_link_tracker: report_model, record_reference."""

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

        cls.partner = cls.env['res.partner'].create({
            'name': 'Link Tracker Test Partner',
        })

        cls.token = cls.env['qr.download.token'].create({
            'report_id': cls.report.id,
            'track_analytics': True,
        })

    # ── report_model ──────────────────────────────────────────────

    def test_report_model_stored(self):
        """report_model should be stored and equal to the report's model."""
        event = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner.id,
        })
        self.assertEqual(event.report_model, 'res.partner')

    # ── record_reference ──────────────────────────────────────────

    def test_record_reference_with_valid_record(self):
        """record_reference should be the display_name of the linked record."""
        event = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner.id,
        })
        self.assertEqual(event.record_reference, self.partner.display_name)

    def test_record_reference_with_deleted_record(self):
        """record_reference should fall back to 'ID: <id>' for deleted records."""
        dead_id = self.partner.id
        event = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': dead_id,
            'scanned_at': fields.Datetime.now(),
        })
        # Confirm initial state is the partner's display name
        self.assertEqual(event.record_reference, self.partner.display_name)

        # Delete the partner record
        self.partner.unlink()

        # Stored compute won't re-trigger because record_id & report_model
        # haven't changed — force recomputation to exercise the fallback.
        event._compute_record_reference()
        self.assertEqual(event.record_reference, f"ID: {dead_id}")

    def test_record_reference_without_record_id(self):
        """record_reference should be 'Unknown' when record_id is 0/False."""
        event = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': 0,
        })
        self.assertEqual(event.record_reference, 'Unknown')

    def test_record_reference_with_invalid_model(self):
        """record_reference should fall back to 'ID: <id>' for bad models."""
        bogus_report = self.env['ir.actions.report'].create({
            'name': 'Bogus Report',
            'model': 'no.such.model',
            'report_type': 'qweb-pdf',
            'report_name': 'cyllo_link_tracker.bogus_report',
        })
        bogus_token = self.env['qr.download.token'].create({
            'report_id': bogus_report.id,
        })
        event = self.env['qr.scan.event'].create({
            'token_id': bogus_token.id,
            'record_id': self.partner.id,
        })
        self.assertEqual(event.record_reference, f"ID: {self.partner.id}")

    def test_multiple_events_different_records(self):
        """Each scan event should reference its own record independently."""
        partner_2 = self.env['res.partner'].create({
            'name': 'Second Test Partner',
        })
        ev1 = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': self.partner.id,
        })
        ev2 = self.env['qr.scan.event'].create({
            'token_id': self.token.id,
            'record_id': partner_2.id,
        })
        self.assertEqual(ev1.record_reference, self.partner.display_name)
        self.assertEqual(ev2.record_reference, partner_2.display_name)
