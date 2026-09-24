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


class Appointment(models.Model):
    """Extends appointment.appointment to store the linked HR applicant.

    When a candidate books an interview via the personalised URL
    (containing ``applicant_code``), the website controller resolves the
    code to an ``hr.applicant`` record and writes it here so that
    interviewers can navigate directly from the appointment to the
    applicant form.
    """

    _inherit = 'appointment.appointment'

    applicant_id = fields.Many2one(
        comodel_name='hr.applicant',
        string='Applicant',
        ondelete='set null',
        index=True,
        tracking=True,
        help='HR applicant whose interview this appointment belongs to.',
    )

    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='Applied Job',
        related='applicant_id.job_id',
        store=True,
        readonly=True,
        help='Job position derived from the linked applicant.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('applicant_id') and not vals.get('staff_id'):
                applicant = self.env['hr.applicant'].browse(vals['applicant_id'])
                if applicant.user_id:
                    employee = self.env['hr.employee'].search([('user_id', '=', applicant.user_id.id)], limit=1)
                    if employee:
                        vals['staff_id'] = employee.id
        return super().create(vals_list)

    def write(self, vals):
        if 'applicant_id' in vals and vals.get('applicant_id') and 'staff_id' not in vals:
            applicant = self.env['hr.applicant'].browse(vals['applicant_id'])
            if applicant.user_id:
                employee = self.env['hr.employee'].search([('user_id', '=', applicant.user_id.id)], limit=1)
                if employee:
                    vals['staff_id'] = employee.id

        res = super().write(vals)

        if 'staff_id' in vals or 'applicant_id' in vals:
            for rec in self:
                if rec.calendar_event_id and rec.staff_id and rec.staff_id.user_id:
                    partner = rec.staff_id.user_id.partner_id
                    if partner:
                        rec.calendar_event_id.write({
                            'partner_ids': [(4, partner.id)],
                            'user_id': rec.staff_id.user_id.id,
                        })
        return res

    def action_open_applicant(self):
        """Open the linked applicant form view from the appointment smart-button."""
        self.ensure_one()
        if not self.applicant_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Applicant'),
            'res_model': 'hr.applicant',
            'view_mode': 'form',
            'res_id': self.applicant_id.id,
        }
