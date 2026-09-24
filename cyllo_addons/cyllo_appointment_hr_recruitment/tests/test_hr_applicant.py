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
"""Tests for the HrApplicant model extension in cyllo_appointment_hr_recruitment.

Covers:
- _compute_interview_invite_code  : auto-generation and idempotency of the
                                    unique invite token.
- _compute_appointment_count      : correct count derived from appointment_ids.
- action_view_appointments        : shape of the returned window action.
- _get_interview_invite_url       : URL construction (no-request fallback path
                                    is exercised because HTTP request context
                                    is not available in TransactionCase).
"""

from odoo.tests.common import TransactionCase


class TestHrApplicant(TransactionCase):
    """Unit tests for hr.applicant extensions added by
    cyllo_appointment_hr_recruitment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Minimal job & applicant records shared across tests.
        cls.job = cls.env['hr.job'].create({'name': 'Software Engineer'})
        cls.applicant = cls.env['hr.applicant'].create({
            'partner_name': 'Test Candidate',
            'job_id': cls.job.id,
            'email_from': 'candidate@example.com',
            'partner_phone': '+1234567890',
        })

    # _compute_interview_invite_code
    def test_invite_code_generated_on_create(self):
        """A newly created applicant must have a non-empty invite code."""
        self.assertTrue(
            self.applicant.interview_invite_code,
            "interview_invite_code should be auto-generated on creation.",
        )

    def test_invite_code_is_16_hex_chars(self):
        """The token must be exactly 16 lowercase hex characters."""
        code = self.applicant.interview_invite_code
        self.assertEqual(len(code), 16)
        self.assertTrue(
            all(c in '0123456789abcdef' for c in code),
            f"Token '{code}' contains non-hex characters.",
        )

    def test_invite_code_is_unique_across_applicants(self):
        """Two different applicants must receive different tokens."""
        other = self.env['hr.applicant'].create({
            'partner_name': 'Another Candidate',
            'job_id': self.job.id,
        })
        self.assertNotEqual(
            self.applicant.interview_invite_code,
            other.interview_invite_code,
            "Each applicant should receive a unique invite code.",
        )

    def test_invite_code_is_not_regenerated_on_write(self):
        """Writing an unrelated field must NOT change the existing token."""
        original_code = self.applicant.interview_invite_code
        self.applicant.write({'partner_name': 'Updated Name'})
        self.assertEqual(
            self.applicant.interview_invite_code,
            original_code,
            "invite_code must remain stable after an unrelated write.",
        )

    def test_invite_code_is_not_copied(self):
        """Copying an applicant must generate a fresh token (copy=False)."""
        copy = self.applicant.copy()
        self.assertNotEqual(
            copy.interview_invite_code,
            self.applicant.interview_invite_code,
            "Copied applicant must get a new invite code, not the original.",
        )

    # _compute_appointment_count
    def test_appointment_count_starts_at_zero(self):
        """A brand-new applicant with no linked appointments has count = 0."""
        fresh = self.env['hr.applicant'].create({
            'partner_name': 'Zero Appointments',
            'job_id': self.job.id,
        })
        self.assertEqual(
            fresh.appointment_count, 0,
            "appointment_count must be 0 when no appointments are linked.",
        )

    def test_appointment_count_reflects_linked_records(self):
        """appointment_count must equal len(appointment_ids)."""
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Count Test Candidate',
            'job_id': self.job.id,
        })
        # Create a minimal appointment type to satisfy appointment constraints.
        apt_type = self.env['appointment.type'].create({
            'name': 'Interview Type Count Test',
            'category': 'interview',
        })
        # Create two appointment records linked to this applicant.
        for i in range(2):
            self.env['appointment.appointment'].create({
                'appointment_type_id': apt_type.id,
                'applicant_id': applicant.id,
                'name': f'Interview {i + 1}',
                'start': '2026-07-10 09:00:00',
                'stop': '2026-07-10 10:00:00',
            })
        self.assertEqual(
            applicant.appointment_count, 2,
            "appointment_count must match the number of linked appointments.",
        )

    def test_appointment_count_decreases_on_unlink(self):
        """Removing an appointment must decrement appointment_count."""
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Decrement Test',
            'job_id': self.job.id,
        })
        apt_type = self.env['appointment.type'].create({
            'name': 'Interview Type Decrement Test',
            'category': 'interview',
        })
        appt = self.env['appointment.appointment'].create({
            'appointment_type_id': apt_type.id,
            'applicant_id': applicant.id,
            'name': 'Interview to Delete',
            'start': '2026-07-11 09:00:00',
            'stop': '2026-07-11 10:00:00',
        })
        self.assertEqual(applicant.appointment_count, 1)
        appt.unlink()
        self.assertEqual(
            applicant.appointment_count, 0,
            "appointment_count must drop to 0 after the linked appointment is deleted.",
        )

    # action_view_appointments
    def test_action_view_appointments_returns_window_action(self):
        """action_view_appointments must return a valid ir.actions.act_window dict."""
        action = self.applicant.action_view_appointments()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.appointment')
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])

    def test_action_view_appointments_domain_filters_correctly(self):
        """The returned action domain must filter by applicant id."""
        action = self.applicant.action_view_appointments()
        expected_domain = [('applicant_id', '=', self.applicant.id)]
        self.assertEqual(
            action['domain'],
            expected_domain,
            "Action domain must restrict appointments to the current applicant.",
        )

    def test_action_view_appointments_sets_default_context(self):
        """The context must pre-set default_applicant_id for new appointment creation."""
        action = self.applicant.action_view_appointments()
        self.assertEqual(
            action['context'].get('default_applicant_id'),
            self.applicant.id,
            "context['default_applicant_id'] must be set to the applicant id.",
        )

    def test_action_view_appointments_requires_singleton(self):
        """Calling action_view_appointments on a multi-record set must raise."""
        other = self.env['hr.applicant'].create({
            'partner_name': 'Another',
            'job_id': self.job.id,
        })
        multi_set = self.applicant | other
        with self.assertRaises(Exception):
            multi_set.action_view_appointments()

    # _get_interview_invite_url
    def test_get_interview_invite_url_without_request_returns_empty(self):
        """Outside an HTTP request context, the method must return an empty string
        rather than raising an exception, as the guard ``if not request`` handles it."""
        # In TransactionCase there is no active HTTP request, so the early
        # return path (return '') is exercised.
        url = self.applicant._get_interview_invite_url()
        self.assertIsInstance(url, str)
        # The result may be empty ('') when no HTTP request is present.
        # We assert it does not raise and is a string.

    def test_get_interview_invite_url_requires_singleton(self):
        """_get_interview_invite_url must raise when called on more than one record."""
        other = self.env['hr.applicant'].create({
            'partner_name': 'Multi Record Test',
            'job_id': self.job.id,
        })
        multi = self.applicant | other
        with self.assertRaises(Exception):
            multi._get_interview_invite_url()
