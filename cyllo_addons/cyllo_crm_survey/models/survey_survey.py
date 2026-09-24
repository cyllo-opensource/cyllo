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


class SurveyTemplate(models.Model):
    _inherit = 'survey.survey'

    lead_id = fields.Many2one('crm.lead', 'Lead')
    create_lead = fields.Boolean('Create Lead', help="If checked, a CRM Lead will be created upon survey submission.")

    def action_send_survey(self):
        """Send survey to the lead."""
        rec = super().action_send_survey()
        context = dict(rec.get('context', {}))
        lead_id = self.env.context.get('default_lead_id')
        if lead_id:
            lead = self.env['crm.lead'].browse(lead_id)
            if lead.partner_id:
                context['default_partner_ids'] = [(6, 0, [lead.partner_id.id])]
        rec['context'] = context
        return rec


