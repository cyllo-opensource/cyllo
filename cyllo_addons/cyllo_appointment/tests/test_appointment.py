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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from odoo import fields


class TestAppointment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Test Staff'})

        # Basic (free, no staff required) appointment type
        cls.appt_type = cls.env['appointment.type'].create({
            'name': 'Basic Type',
            'duration': 1.0,
            'slot_interval': '60',
            'min_booking_notice': 0.0,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': False,
            'require_resource': False,
            'send_confirmation': False,
            'send_reminder': False,
            'send_followup': False,
            'send_cancellation': False,
            'allow_reschedule': True,
            'reschedule_deadline_hours': 0.0,
        })
        # Future start times to avoid min_booking_notice issues
        cls.future_start = fields.Datetime.now() + timedelta(days=5)
        cls.future_end = cls.future_start + timedelta(hours=1)

    def _create_appt(self, start=None, end=None, state='draft', **kwargs):
        start = start or self.future_start
        end = end or self.future_end
        vals = {
            'appointment_type_id': self.appt_type.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'state': state,
        }
        vals.update(kwargs)
        return self.env['appointment.appointment'].create(vals)

     
    # create – sequence generation
    def test_create_generates_sequence(self):
        appt = self._create_appt()
        self.assertNotEqual(appt.name, 'New')
        self.assertTrue(appt.name)

    def test_create_access_token_set(self):
        appt = self._create_appt()
        self.assertTrue(appt.access_token)

     
    # _compute_display_name
    def test_compute_display_name(self):
        appt = self._create_appt()
        appt._compute_display_name()
        self.assertIn(self.partner.name, appt.display_name)
        self.assertIn(self.appt_type.name, appt.display_name)

    def test_compute_display_name_no_type(self):
        # display_name should still work when type is cleared (edge case)
        appt = self._create_appt()
        appt.appointment_type_id = False
        appt._compute_display_name()
        self.assertTrue(appt.display_name)

     
    # _compute_meeting_subject
    def test_compute_meeting_subject(self):
        appt = self._create_appt()
        appt._compute_meeting_subject()
        self.assertIn(self.partner.name, appt.meeting_subject)
        self.assertIn(self.appt_type.name, appt.meeting_subject)

    def test_compute_meeting_subject_with_booker_name(self):
        appt = self._create_appt(booker_name='Walk-in Customer')
        appt._compute_meeting_subject()
        self.assertIn('Walk-in Customer', appt.meeting_subject)

     
    # _compute_duration
    def test_compute_duration(self):
        start = fields.Datetime.now() + timedelta(days=5)
        end = start + timedelta(hours=2)
        appt = self._create_appt(start=start, end=end)
        appt._compute_duration()
        self.assertAlmostEqual(appt.duration, 2.0, places=2)

    def test_compute_duration_zero_when_no_times(self):
        appt = self._create_appt()
        appt.start_datetime = False
        appt._compute_duration()
        self.assertEqual(appt.duration, 0.0)

     
    # _compute_color
    def test_compute_color_draft(self):
        appt = self._create_appt(state='draft')
        appt._compute_color()
        self.assertEqual(appt.color, 0)

    def test_compute_color_confirmed(self):
        appt = self._create_appt(state='confirmed')
        appt._compute_color()
        self.assertEqual(appt.color, 1)

    def test_compute_color_done(self):
        appt = self._create_appt(state='done')
        appt._compute_color()
        self.assertEqual(appt.color, 10)

    def test_compute_color_cancelled(self):
        appt = self._create_appt(state='cancelled')
        appt._compute_color()
        self.assertEqual(appt.color, 9)

     
    # _compute_staff_resource_domain
    def test_compute_staff_resource_domain_empty(self):
        appt = self._create_appt()
        appt._compute_staff_resource_domain()
        self.assertEqual(appt.staff_domain, '[]')
        self.assertEqual(appt.resource_domain, '[]')

    def test_compute_staff_resource_domain_with_staff(self):
        self.appt_type.write({'staff_ids': [(4, self.employee.id)]})
        appt = self._create_appt()
        appt._compute_staff_resource_domain()
        self.assertIn(str(self.appt_type.id), appt.staff_domain)
        # cleanup
        self.appt_type.write({'staff_ids': [(3, self.employee.id)]})

     
    # _check_dates constraint
    def test_check_dates_valid(self):
        appt = self._create_appt()
        self.assertTrue(appt.id)

    def test_check_dates_end_before_start(self):
        start = fields.Datetime.now() + timedelta(days=6)
        with self.assertRaises(ValidationError):
            self._create_appt(start=start, end=start - timedelta(hours=1))

     
    # _check_overlap constraint
    def test_check_overlap_same_staff_raises(self):
        start = fields.Datetime.now() + timedelta(days=7)
        end = start + timedelta(hours=1)
        # Create the first appointment with staff
        self.appt_type.write({'require_staff': True})
        self.env['appointment.appointment'].create({
            'appointment_type_id': self.appt_type.id,
            'partner_id': self.partner.id,
            'start_datetime': start,
            'end_datetime': end,
            'staff_id': self.employee.id,
            'state': 'confirmed',
        })
        with self.assertRaises(ValidationError):
            self.env['appointment.appointment'].create({
                'appointment_type_id': self.appt_type.id,
                'partner_id': self.partner.id,
                'start_datetime': start,
                'end_datetime': end,
                'staff_id': self.employee.id,
                'state': 'confirmed',
            })
        # cleanup
        self.appt_type.write({'require_staff': False})

    def test_check_overlap_cancelled_does_not_block(self):
        """A cancelled appointment should not block the same time slot."""
        start = fields.Datetime.now() + timedelta(days=8)
        end = start + timedelta(hours=1)
        appt1 = self._create_appt(start=start, end=end, state='cancelled')
        # Same slot → should succeed
        appt2 = self._create_appt(start=start, end=end, state='confirmed')
        self.assertTrue(appt2.id)

     
    # _check_min_booking_notice constraint
    def test_check_min_booking_notice_blocks_too_soon(self):
        appt_type_strict = self.env['appointment.type'].create({
            'name': 'Strict Notice',
            'duration': 1.0,
            'min_booking_notice': 48.0,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': False,
        })
        # Trying to book 1 hour from now violates 48h notice
        too_soon = fields.Datetime.now() + timedelta(hours=1)
        with self.assertRaises(ValidationError):
            self.env['appointment.appointment'].create({
                'appointment_type_id': appt_type_strict.id,
                'partner_id': self.partner.id,
                'start_datetime': too_soon,
                'end_datetime': too_soon + timedelta(hours=1),
            })

     
    # _check_required_assignments constraint
    def test_check_required_staff_missing_raises(self):
        appt_type_req = self.env['appointment.type'].create({
            'name': 'Staff Required',
            'duration': 1.0,
            'min_booking_notice': 0.0,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': True,
            'require_resource': False,
        })
        with self.assertRaises(ValidationError):
            self.env['appointment.appointment'].create({
                'appointment_type_id': appt_type_req.id,
                'partner_id': self.partner.id,
                'start_datetime': self.future_start,
                'end_datetime': self.future_end,
            })

     
    # State machine actions
    def test_action_confirm(self):
        appt = self._create_appt(state='draft')
        appt.action_confirm()
        self.assertEqual(appt.state, 'confirmed')

    def test_action_start(self):
        appt = self._create_appt(state='confirmed')
        appt.action_start()
        self.assertEqual(appt.state, 'in_progress')

    def test_action_done(self):
        appt = self._create_appt(state='in_progress')
        appt.action_done()
        self.assertEqual(appt.state, 'done')

    def test_action_no_show_future_raises(self):
        appt = self._create_appt(state='confirmed')
        with self.assertRaises(UserError):
            appt.action_no_show()

    def test_action_no_show_past_succeeds(self):
        past_start = fields.Datetime.now() - timedelta(hours=2)
        past_end = past_start + timedelta(hours=1)
        appt = self._create_appt(start=past_start, end=past_end, state='confirmed')
        appt.action_no_show()
        self.assertEqual(appt.state, 'no_show')

    def test_action_cancel_returns_wizard(self):
        appt = self._create_appt(state='confirmed')
        action = appt.action_cancel()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.cancel.wizard')

    def test_action_reschedule_returns_wizard(self):
        appt = self._create_appt(state='confirmed')
        action = appt.action_reschedule()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'appointment.reschedule.wizard')

    def test_action_reschedule_not_allowed_raises(self):
        appt_type_no_reschedule = self.env['appointment.type'].create({
            'name': 'No Reschedule',
            'duration': 1.0,
            'min_booking_notice': 0.0,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': False,
            'allow_reschedule': False,
        })
        appt = self.env['appointment.appointment'].create({
            'appointment_type_id': appt_type_no_reschedule.id,
            'partner_id': self.partner.id,
            'start_datetime': self.future_start,
            'end_datetime': self.future_end,
            'state': 'confirmed',
        })
        with self.assertRaises(UserError):
            appt.action_reschedule()

    def test_action_reschedule_past_deadline_raises(self):
        """Rescheduling past the deadline window should raise UserError.

        Appointment is 5 days away (120h). Setting reschedule_deadline_hours=200
        means the cutoff was at start - 200h = -80h (already in the past),
        so any reschedule attempt should be blocked.
        """
        appt_type_strict_reschedule = self.env['appointment.type'].create({
            'name': 'Strict Reschedule',
            'duration': 1.0,
            'min_booking_notice': 0.0,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': False,
            'allow_reschedule': True,
            'reschedule_deadline_hours': 200.0,  # 200h > 120h remaining → deadline expired
        })
        # Appointment starts in 5 days (120h); deadline = 120h - 200h = -80h (past)
        appt = self.env['appointment.appointment'].create({
            'appointment_type_id': appt_type_strict_reschedule.id,
            'partner_id': self.partner.id,
            'start_datetime': fields.Datetime.now() + timedelta(days=5),
            'end_datetime': fields.Datetime.now() + timedelta(days=5, hours=1),
            'state': 'confirmed',
        })
        with self.assertRaises(UserError):
            appt.action_reschedule()

     
    # _create_sale_order
    def test_create_sale_order_for_paid_type(self):
        product = self.env['product.product'].create({
            'name': 'Appointment Service',
            'type': 'service',
            'list_price': 100.0,
        })
        paid_type = self.env['appointment.type'].create({
            'name': 'Paid Type',
            'duration': 1.0,
            'min_booking_notice': 0.0,
            'is_paid': True,
            'product_id': product.id,
            'refund_policy': 'none',
            'require_staff': False,
        })
        appt = self.env['appointment.appointment'].create({
            'appointment_type_id': paid_type.id,
            'partner_id': self.partner.id,
            'start_datetime': self.future_start,
            'end_datetime': self.future_end,
        })
        self.assertTrue(appt.sale_order_id, "A sale order should be auto-created for paid appointments.")
        self.assertEqual(appt.sale_order_id.partner_id, self.partner)

    def test_create_sale_order_skipped_for_free_type(self):
        appt = self._create_appt()
        self.assertFalse(appt.sale_order_id)

     
    # _create_calendar_event
    def test_create_calendar_event(self):
        appt = self._create_appt(state='confirmed')
        # action_confirm triggers _create_calendar_event
        appt2 = self._create_appt(
            start=self.future_start + timedelta(days=10),
            end=self.future_end + timedelta(days=10),
        )
        appt2.action_confirm()
        self.assertTrue(appt2.calendar_event_id)

    def test_create_calendar_event_not_duplicated(self):
        appt = self._create_appt(
            start=self.future_start + timedelta(days=11),
            end=self.future_end + timedelta(days=11),
        )
        appt.action_confirm()
        existing_event = appt.calendar_event_id
        appt._create_calendar_event()
        # Second call should not create a new event
        self.assertEqual(appt.calendar_event_id, existing_event)

     
    # _get_paid_invoice
    def test_get_paid_invoice_no_sale_order(self):
        appt = self._create_appt()
        invoice = appt._get_paid_invoice()
        self.assertFalse(invoice)

     
    # write – calendar event sync
    def test_write_updates_calendar_event(self):
        appt = self._create_appt(
            start=self.future_start + timedelta(days=12),
            end=self.future_end + timedelta(days=12),
        )
        appt.action_confirm()
        new_start = self.future_start + timedelta(days=13)
        new_end = new_start + timedelta(hours=1)
        appt.write({'start_datetime': new_start, 'end_datetime': new_end})
        if appt.calendar_event_id:
            self.assertEqual(appt.calendar_event_id.start, new_start)

    def test_write_cancel_unlinks_calendar_event(self):
        appt = self._create_appt(
            start=self.future_start + timedelta(days=14),
            end=self.future_end + timedelta(days=14),
        )
        appt.action_confirm()
        cal_event_id = appt.calendar_event_id.id if appt.calendar_event_id else None
        appt.write({'state': 'cancelled'})
        if cal_event_id:
            cal_event = self.env['calendar.event'].browse(cal_event_id).exists()
            self.assertFalse(cal_event)

     
    # action_view_refund_credit_note
    def test_action_view_refund_credit_note(self):
        appt = self._create_appt()
        action = appt.action_view_refund_credit_note()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'account.move')

     
    # _tz_get
    def test_tz_get_returns_timezones(self):
        tz_list = self.env['appointment.appointment']._tz_get()
        self.assertIsInstance(tz_list, list)
        self.assertTrue(len(tz_list) > 100)
        # Each entry must be a 2-tuple
        self.assertEqual(len(tz_list[0]), 2)

     
    # _check_slot_capacity
    def test_check_slot_capacity_exceeded(self):
        """Booking more attendees than a slot allows should raise ValidationError."""
        slot_type = self.env['appointment.type'].create({
            'name': 'Capped Type',
            'duration': 1.0,
            'min_booking_notice': 0.0,
            'scheduling_type': 'predefined',
            'max_attendees': 1,
            'is_paid': False,
            'refund_policy': 'none',
            'require_staff': False,
        })
        start = self.future_start + timedelta(days=20)
        slot = self.env['appointment.slot'].create({
            'name': 'Capped Slot',
            'appointment_type_id': slot_type.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
        })
        partner2 = self.env['res.partner'].create({'name': 'Second Customer'})
        # Book first attendee
        self.env['appointment.appointment'].create({
            'appointment_type_id': slot_type.id,
            'partner_id': self.partner.id,
            'slot_id': slot.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
            'state': 'confirmed',
            'attendee_count': 1,
        })
        # Booking a second attendee should fail
        with self.assertRaises(ValidationError):
            self.env['appointment.appointment'].create({
                'appointment_type_id': slot_type.id,
                'partner_id': partner2.id,
                'slot_id': slot.id,
                'start_datetime': start,
                'end_datetime': start + timedelta(hours=1),
                'state': 'confirmed',
                'attendee_count': 1,
            })
