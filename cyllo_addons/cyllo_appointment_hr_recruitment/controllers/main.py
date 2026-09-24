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
from odoo import http
from odoo.http import request
from odoo.addons.cyllo_appointment.controllers.main import AppointmentWebsiteController


class AppointmentHrRecruitmentController(AppointmentWebsiteController):
    """Extends the Cyllo Appointment website controller to support
    recruitment-driven booking.

    When a candidate follows a personalised interview URL that contains
    ``applicant_code`` as a GET or POST parameter, the newly created
    ``appointment.appointment`` record is automatically linked to the
    matching ``hr.applicant`` record via ``applicant_id``.
    """

    @http.route(
        ['/appointment/<model("appointment.type"):appointment_type>/submit'],
        type='http', auth='public', website=True, methods=['POST'], csrf=True,
    )
    def appointment_submit(self, appointment_type, **post):
        """Intercept the standard submit to inject ``applicant_id`` when an
        ``applicant_code`` token is present in the POST payload.
        """
        applicant_code = post.get('applicant_code')

        if not applicant_code:
            return super().appointment_submit(appointment_type, **post)
        existing_ids = set(
            request.env['appointment.appointment'].sudo().search([]).ids
        )
        response = super().appointment_submit(appointment_type, **post)
        new_appointments = request.env['appointment.appointment'].sudo().search([
            ('id', 'not in', list(existing_ids)),
        ])
        if new_appointments and applicant_code:
            applicant = request.env['hr.applicant'].sudo().search([
                ('interview_invite_code', '=', applicant_code),
            ], limit=1)
            if applicant:
                new_appointments.write({'applicant_id': applicant.id})

        return response

    @http.route(
        ['/appointment/<model("appointment.type"):appointment_type>'],
        type='http', auth='public', website=True,
    )
    def appointment_details(self, appointment_type, **kw):
        """Forward ``applicant_code`` from the URL into the template rendering
        context so the booking form can embed it as a hidden input field.
        Also pre-fills the applicant's name, email and phone so the candidate
        does not have to type their details again."""
        response = super().appointment_details(appointment_type, **kw)

        applicant_code = kw.get('applicant_code')
        if applicant_code and hasattr(response, 'qcontext'):
            response.qcontext['applicant_code'] = applicant_code

            applicant = request.env['hr.applicant'].sudo().search([
                ('interview_invite_code', '=', applicant_code),
            ], limit=1)
            if applicant:
                partner = applicant.partner_name or ''
                email = applicant.email_from or ''
                phone = applicant.partner_phone or applicant.partner_mobile or ''
                response.qcontext.update({
                    'prefill_name': partner,
                    'prefill_email': email,
                    'prefill_phone': phone,
                })

        return response
