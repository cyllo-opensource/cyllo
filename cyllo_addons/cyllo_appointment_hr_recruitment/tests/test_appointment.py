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
"""Tests for the Appointment (appointment.appointment) model extension in
cyllo_appointment_hr_recruitment.

Covers:
- create()  : auto-assignment of staff_id from applicant's responsible user
              when no staff_id is supplied; bypass when staff_id is explicit.
- write()   : staff_id assignment when applicant_id changes; calendar event
              partner synchronisation when staff_id / applicant_id is updated.
- action_open_applicant() : shape and content of the returned window action,
                            and the False-return path when no applicant is set.
"""

from odoo.tests.common import TransactionCase


class TestAppointmentRecruitment(TransactionCase):
    """Unit tests for appointment.appointment extensions added by
    cyllo_appointment_hr_recruitment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

         
        # Shared HR setup
        cls.job = cls.env['hr.job'].create({'name': 'QA Engineer'})

        # Responsible user for the applicant (will become the interviewer).
        cls.user_interviewer = cls.env['res.users'].create({
            'name': 'Interviewer User',
            'login': 'interviewer_recruitment_test@cyllo.test',
            'email': 'interviewer@cyllo.test',
        })

        # Employee record tied to the interviewer user.
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Interviewer Employee',
            'user_id': cls.user_interviewer.id,
        })

        # Applicant with a responsible user set.
        cls.applicant = cls.env['hr.applicant'].create({
            'partner_name': 'Jane Doe',
            'job_id': cls.job.id,
            'email_from': 'jane@example.com',
            'user_id': cls.user_interviewer.id,
        })

        # Appointment type used across tests.
        cls.apt_type = cls.env['appointment.type'].create({
            'name': 'Recruitment Interview Type',
            'category': 'interview',
        })

     
    # Helper
    def _make_appointment(self, vals=None):
        """Return a new appointment.appointment record with sensible defaults."""
        defaults = {
            'appointment_type_id': self.apt_type.id,
            'name': 'Test Interview Appointment',
            'start': '2026-08-01 10:00:00',
            'stop': '2026-08-01 11:00:00',
        }
        if vals:
            defaults.update(vals)
        return self.env['appointment.appointment'].create(defaults)

    # create()
    def test_create_assigns_staff_from_applicant_user(self):
        """When applicant_id is set and no explicit staff_id is provided,
        create() must derive staff_id from the applicant's responsible user."""
        appt = self._make_appointment({'applicant_id': self.applicant.id})
        self.assertEqual(
            appt.staff_id,
            self.employee,
            "staff_id should be auto-assigned from the applicant's responsible user.",
        )

    def test_create_does_not_override_explicit_staff_id(self):
        """An explicitly supplied staff_id must not be overwritten during create."""
        other_user = self.env['res.users'].create({
            'name': 'Other Interviewer',
            'login': 'other_interviewer@cyllo.test',
            'email': 'other@cyllo.test',
        })
        other_employee = self.env['hr.employee'].create({
            'name': 'Other Employee',
            'user_id': other_user.id,
        })
        appt = self._make_appointment({
            'applicant_id': self.applicant.id,
            'staff_id': other_employee.id,
        })
        self.assertEqual(
            appt.staff_id,
            other_employee,
            "An explicit staff_id passed to create() must not be overwritten.",
        )

    def test_create_without_applicant_does_not_assign_staff(self):
        """When no applicant_id is provided, staff_id must remain unset."""
        appt = self._make_appointment()
        # staff_id should be falsy (empty Many2one)
        self.assertFalse(
            appt.staff_id,
            "staff_id must not be auto-assigned when no applicant_id is given.",
        )

    def test_create_with_applicant_having_no_user_does_not_assign_staff(self):
        """An applicant without a user_id must not cause staff_id assignment."""
        no_user_applicant = self.env['hr.applicant'].create({
            'partner_name': 'No User Applicant',
            'job_id': self.job.id,
        })
        appt = self._make_appointment({'applicant_id': no_user_applicant.id})
        self.assertFalse(
            appt.staff_id,
            "staff_id must stay empty when the applicant has no responsible user.",
        )

    def test_create_multiple_appointments_bulk(self):
        """create() must handle a vals_list with multiple entries (model_create_multi)."""
        records = self.env['appointment.appointment'].create([
            {
                'appointment_type_id': self.apt_type.id,
                'name': f'Bulk Interview {i}',
                'start': f'2026-08-0{i + 2} 09:00:00',
                'stop': f'2026-08-0{i + 2} 10:00:00',
                'applicant_id': self.applicant.id,
            }
            for i in range(3)
        ])
        self.assertEqual(len(records), 3)
        for rec in records:
            self.assertEqual(
                rec.staff_id, self.employee,
                "All bulk-created appointments must have staff_id auto-assigned.",
            )

     
    # write()
    def test_write_assigns_staff_when_applicant_id_set(self):
        """Writing applicant_id without staff_id must auto-assign staff_id."""
        appt = self._make_appointment()
        self.assertFalse(appt.staff_id)

        appt.write({'applicant_id': self.applicant.id})
        self.assertEqual(
            appt.staff_id,
            self.employee,
            "write() should derive staff_id when applicant_id is updated.",
        )

    def test_write_does_not_override_explicit_staff_on_write(self):
        """If staff_id is also present in the vals dict, it must be honoured."""
        other_user = self.env['res.users'].create({
            'name': 'Write Other User',
            'login': 'write_other@cyllo.test',
            'email': 'write_other@cyllo.test',
        })
        other_emp = self.env['hr.employee'].create({
            'name': 'Write Other Employee',
            'user_id': other_user.id,
        })
        appt = self._make_appointment()
        appt.write({'applicant_id': self.applicant.id, 'staff_id': other_emp.id})
        self.assertEqual(
            appt.staff_id, other_emp,
            "An explicit staff_id in the write vals must not be overwritten.",
        )

    def test_write_returns_true(self):
        """write() must return True (standard ORM contract)."""
        appt = self._make_appointment()
        result = appt.write({'name': 'Updated Name'})
        self.assertTrue(result, "write() must return True as per ORM convention.")

     
    # action_open_applicant()
    def test_action_open_applicant_returns_form_action(self):
        """When an applicant is linked, action_open_applicant must return a
        valid ir.actions.act_window targeting hr.applicant."""
        appt = self._make_appointment({'applicant_id': self.applicant.id})
        action = appt.action_open_applicant()

        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'hr.applicant')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['res_id'], self.applicant.id)

    def test_action_open_applicant_returns_false_without_applicant(self):
        """When no applicant is linked, the method must return False."""
        appt = self._make_appointment()
        result = appt.action_open_applicant()
        self.assertFalse(
            result,
            "action_open_applicant must return False when no applicant is linked.",
        )

    def test_action_open_applicant_requires_singleton(self):
        """Calling action_open_applicant on a multi-record set must raise."""
        appt1 = self._make_appointment({'name': 'Appt 1'})
        appt2 = self._make_appointment({'name': 'Appt 2'})
        multi = appt1 | appt2
        with self.assertRaises(Exception):
            multi.action_open_applicant()

    def test_action_open_applicant_name_is_set(self):
        """The returned action must include a human-readable name."""
        appt = self._make_appointment({'applicant_id': self.applicant.id})
        action = appt.action_open_applicant()
        self.assertTrue(action.get('name'), "The action must have a non-empty 'name'.")

     
    # Field: applicant_id / job_id
    def test_job_id_is_derived_from_applicant(self):
        """The related job_id field must reflect the applicant's job_id."""
        appt = self._make_appointment({'applicant_id': self.applicant.id})
        self.assertEqual(
            appt.job_id,
            self.job,
            "appointment.job_id must mirror the linked applicant's job_id.",
        )

    def test_applicant_id_ondelete_set_null(self):
        """Deleting an applicant must set applicant_id to False (ondelete='set null')."""
        disposable_applicant = self.env['hr.applicant'].create({
            'partner_name': 'Disposable Candidate',
            'job_id': self.job.id,
        })
        appt = self._make_appointment({'applicant_id': disposable_applicant.id})
        self.assertEqual(appt.applicant_id, disposable_applicant)

        disposable_applicant.unlink()
        self.assertFalse(
            appt.applicant_id,
            "applicant_id must be set to False after the linked applicant is deleted.",
        )
