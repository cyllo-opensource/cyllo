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
from odoo import api, fields, models


class MailActivity(models.Model):
    """Inherited mail.activity for crm dashboard"""
    _inherit = 'mail.activity'

    is_dismissed_notification = fields.Boolean(default=False)
    is_marked_as_read = fields.Boolean(default=False)
    is_exit_criteria = fields.Boolean(default=False)

    @api.model
    def get_crm_activities_summary(self, date_from=None, date_to=None,
                                   domain=None):
        """Get CRM activities summary for dashboard"""
        base_domain = [('res_model', '=', 'crm.lead')]

        if date_from:
            base_domain.append(('date_deadline', '>=', date_from))
        if date_to:
            base_domain.append(('date_deadline', '<=', date_to))

        # If domain is provided for leads, filter activities by those lead IDs
        if domain:
            crm_lead_obj = self.env['crm.lead']
            filtered_leads = crm_lead_obj.search(domain)
            lead_ids = filtered_leads.ids
            base_domain.append(('res_id', 'in', lead_ids))

        activities = self.search(base_domain)

        # Group by activity type
        summary = {}
        for activity in activities:
            activity_type = activity.activity_type_id.name
            if activity_type not in summary:
                summary[activity_type] = 0
            summary[activity_type] += 1

        return summary
