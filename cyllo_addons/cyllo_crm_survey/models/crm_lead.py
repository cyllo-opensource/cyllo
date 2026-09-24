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
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    survey_count = fields.Integer(compute='_compute_survey_count', string='Survey Count')

    def _compute_survey_count(self):
        """Compute the number of surveys associated with the lead."""
        for lead in self:
            lead.survey_count = self.env['survey.survey'].search_count([('lead_id', '=', lead.id)])

    def action_view_surveys(self):
        """Action to view the surveys."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_form')
        action['domain'] = [('lead_id', '=', self.id)]
        action['context'] = {'default_lead_id': self.id}
        return action

    def action_create_survey(self):
        """Action to create the survey."""
        lead = self[0] if self else self.env['crm.lead']
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'view_mode': 'form, kanban',
            'views': [
                (self.env.ref('survey.survey_survey_view_form').id, 'form'),
                (self.env.ref('survey.survey_survey_view_kanban').id, 'kanban'),
            ],
            'target': 'current',
            'context': {
                'default_title': f'{lead.display_name} Survey' if lead else 'New Survey',
                'default_lead_id': lead.id,
            },
        }
