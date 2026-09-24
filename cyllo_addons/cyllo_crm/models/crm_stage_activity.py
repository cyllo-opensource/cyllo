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
from datetime import timedelta

from odoo import Command, api, fields, models


class CrmStageActivity(models.Model):
    """This class manages mandatory activities in a stage"""
    _name = 'crm.stage.activity'
    _description = 'CRM Stage Required Activities'

    stage_id = fields.Many2one(
        'crm.stage',
        string='Stage',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.company)
    sequence = fields.Integer('Sequence', default=10)
    user_id = fields.Many2one('res.users', string="Assigned user")
    activity_id = fields.Many2one(
        'mail.activity.type',
        string='Required Activity',
        required=True,
        ondelete='cascade',
    )
    is_exit_criteria = fields.Boolean(default=False, string="is exit criteria")

    @api.model
    def _create_exit_criteria_if_needed(self, opportunity_id, stage_id):
        """
        Check if there are any open activities for the opportunity.
        If not, create exit criteria activities.
        """
        opportunity = self.env['crm.lead'].browse(opportunity_id)
        if not opportunity or not opportunity.exists():
            return False

        # Get all exit criteria for the current stage
        exit_criteria = self.search([
            ('stage_id', '=', stage_id),
            ('is_exit_criteria', '=', True)
        ])

        if not exit_criteria:
            return False

        # Check if there are any open activities for this opportunity
        open_activities = self.env['mail.activity'].search_count([
            ('res_id', '=', opportunity.id),
            ('res_model', '=', 'crm.lead'),
            ('state', '!=', 'done'), ('is_exit_criteria', '=', True)
        ])
        # If no open activities, create exit criteria activities
        if not open_activities:
            if stage_id not in opportunity.triggered_stage_ids.ids:
                opportunity.write({
                    "triggered_stage_ids": [Command.link(stage_id)]
                })
                # Get responsible user
                user_id = exit_criteria.user_id.id or opportunity.user_id.id or self.env.uid
                deadline = fields.Date.context_today(
                    self) + timedelta(
                    days=exit_criteria.activity_id.delay_count or 0)

                # Create activity
                self.env['mail.activity'].create({
                    'activity_type_id': exit_criteria.activity_id.id,
                    'summary': f"Exit criteria: {exit_criteria.activity_id.name}",
                    'note': f"This activity must be completed to move from the {opportunity.stage_id.name} stage.",
                    'date_deadline': deadline,
                    'user_id': user_id,
                    'res_model_id': self.env.ref('crm.model_crm_lead').id,
                    'res_id': opportunity.id,
                    'is_exit_criteria': True,
                })
                self.notify_user_activity(user_id,
                                          exit_criteria.activity_id.name,
                                          opportunity.stage_id.name,
                                          opportunity.name, str(deadline))
            return True
        return False

    def notify_user_activity(self, user_id, activity, stage_name, lead_name,
                             deadline):
        """Send email to the users about assigned activity"""
        user = self.env['res.users'].browse(user_id)
        template = self.env.ref(
            'cyllo_crm.email_template_activity_assigned')
        template.with_context({
            'user_name': user.name,
            'email_to': user.email,
            'lead_name': lead_name,
            'stage_name': stage_name,
            'activity_name': activity,
            'due_date': deadline,
        }).send_mail(self.id, force_send=True)
