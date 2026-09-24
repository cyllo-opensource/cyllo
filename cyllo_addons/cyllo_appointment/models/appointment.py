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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging
import uuid

_logger = logging.getLogger(__name__)


class Appointment(models.Model):
    _name = 'appointment.appointment'
    _description = 'Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    # Identity
    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    display_name = fields.Char(string='Title', compute='_compute_display_name',
                               store=True)
    meeting_subject = fields.Char(
        string='Meeting Subject', compute='_compute_meeting_subject',
        store=True
    )
    # Type & Classification
    appointment_type_id = fields.Many2one(
        'appointment.type', string='Appointment Type',
        required=True, tracking=True, ondelete='restrict'
    )
    category = fields.Selection(
        related='appointment_type_id.category', string='Category', store=True
    )
    scheduling_type = fields.Selection(
        related='appointment_type_id.scheduling_type', string='Scheduling Type',
        store=False
    )
    # Scheduling
    start_datetime = fields.Datetime(string='Start', tracking=True)
    end_datetime = fields.Datetime(string='End', tracking=True)
    duration = fields.Float(string='Duration (hours)',
                            compute='_compute_duration', store=True)
    slot_id = fields.Many2one('appointment.slot', string='Time Slot')
    event_id = fields.Many2one('event.event', string='Event', readonly=True)
    timezone = fields.Selection(
        '_tz_get', string='Timezone',
        default=lambda self: self.env.user.tz or 'UTC'
    )
    # Customer / Attendee
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 required=True, tracking=True)
    attendee_ids = fields.Many2many('res.partner',
                                    string='Additional Attendees')
    attendee_count = fields.Integer(string='Number of Attendees', default=1)
    customer_notes = fields.Text(string='Customer Notes')
    booker_name = fields.Char(string='Booker Name',
                              help='Name entered by the customer on the website booking form')
    # Staff & Resources
    staff_domain = fields.Char(compute='_compute_staff_resource_domain')
    resource_domain = fields.Char(compute='_compute_staff_resource_domain')
    staff_id = fields.Many2one('hr.employee', string='Staff Member',
                               tracking=True)
    resource_id = fields.Many2one('appointment.resource', string='Resource',
                                  tracking=True)
    # Location
    location_type = fields.Selection(
        related='appointment_type_id.location_type', string='Location Type',
        store=True
    )
    location = fields.Char(string='Location')
    meeting_url = fields.Char(string='Meeting URL')
    # Billing / Payment
    sale_order_id = fields.Many2one('sale.order', string='Sales Order',
                                    readonly=True)
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_payment', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('no_show', 'No Show'),
    ], string='Status', default='draft', required=True, tracking=True)
    # Rescheduling
    is_rescheduled = fields.Boolean(string='Was Rescheduled', default=False, copy=False)
    original_start_datetime = fields.Datetime(string='Original Start')
    reschedule_count = fields.Integer(string='Reschedule Count', default=0)
    reschedule_reason = fields.Text(string='Reschedule Reason')
    # Cancellation
    cancellation_reason = fields.Text(string='Cancellation Reason')
    cancelled_by = fields.Selection([
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('system', 'System'),
    ], string='Cancelled By')
    # Notifications
    confirmation_sent = fields.Boolean(string='Confirmation Sent',
                                       default=False)
    reminder_sent = fields.Boolean(string='Reminders Sent', default=False)
    sent_reminder_hours = fields.Char(string='Sent Reminder Hours', default='')
    followup_sent = fields.Boolean(string='Follow-up Sent', default=False)
    cancellation_sent = fields.Boolean(string='Cancellation Sent',
                                       default=False)
    whatsapp_confirmation_sent = fields.Boolean(
        string='WhatsApp Confirmation Sent', default=False)
    whatsapp_reminder_sent = fields.Boolean(string='WhatsApp Reminders Sent',
                                            default=False)
    whatsapp_followup_sent = fields.Boolean(string='WhatsApp Follow-up Sent',
                                            default=False)
    whatsapp_cancellation_sent = fields.Boolean(
        string='WhatsApp Cancellation Sent', default=False)
    # Secure website management token
    access_token = fields.Char(
        string='Access Token', copy=False, readonly=True, index=True,
        default=lambda self: str(uuid.uuid4())
    )
    # Internal
    internal_notes = fields.Html(string='Internal Notes')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Very Important'),
    ], string='Priority', default='0')
    color = fields.Integer(string='Color', compute='_compute_color')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event')
    refund_credit_note_id = fields.Many2one(
        'account.move', string='Refund Credit Note',
        readonly=True, copy=False,
        domain=[('move_type', '=', 'out_refund')]
    )
    refund_status = fields.Selection([
        ('pending', 'Pending'),
        ('issued', 'Issued'),
        ('reconciled', 'Reconciled'),
        ('none', 'No Refund'),
    ], string='Refund Status', readonly=True, copy=False)
    confirmation_template_id = fields.Many2one(
        'mail.template', string='Confirmation Email Template (used)',
        readonly=True, copy=False,
        domain=[('model', '=', 'appointment.appointment')]
    )
    reminder_template_id = fields.Many2one(
        'mail.template', string='Reminder Email Template (used)',
        readonly=True, copy=False,
        domain=[('model', '=', 'appointment.appointment')]
    )
    followup_template_id = fields.Many2one(
        'mail.template', string='Follow-up Email Template (used)',
        readonly=True, copy=False,
        domain=[('model', '=', 'appointment.appointment')]
    )
    cancellation_template_id = fields.Many2one(
        'mail.template', string='Cancellation Email Template (used)',
        readonly=True, copy=False,
        domain=[('model', '=', 'appointment.appointment')]
    )

    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in sorted(
            __import__('pytz').all_timezones,
            key=lambda tz: tz if not tz.startswith('Etc/') else '_'
        )]

    @api.depends('appointment_type_id', 'partner_id', 'start_datetime')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.appointment_type_id:
                parts.append(rec.appointment_type_id.name)
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            rec.display_name = ' - '.join(parts) if parts else _('Appointment')

    @api.depends('partner_id.name', 'appointment_type_id.name', 'booker_name')
    def _compute_meeting_subject(self):
        for rec in self:
            customer = rec.booker_name or rec.partner_id.name or ''
            atype = rec.appointment_type_id.name or ''
            if customer and atype:
                rec.meeting_subject = '%s - %s' % (customer, atype)
            else:
                rec.meeting_subject = customer or atype or ''

    @api.depends('company_id', 'appointment_type_id.staff_ids',
                 'appointment_type_id.resource_ids')
    def _compute_staff_resource_domain(self):
        for rec in self:
            company_id = rec.company_id.id or rec.env.company.id
            if rec.appointment_type_id and rec.appointment_type_id.staff_ids:
                rec.staff_domain = f"[('appointment_type_ids', 'in', {rec.appointment_type_id.id}), ('company_id', '=', {company_id})]"
            else:
                rec.staff_domain = f"[('company_id', '=', {company_id})]"

            if rec.appointment_type_id and rec.appointment_type_id.resource_ids:
                rec.resource_domain = f"[('appointment_type_ids', 'in', {rec.appointment_type_id.id}), ('company_id', '=', {company_id})]"
            else:
                rec.resource_domain = f"[('company_id', '=', {company_id})]"

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0.0

    @api.depends('state')
    def _compute_color(self):
        color_map = {
            'draft': 0,
            'confirmed': 1,
            'in_progress': 2,
            'done': 10,
            'cancelled': 9,
            'rejected': 9,
            'no_show': 6,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'appointment.appointment') or _('New')
        records = super().create(vals_list)
        #Creating calendar event
        for record in records:
            if record.event_id:
                self.env['event.registration'].create({
                    'event_id': record.event_id.id,
                    'partner_id': record.partner_id.id,
                })
            if record.appointment_type_id.is_paid and not record.sale_order_id:
                record._create_sale_order()
        for record in records:
            if record.state == 'confirmed':
                record._create_calendar_event()
                if record.appointment_type_id.send_confirmation:
                    record._send_confirmation_email()
                if record.appointment_type_id.send_whatsapp_confirmation and not record.whatsapp_confirmation_sent:
                    record._send_whatsapp_confirmation()
                record._send_staff_confirmation_email()
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.calendar_event_id:
                rec.calendar_event_id.write({
                    'name': rec.display_name,
                    'start': rec.start_datetime,
                    'stop': rec.end_datetime,
                })
        if 'state' in vals and vals['state'] == 'cancelled':
            for record in self:
                if record.calendar_event_id:
                    record.calendar_event_id.unlink()
                if record.appointment_type_id.send_cancellation and not record.cancellation_sent:
                    record._send_cancellation_email()
                if record.appointment_type_id.send_whatsapp_cancellation and not record.whatsapp_cancellation_sent:
                    record._send_whatsapp_cancellation()
                if record.appointment_type_id.is_paid:
                    record._process_cancellation_refund()
        return res

    def copy(self, default=None):
        raise UserError(_("Duplicating records is not allowed."))

    @api.onchange('appointment_type_id')
    def _onchange_appointment_type_id(self):
        if self.appointment_type_id:
            atype = self.appointment_type_id
            if self.start_datetime and not self.end_datetime:
                self.end_datetime = self.start_datetime + timedelta(
                    hours=atype.duration)
            if atype.location:
                self.location = atype.location
            self.confirmation_template_id = atype.confirmation_template_id
            self.reminder_template_id = atype.reminder_template_id
            self.followup_template_id = atype.followup_template_id
            self.cancellation_template_id = atype.cancellation_template_id
        else:
            self.confirmation_template_id = False
            self.reminder_template_id = False
            self.followup_template_id = False
            self.cancellation_template_id = False

    @api.onchange('slot_id')
    def _onchange_slot_id(self):
        if self.slot_id:
            slot = self.slot_id
            self.appointment_type_id = slot.appointment_type_id
            self.start_datetime = slot.start_datetime
            self.end_datetime = slot.end_datetime
            if slot.staff_id:
                self.staff_id = slot.staff_id
            if slot.resource_id:
                self.resource_id = slot.resource_id
            if slot.event_id:
                self.event_id = slot.event_id

    @api.onchange('start_datetime', 'appointment_type_id')
    def _onchange_start_datetime(self):
        if self.start_datetime and self.appointment_type_id:
            self.end_datetime = self.start_datetime + timedelta(
                hours=self.appointment_type_id.duration
            )

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                if rec.end_datetime <= rec.start_datetime:
                    raise ValidationError(
                        _('End time must be after start time.'))

    @api.constrains('start_datetime', 'end_datetime', 'slot_id',
                    'appointment_type_id')
    def _check_predefined_slot_times(self):
        for rec in self:
            if rec.appointment_type_id.scheduling_type == 'predefined' and rec.slot_id:
                if rec.start_datetime and rec.start_datetime != rec.slot_id.start_datetime:
                    raise ValidationError(_(
                        'Start time must match the selected slot (%s).'
                    ) % rec.slot_id.display_name)
                if rec.end_datetime and rec.end_datetime != rec.slot_id.end_datetime:
                    raise ValidationError(_(
                        'End time must match the selected slot (%s).'
                    ) % rec.slot_id.display_name)

    @api.constrains('start_datetime', 'end_datetime', 'staff_id', 'resource_id',
                    'state', 'slot_id')
    def _check_overlap(self):
        for rec in self:
            if rec.state in ('cancelled', 'rejected'):
                continue
            if not rec.start_datetime or not rec.end_datetime:
                continue
            search_start = rec.start_datetime - timedelta(days=1)
            search_end = rec.end_datetime + timedelta(days=1)
            appt_domain = [
                ('id', '!=', rec.id),
                ('state', 'not in', ('draft','cancelled', 'rejected')),
                ('start_datetime', '<', search_end),
                ('end_datetime', '>', search_start),
            ]
            # Check overlap with defined time slots
            slot_domain = [
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime),
            ]
            if rec.slot_id:
                slot_domain.append(('id', '!=', rec.slot_id.id))
            if rec.staff_id:
                # 1. Overlap with other appointments
                staff_appts = self.search(
                    appt_domain + [('staff_id', '=', rec.staff_id.id)])
                if rec.slot_id:
                    staff_appts = staff_appts.filtered(
                        lambda a: a.slot_id != rec.slot_id)
                for appt in staff_appts:
                    if appt.start_datetime < rec.end_datetime and appt.end_datetime > rec.start_datetime:
                        raise ValidationError(
                            _('Staff member "%s" is already booked by another appointment during this time.') % rec.staff_id.name)
                # 2. Overlap with predefined slots
                staff_slots = self.env['appointment.slot'].search(
                    slot_domain + [('staff_id', '=', rec.staff_id.id)], limit=1)
                if staff_slots:
                    raise ValidationError(
                        _('Staff member "%s" is already scheduled for a "%s" slot during this time.') % (
                            rec.staff_id.name,
                            staff_slots.appointment_type_id.name))
            if rec.resource_id:
                # 1. Overlap with other appointments
                res_appts = self.search(
                    appt_domain + [('resource_id', '=', rec.resource_id.id)])
                if rec.slot_id:
                    res_appts = res_appts.filtered(
                        lambda a: a.slot_id != rec.slot_id)
                for appt in res_appts:
                    if appt.start_datetime < rec.end_datetime and appt.end_datetime > rec.start_datetime:
                        raise ValidationError(
                            _('Resource "%s" is already booked by another appointment during this time.') % rec.resource_id.name)
                # 2. Overlap with predefined slots
                res_slots = self.env['appointment.slot'].search(
                    slot_domain + [('resource_id', '=', rec.resource_id.id)],
                    limit=1)
                if res_slots:
                    raise ValidationError(
                        _('Resource "%s" is already scheduled for a "%s" slot during this time.') % (
                            rec.resource_id.name,
                            res_slots.appointment_type_id.name))

    @api.constrains('slot_id', 'attendee_count', 'state')
    def _check_slot_capacity(self):
        for rec in self:
            if rec.slot_id and rec.state not in ('cancelled', 'rejected'):
                active_appts = rec.slot_id.appointment_ids.filtered(
                    lambda a: a.state not in ('cancelled', 'rejected')
                )
                total_attendees = sum(active_appts.mapped('attendee_count'))
                if total_attendees > rec.slot_id.max_attendees:
                    # Calculate spots before this appointment to show accurate error
                    spots_before_this = rec.slot_id.max_attendees - (
                            total_attendees - rec.attendee_count)
                    raise ValidationError(_(
                        'The selected slot "%s" does not have enough capacity for %s attendee(s). Only %s spot(s) remaining.'
                    ) % (rec.slot_id.name, rec.attendee_count,
                         max(0, spots_before_this)))

    @api.constrains('start_datetime', 'appointment_type_id')
    def _check_min_booking_notice(self):
        for rec in self:
            if rec.appointment_type_id and rec.start_datetime:
                min_notice = rec.appointment_type_id.min_booking_notice
                if min_notice > 0:
                    min_start = fields.Datetime.now() + timedelta(
                        hours=min_notice)
                    if rec.start_datetime < min_start:
                        raise ValidationError(_(
                            'This appointment type requires at least %s hour(s) advance notice.'
                        ) % min_notice)

    @api.constrains('start_datetime', 'appointment_type_id')
    def _check_max_booking_horizon(self):
        for rec in self:
            if rec.appointment_type_id and rec.start_datetime:
                max_days = rec.appointment_type_id.max_booking_days
                if max_days > 0:
                    max_date = fields.Datetime.now() + timedelta(days=max_days)
                    if rec.start_datetime > max_date:
                        raise ValidationError(_(
                            'You cannot book this appointment more than %s days in advance.'
                        ) % max_days)

    @api.constrains('appointment_type_id', 'staff_id', 'resource_id', 'state')
    def _check_required_assignments(self):
        for rec in self:
            if rec.state in ('cancelled', 'rejected'):
                continue
            if rec.appointment_type_id.require_staff and not rec.staff_id:
                raise ValidationError(
                    _('A staff member must be assigned for this appointment type.'))
            if rec.appointment_type_id.require_resource and not rec.resource_id:
                raise ValidationError(
                    _('A resource must be assigned for this appointment type.'))

    def _process_cancellation_refund(self):
        self.ensure_one()
        appt_type = self.appointment_type_id
        if appt_type.refund_policy == 'none':
            return
        refund_pct = appt_type.get_refund_percentage(
            cancellation_datetime=fields.Datetime.now(),
            appointment_start=self.start_datetime,
        )
        if refund_pct <= 0:
            self._message_log(body=_(
                'Cancellation refund: No refund applicable based on policy and cancellation time.'))
            return
        invoice = self._get_paid_invoice()
        if not invoice:
            _logger.warning(
                'Appointment %s: no paid invoice found, skipping refund.',
                self.name)
            return
        credit_note = self._create_credit_note(invoice, refund_pct)
        self.write({
            'refund_credit_note_id': credit_note.id,
            'refund_status': 'reconciled' if appt_type.refund_policy in ('full',
                                                                         'partial') else 'issued',
        })
        if appt_type.refund_policy in ('full', 'partial'):
            self._reconcile_credit_note(credit_note, invoice)
        # 'credit' policy: left unreconciled
        self._message_log(
            body=_('Credit note %s created for %.0f%% refund (policy: %s).')
                 % (credit_note.name, refund_pct, appt_type.refund_policy)
        )

    def _get_paid_invoice(self):
        self.ensure_one()
        if not self.sale_order_id:
            return self.env['account.move'].browse()
        return self.sale_order_id.invoice_ids.filtered(
            lambda inv: inv.move_type == 'out_invoice'
                        and inv.payment_state in ('paid', 'in_payment',
                                                  'partial')
        )[:1]

    def _create_credit_note(self, invoice, refund_pct):
        self.ensure_one()
        move_reversal = self.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'reason': _('Cancellation of %s (%.0f%% refund)') % (self.name,
                                                                 refund_pct),
            'journal_id': invoice.journal_id.id,
            'date': fields.Date.today(),
        })
        result = move_reversal.reverse_moves()
        credit_note = self.env['account.move'].browse(result['res_id'])
        if refund_pct < 100.0:
            if credit_note.state != 'draft':
                credit_note.button_draft()
            for line in credit_note.invoice_line_ids:
                line.price_unit = line.price_unit * (refund_pct / 100.0)
        credit_note.action_post()
        return credit_note

    def _reconcile_credit_note(self, credit_note, invoice):
        """Auto-generate an outbound refund payment to reconcile the credit note."""
        self.ensure_one()
        if credit_note.state != 'posted':
            return
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=credit_note.ids,
        ).create({})
        payment_register._create_payments()

    def _create_calendar_event(self):
        """Create a calendar event linked to this appointment."""
        self.ensure_one()
        if self.calendar_event_id:
            return
        partner_ids = [(4, self.partner_id.id)]
        if self.staff_id and self.staff_id.user_id and self.staff_id.user_id.partner_id:
            partner_ids.append((4, self.staff_id.user_id.partner_id.id))
        event = self.env['calendar.event'].create({
            'name': self.display_name or self.name,
            'start': self.start_datetime,
            'stop': self.end_datetime,
            'partner_ids': partner_ids,
            'description': self.customer_notes or '',
            'user_id': self.staff_id.user_id.id if self.staff_id and self.staff_id.user_id else self.env.user.id,
        })
        self.calendar_event_id = event.id

    def _create_sale_order(self):
        self.ensure_one()
        appt_type = self.appointment_type_id
        if not appt_type.is_paid or not appt_type.product_id:
            return False

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'origin': self.name,
            'note': _('Sale order generated from appointment %s') % self.name,
            'order_line': [(0, 0, {
                'product_id': appt_type.product_id.id,
                'name': appt_type.product_id.name,
                'product_uom_qty': 1,
                'price_unit': appt_type.product_id.lst_price,
            })],
        })
        self.sale_order_id = sale_order.id
        return sale_order

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            if not rec.calendar_event_id:
                rec._create_calendar_event()
            if rec.appointment_type_id.send_confirmation and not rec.confirmation_sent:
                rec._send_confirmation_email()
            if rec.appointment_type_id.send_whatsapp_confirmation and not rec.whatsapp_confirmation_sent:
                rec._send_whatsapp_confirmation()
            rec._send_staff_confirmation_email()

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            if rec.appointment_type_id.send_followup and not rec.followup_sent:
                rec._send_followup_email()
            if rec.appointment_type_id.send_whatsapp_followup and not rec.whatsapp_followup_sent:
                rec._send_whatsapp_followup()

    def action_cancel(self):
        atype = self.appointment_type_id
        if atype.cancel_policy=='never':
            raise UserError(
                _('Cancellation is not allowed for this appointment type.'))
        else:
            if atype.cancel_policy=='up_to':
                cancel_deadline_hours = atype.cancel_deadline_hours
                if cancel_deadline_hours > 0:
                    cancel_deadline = self.start_datetime - timedelta(hours=cancel_deadline_hours)
                    if fields.Datetime.now() > cancel_deadline:
                        raise UserError(_(
                            'Cancellation is no longer allowed within %s hours of the appointment.'
                        ) % cancel_deadline_hours)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Appointment'),
            'res_model': 'appointment.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    def action_reschedule(self):
        self.ensure_one()
        atype = self.appointment_type_id
        if not atype.allow_reschedule:
            raise UserError(
                _('Rescheduling is not allowed for this appointment type.'))
        deadline_hours = atype.reschedule_deadline_hours
        if deadline_hours > 0:
            deadline = self.start_datetime - timedelta(hours=deadline_hours)
            if fields.Datetime.now() > deadline:
                raise UserError(_(
                    'Rescheduling is no longer allowed within %s hours of the appointment.'
                ) % deadline_hours)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Appointment'),
            'res_model': 'appointment.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    def action_no_show(self):
        for rec in self:
            rec.write({'state' : 'no_show'})

    def _send_confirmation_email(self):
        self.ensure_one()
        template = (self.confirmation_template_id
                    or self.appointment_type_id.confirmation_template_id)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.confirmation_sent = True
                _logger.info('Confirmation email sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning('Failed to send confirmation email for %s: %s',
                                self.name, str(e))

    def _send_staff_confirmation_email(self):
        self.ensure_one()
        if self.staff_id and self.staff_id.notify_on_new_appointment and self.staff_id.work_email:
            staff_tmpl = self.env.ref(
                'cyllo_appointment.email_template_appointment_confirmed_staff',
                raise_if_not_found=False)
            if staff_tmpl:
                try:
                    staff_tmpl.send_mail(self.id, force_send=True)
                except Exception as e:
                    _logger.warning(
                        "Failed to send staff confirmation email for %s: %s",
                        self.name, str(e))

    def _send_reminder_emails(self):
        """Called by scheduled action to send reminders."""
        now = fields.Datetime.now()
        appointments = self.search([
            ('state', 'in', ['confirmed']),
            ('start_datetime', '>=', now - timedelta(minutes=30)),
        ])
        for appt in appointments:
            atype = appt.appointment_type_id
            reminder_template = appt.reminder_template_id or atype.reminder_template_id
            if not atype.send_reminder or not reminder_template:
                continue
            reminder_times_str = atype.reminder_hours_before or '24'
            reminder_hours = [float(h.strip()) for h in
                              reminder_times_str.split(',') if h.strip()]
            sent_hours_str = appt.sent_reminder_hours or ''
            sent_hours = [float(h.strip()) for h in sent_hours_str.split(',') if
                          h.strip()]
            for hours in reminder_hours:
                if hours in sent_hours:
                    continue
                reminder_time = appt.start_datetime - timedelta(hours=hours)
                if reminder_time <= now < reminder_time + timedelta(minutes=30):
                    try:
                        reminder_template.send_mail(appt.id,
                                                     force_send=True)
                        appt.reminder_sent = True
                        sent_hours.append(hours)
                        appt.sent_reminder_hours = ','.join(
                            map(str, sent_hours))
                        if atype.send_sms_reminder and atype.sms_reminder_template_id:
                            appt._send_sms_reminder()
                        if atype.send_whatsapp_reminder and atype.whatsapp_reminder_template_id and not appt.whatsapp_reminder_sent:
                            appt._send_whatsapp_reminder()
                        break
                    except Exception as e:
                        _logger.warning('Failed to send reminder for %s: %s',
                                        appt.name, str(e))

    def _send_sms_reminder(self):
        self.ensure_one()
        if not self.partner_id.mobile and not self.partner_id.phone:
            return
        template = self.appointment_type_id.sms_reminder_template_id
        if template:
            try:
                template.send_sms(self.id)
            except Exception as e:
                _logger.warning('Failed to send SMS for %s: %s', self.name,
                                str(e))

    def _send_followup_email(self):
        self.ensure_one()
        template = (self.followup_template_id
                    or self.appointment_type_id.followup_template_id)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.followup_sent = True
            except Exception as e:
                _logger.warning('Failed to send follow-up for %s: %s',
                                self.name, str(e))

    def _send_cancellation_email(self):
        self.ensure_one()
        template = (self.cancellation_template_id
                    or self.appointment_type_id.cancellation_template_id)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.cancellation_sent = True
                _logger.info('Cancellation email sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning('Failed to send cancellation email for %s: %s',
                                self.name, str(e))

    def _send_whatsapp_confirmation(self):
        self.ensure_one()
        if not self.partner_id.whatsapp_number and not self.partner_id.mobile and not self.partner_id.phone:
            return
        template = self.appointment_type_id.whatsapp_confirmation_template_id
        if template:
            try:
                template.action_send_template(self, attachment=False,
                                              partner=self.partner_id)
                self.whatsapp_confirmation_sent = True
                _logger.info('WhatsApp confirmation sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning(
                    'Failed to send WhatsApp confirmation for %s: %s',
                    self.name, str(e))

    def _send_whatsapp_reminder(self):
        self.ensure_one()
        if not self.partner_id.whatsapp_number and not self.partner_id.mobile and not self.partner_id.phone:
            return
        template = self.appointment_type_id.whatsapp_reminder_template_id
        if template:
            try:
                template.action_send_template(self, attachment=False,
                                              partner=self.partner_id)
                self.whatsapp_reminder_sent = True
                _logger.info('WhatsApp reminder sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning('Failed to send WhatsApp reminder for %s: %s',
                                self.name, str(e))

    def _send_whatsapp_followup(self):
        self.ensure_one()
        if not self.partner_id.whatsapp_number and not self.partner_id.mobile and not self.partner_id.phone:
            return
        template = self.appointment_type_id.whatsapp_followup_template_id
        if template:
            try:
                template.action_send_template(self, attachment=False,
                                              partner=self.partner_id)
                self.whatsapp_followup_sent = True
                _logger.info('WhatsApp follow-up sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning('Failed to send WhatsApp follow-up for %s: %s',
                                self.name, str(e))

    def _send_whatsapp_cancellation(self):
        self.ensure_one()
        if not self.partner_id.whatsapp_number and not self.partner_id.mobile and not self.partner_id.phone:
            return
        template = self.appointment_type_id.whatsapp_cancellation_template_id
        if template:
            try:
                template.action_send_template(self, attachment=False,
                                              partner=self.partner_id)
                self.whatsapp_cancellation_sent = True
                _logger.info('WhatsApp cancellation sent for appointment %s',
                             self.name)
            except Exception as e:
                _logger.warning(
                    'Failed to send WhatsApp cancellation for %s: %s',
                    self.name, str(e))

    def action_view_refund_credit_note(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refund Credit Note'),
            'res_model': 'account.move',
            'res_id': self.refund_credit_note_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sale_order(self):
        self.ensure_one()
        return{
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id' : self.sale_order_id.id,
            'target': 'current',
        }
