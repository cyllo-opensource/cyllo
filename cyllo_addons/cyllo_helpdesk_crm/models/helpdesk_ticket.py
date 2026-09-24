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
from odoo import fields, models, api, _


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    crm_lead_ids = fields.One2many('crm.lead', 'helpdesk_ticket_id',
                                   string='CRM Leads')
    crm_lead_count = fields.Integer(compute='_compute_crm_lead_count',
                                    string="CRM Lead Count")

    @api.depends('crm_lead_ids')
    def _compute_crm_lead_count(self):
        for ticket in self:
            ticket.crm_lead_count = len(ticket.sudo().crm_lead_ids)

    def action_view_crm_leads(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm.crm_lead_action_pipeline")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        action['context'] = {'default_helpdesk_ticket_id': self.id}
        return action

    def action_create_crm_lead(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm.crm_lead_action_pipeline")
        action['res_model'] = 'crm.lead'
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('crm.crm_lead_view_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_name': self.name,
            'default_helpdesk_ticket_id': self.id,
        }
        self._message_log(body=_("CRM Lead creation initiated."))
        return action
