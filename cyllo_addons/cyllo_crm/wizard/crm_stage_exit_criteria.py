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
import logging
from collections import defaultdict
from datetime import timedelta

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)


class CrmStageExitCriteria(models.TransientModel):
    """wizard to manage exit criteria"""
    _name = 'crm.stage.exit.criteria'
    _description = 'Configure CRM Stage Exit Criteria'

    user_id = fields.Many2one('res.users', string="Assigned user")
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.company)
    stage_ids = fields.Many2many('crm.stage', string='Stages')
    exit_criteria_ids = fields.One2many('crm.stage.exit.criteria.line',
                                        'wizard_id', string='Exit Criteria')

    def action_save(self):
        """Save action for exit criteria"""
        activity = self.env['crm.stage.activity']
        existing_activities = activity.search([('is_exit_criteria', '=', True)])
        existing_key = {
            (rec.stage_id.id, rec.activity_id.id): rec for rec in
            existing_activities
        }
        new_keys = set()
        criteria_ids = []
        for line in self.exit_criteria_ids:
            key = (line.stage_id.id, line.activity_id.id)
            new_keys.add(key)
            existing = existing_key.get(key)
            if existing:
                new_user = line.user_id.id or False
                if existing.user_id.id != new_user:
                    existing.write({'user_id': new_user})
            else:
                criteria = activity.create({
                    'stage_id': line.stage_id.id,
                    'activity_id': line.activity_id.id,
                    'sequence': 10,
                    'user_id': line.user_id.id,
                    'is_exit_criteria': True,
                })
                criteria_ids.append(criteria.id)

        for key, rec in existing_key.items():
            if key not in new_keys:
                activities = self.env['mail.activity'].search(
                    [('is_exit_criteria', '=', True),
                     ('activity_type_id', '=', rec.activity_id.id)])
                for act in activities:
                    self.env['crm.lead'].browse(act.res_id).write({
                        "triggered_stage_ids": [Command.unlink(rec.stage_id.id)]
                    })
                activities.unlink()
                rec.unlink()

        self.env['ir.config_parameter'].sudo().set_param(
            'crm.exit_criteria_configured', 'True'
        )
        if criteria_ids:
            self.create_exit_criteria_activity(criteria_ids)
            self.notify_users_email(criteria_ids)

    def create_exit_criteria_activity(self, criteria_ids):
        """Create activity for existing leads"""
        activities = self.env['crm.stage.activity'].browse(criteria_ids)
        for activity in activities:
            stage_id = activity.stage_id.id
            activity_id = activity.activity_id.id
            leads = self.env['crm.lead'].search([('stage_id', '=', stage_id)])
            for lead in leads:
                user_id = activity.user_id.id or lead.user_id.id or self.env.uid

                # Create activity
                self.env['mail.activity'].create({
                    'activity_type_id': activity_id,
                    'summary': f"Exit criteria: {activity.activity_id.name}",
                    'note': f"This activity must be completed to move from the {lead.stage_id.name} stage.",
                    'date_deadline': fields.Date.context_today(
                        self) + timedelta(
                        days=activity.activity_id.delay_count or 0),
                    'user_id': user_id,
                    'res_model_id': self.env.ref('crm.model_crm_lead').id,
                    'res_id': lead.id,
                    'is_exit_criteria': True,
                })

                # Update stage id to triggered stages
                lead.write({
                    "triggered_stage_ids": [Command.link(stage_id)]
                })

    def notify_users_email(self, criteria_ids):
        """Notify Assigned Users by email"""
        user_activities = defaultdict(list)
        activities = self.env['crm.stage.activity'].browse(criteria_ids)
        for record in activities:
            if record.user_id:
                user_activities[record.user_id.id].append(record)

        for user_id, record in user_activities.items():
            user = self.env['res.users'].browse(user_id)
            if not user.email:
                continue
            activities = [
                f"Activity: {rec.activity_id.name} on Stage: {rec.stage_id.name}"
                for rec in record
            ]
            body = (
                f"Dear {user.name},\n\n"
                "You have been assigned to the following CRM activities for existing leads:\n\n"
                f"{chr(10).join(activities)}\n\n"
                "Your attention to these activities is crucial to maintain our credibility and ensure proper follow-up "
                "at each stage of the customer journey. Please prioritize completing these actions to help move leads "
                "through their respective stages.\n\n"
                "Timely completion will not only improve our conversion rates but also enhance customer satisfaction.\n\n"
                "Thank you for your dedication to maintaining our high standards of customer engagement!"
            )
            mail = self.env['mail.mail'].create({
                'subject': 'CRM Stage Activities Notification',
                'body_html': f'<pre>{body}</pre>',
                'email_to': user.email,
            })
            mail.send()
