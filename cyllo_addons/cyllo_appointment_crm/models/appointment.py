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
from markupsafe import Markup

from odoo import api, fields, models, Command, _


class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        tracking=True,
        help='CRM opportunity linked to this appointment.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._handle_crm_on_confirm()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'confirmed':
            self._handle_crm_on_confirm()
        return res

    def action_confirm(self):
        res = super().action_confirm()
        self._handle_crm_on_confirm()
        return res

    def _handle_crm_on_confirm(self):
        """For each confirmed appointment whose type has lead_create=True,
        either link to an existing active opportunity or create a new one.
        Also schedules a meeting activity on the linked opportunity and
        posts a log note on the appointment."""
        to_process = self.filtered(
            lambda a: a.state == 'confirmed'
            and a.appointment_type_id.lead_create
            and not a.opportunity_id
        )
        for appointment in to_process:
            opportunity = appointment._get_or_create_lead()
            if opportunity:
                appointment.opportunity_id = opportunity
                appointment._post_crm_link_note(opportunity)
                appointment._schedule_meeting_activity(opportunity)

    def _get_or_create_lead(self):
        """Return an existing active opportunity for the customer + staff
        combination, or create a new one.

        Priority:
        1. If the appointment already has an opportunity_id set externally,
           return it immediately.
        2. Search for an existing open (non-won) lead assigned to the same
           staff user and customer partner.
        3. Create a fresh opportunity.
        """
        self.ensure_one()
        customer = self.partner_id
        staff_user = self.staff_id.user_id if self.staff_id else False
        if staff_user and customer == staff_user.partner_id:
            return self.env['crm.lead']
        # 1. Try to reuse an existing active lead
        if staff_user:
            existing = self.env['crm.lead'].sudo().search([
                ('user_id', '=', staff_user.id),
                ('stage_id.is_won', '=', False),
                ('partner_id', '=', customer.id),
                ('type', '=', 'opportunity'),
            ], order='id desc', limit=1)
            if existing:
                return existing
        # 2. Create a new opportunity
        lead_vals = self._get_lead_values()
        lead = self.env['crm.lead'].with_context(
            mail_create_nosubscribe=True
        ).with_company(
            self.company_id or self.env.company
        ).create(lead_vals)
        return lead

    def _get_lead_values(self):
        """Return the dict used to create a new CRM opportunity from this
        appointment."""
        self.ensure_one()
        staff_user = self.staff_id.user_id if self.staff_id else self.env.user
        return {
            'name': self.meeting_subject or self.display_name or self.name,
            'partner_id': self.partner_id.id,
            'type': 'opportunity',
            'user_id': staff_user.id,
            'description': self.customer_notes or '',
            'company_id': (self.company_id or self.env.company).id,
        }

    def _post_crm_link_note(self, opportunity):
        """Log a note on the appointment indicating the linked opportunity."""
        self.ensure_one()
        opportunity_field = self.env['ir.model.fields']._get(
            'appointment.appointment', 'opportunity_id'
        )
        self._message_log(
            body=Markup('<p>%s</p>') % _(
                'Appointment linked to Opportunity %s',
                opportunity._get_html_link()
            ),
            tracking_value_ids=[Command.create({
                'field_id': opportunity_field.id,
                'old_value_char': False,
                'new_value_char': opportunity.name,
            })],
        )

    def _schedule_meeting_activity(self, opportunity):
        """Schedule a 'Meeting' activity on the CRM opportunity so the
        salesperson is reminded of the upcoming appointment."""
        self.ensure_one()
        if self.calendar_event_id:
            pass
        staff_user = self.staff_id.user_id if self.staff_id else self.env.user
        deadline = self.start_datetime.date() if self.start_datetime else fields.Date.today()
        opportunity.sudo().activity_schedule(
            act_type_xmlid='mail.mail_activity_data_meeting',
            date_deadline=deadline,
            summary=self.meeting_subject or self.display_name or self.name,
            user_id=staff_user.id,
        )

    def action_view_opportunity(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Opportunity'),
            'res_model': 'crm.lead',
            'res_id': self.opportunity_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
