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
from odoo import api, models, _


class OnboardingOnboardingStep(models.Model):
    _inherit = "onboarding.onboarding.step"

    @api.model
    def action_open_step_helpdesk_ticket_confirmation(self):
        return self.env['ir.actions.actions']._for_xml_id(
            'cyllo_helpdesk.helpdesk_my_ticket_action'
        )

    @api.model
    def _get_sample_helpdesk_ticket(self):
        ticket = self.env['helpdesk.ticket'].search([
            ('name', '=', _('Sample Helpdesk Ticket')),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if ticket:
            return ticket
        partner = self.env.user.partner_id.commercial_partner_id
        team = self.env['helpdesk.team'].search([], limit=1)
        category = self.env['helpdesk.category'].search([], limit=1)
        tag = self.env['helpdesk.tag'].search([], limit=1)
        return self.env['helpdesk.ticket'].create({
            'name': _('Sample Helpdesk Ticket'),
            'team_id': team.id if team else False,
            'customer_id': partner.id,
            'email': partner.email,
            'phone': partner.phone,
            'category_id': category.id if category else False,
            'tag_id': tag.id if tag else False,
            'tag_ids': [(6, 0, [tag.id])] if tag else [],
            'user_id': self.env.user.id,
        })

    @api.model
    def action_open_step_sample_ticket(self):
        ticket = self._get_sample_helpdesk_ticket()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample Ticket'),
            'res_model': 'helpdesk.ticket',
            'res_id': ticket.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
