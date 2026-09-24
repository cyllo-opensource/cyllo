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
import logging

_logger = logging.getLogger(__name__)


class AppointmentCancelWizard(models.TransientModel):
    _name = 'appointment.cancel.wizard'
    _description = 'Cancel Appointment Wizard'

    appointment_id = fields.Many2one(
        'appointment.appointment', string='Appointment',
        required=True, readonly=True
    )
    cancellation_reason = fields.Text(string='Cancellation Reason',
                                      required=True)
    cancelled_by = fields.Selection([
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('system', 'System'),
    ], string='Cancelled By', default='staff', required=True)
    send_notification = fields.Boolean(string='Notify Customer', default=True)
    # Refund preview fields (all readonly/computed — no user input needed)
    is_paid_appointment = fields.Boolean(
        compute='_compute_refund_preview', string='Is Paid')
    refund_policy = fields.Selection([
        ('none', 'No Refund'),
        ('full', 'Full Refund to Original Payment Method'),
        ('partial', 'Partial Refund to Original Payment Method'),
        ('credit', 'Credit Note (Redeemable on Future Appointments Only)'),
    ], compute='_compute_refund_preview', string='Refund Policy')
    expected_refund_percentage = fields.Float(
        compute='_compute_refund_preview', string='Refund %')
    expected_refund_amount = fields.Monetary(
        compute='_compute_refund_preview', string='Estimated Refund',
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        related='appointment_id.company_id.currency_id',
        readonly=True)

    @api.depends('appointment_id')
    def _compute_refund_preview(self):
        for rec in self:
            appt = rec.appointment_id
            appt_type = appt.appointment_type_id
            rec.is_paid_appointment = appt_type.is_paid
            rec.refund_policy = appt_type.refund_policy
            if not appt_type.is_paid or appt_type.refund_policy == 'none':
                rec.expected_refund_percentage = 0.0
                rec.expected_refund_amount = 0.0
                continue
            pct = appt_type.get_refund_percentage(
                cancellation_datetime=fields.Datetime.now(),
                appointment_start=appt.start_datetime,
            )
            rec.expected_refund_percentage = pct

            invoice = appt._get_paid_invoice()
            if invoice:
                base_amount = invoice.amount_total
            elif appt_type.product_id:
                base_amount = appt_type.product_id.list_price
            else:
                base_amount = 0.0
            rec.expected_refund_amount = base_amount * pct / 100.0 if base_amount else 0.0

    def action_confirm_cancel(self):
        self.ensure_one()
        appt = self.appointment_id
        appt.write({
            'state': 'cancelled',
            'cancellation_reason': self.cancellation_reason,
            'cancelled_by': self.cancelled_by,
        })
        if self.send_notification:
            appt._message_log(
                body=_('Appointment cancelled. Reason: %s') % self.cancellation_reason)
        # Send Staff Cancellation Email
        if appt.staff_id and appt.staff_id.notify_on_cancellation and appt.staff_id.work_email:
            staff_tmpl = self.env.ref(
                'cyllo_appointment.email_template_appointment_cancelled_staff',
                raise_if_not_found=False
            )
            if staff_tmpl:
                try:
                    staff_tmpl.send_mail(appt.id, force_send=True)
                except Exception as e:
                    _logger.warning(
                        "Failed to send staff cancellation email for %s: %s",
                        appt.name, str(e)
                    )
        return {'type': 'ir.actions.act_window_close'}
