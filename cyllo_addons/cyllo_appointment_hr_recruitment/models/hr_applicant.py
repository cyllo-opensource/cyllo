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
import uuid

from odoo import api, fields, models
from odoo.http import request


class HrApplicant(models.Model):
    """Extends hr.applicant to support interview scheduling via Cyllo Appointment.

    Each applicant receives a unique, URL-safe ``interview_invite_code`` that
    is appended as a query parameter when an interviewer shares a booking link.
    When the candidate books the appointment the controller looks up this code
    and links the new ``appointment.appointment`` record back to the applicant.
    """

    _inherit = 'hr.applicant'

    interview_invite_code = fields.Char(
        string='Interview Invite Code',
        readonly=True,
        copy=False,
        store=True,
        precompute=True,
        compute='_compute_interview_invite_code',
        help='Unique token appended to the Cyllo Appointment booking URL so '
             'that the booked appointment is automatically linked to this '
             'applicant.',
    )

    appointment_ids = fields.One2many(
        comodel_name='appointment.appointment',
        inverse_name='applicant_id',
        string='Appointments',
        help='All Cyllo Appointment records linked to this applicant.',
    )

    appointment_count = fields.Integer(
        string='Appointment Count',
        compute='_compute_appointment_count',
    )

    @api.depends('interview_invite_code')
    def _compute_interview_invite_code(self):
        """Generate a 16-character hex token for each applicant that does not
        yet have one.  The token is intentionally short (128-bit UUID prefix)
        and stored permanently so it can be embedded in sent emails without
        becoming invalid on later saves."""
        for applicant in self.filtered(lambda a: not a.interview_invite_code):
            applicant.interview_invite_code = uuid.uuid4().hex[:16]

    def _compute_appointment_count(self):
        for applicant in self:
            applicant.appointment_count = len(applicant.appointment_ids)

    def action_view_appointments(self):
        """Smart-button action: open all linked appointments."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form',
            'domain': [('applicant_id', '=', self.id)],
            'context': {'default_applicant_id': self.id},
        }

    def _get_interview_invite_url(self):
        """Return the public booking URL pre-filled with *applicant_code*.
        The URL pattern mirrors the Cyllo Appointment website controller:
        ``/appointment/<appointment_type_id>/submit?applicant_code=<token>``
        """
        self.ensure_one()
        if not request:
            return ''

        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', default=''
        )
        ApptType = self.env['appointment.type'].sudo()
        appointment_type = self.env.ref(
            'cyllo_appointment_hr_recruitment.appointment_type_interviews',
            raise_if_not_found=False,
        )
        if not appointment_type:
            appointment_type = ApptType.search(
                [('category', '=', 'interview')], limit=1
            )
        if not appointment_type:
            appointment_type = ApptType.search([], limit=1)
        if appointment_type:
            path = (
                f'/appointment/{appointment_type.id}'
                f'?applicant_code={self.interview_invite_code}'
            )
        else:
            path = f'/appointment?applicant_code={self.interview_invite_code}'

        return base_url + path
