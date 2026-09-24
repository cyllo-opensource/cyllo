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
from dateutil.relativedelta import relativedelta
from odoo import fields, models


class MarketingActivityLine(models.Model):
    """
        This model is used to create instances of marketing activities within
        the context of a marketing campaign. Each activity line is associated
        with a specific marketing activity, participant,and campaign.

    """
    _name = "marketing.activity.line"
    _description = "Activity Lines"
    _rec_name = "participant_id"

    activity_id = fields.Many2one('marketing.activity', ondelete='cascade',
                                  help='Activity in the activity line')
    participant_id = fields.Many2one('marketing.participant',
                                     help='Participant in the activity line')
    state = fields.Selection(
        [('schedule', 'SCHEDULED'), ('processed', 'PROCESSED'),
         ('error', 'ERROR'), ('cancel', 'CANCELLED')], default='schedule',
        help='Current state of the activity line')
    record_id = fields.Integer(related='participant_id.record_id',
                               help='Id of the selected record')
    mail_trace_ids = fields.One2many('mailing.trace',
                                     'marketing_activity_line_id',
                                     help='Mails delivered form the activity lines')
    mail_failure_message = fields.Char(string='Failure Message',
                                       help='Mail Failure Reason')
    activity_another_trigger = fields.Boolean(string='Trigger Next',
                                              help='Trigger the activity next')
    mail_clicked = fields.Boolean(help='Is mail clicked')
    mail_replied = fields.Boolean(help='Is mail replied')
    mail_opened = fields.Boolean(help='Is mail opened')
    mail_bounced = fields.Boolean(help='Is mail bounced')

    def trigger_next_activity(self, execution):
        """
           Trigger the next scheduled activities based on the specified
           execution for the current activity.

           This method processes the specified execution (e.g., 'click',
           'opened', 'replied') and updates
           the relevant fields accordingly. It then identifies the next
           scheduled activities and triggers
           their execution.

           Args:
               execution (str): The type of execution triggered ('click',
               'opened', 'replied').

           Returns:
               None
       """
        activity = self.participant_id.test_activity_ids.activity_id.filtered(
            lambda rec: rec.sub_parent_activity_id.id == self.activity_id.id)
        if execution == 'click':
            self.mail_clicked = True
            self.mail_opened = True
        elif execution == 'opened':
            self.mail_opened = True
        elif execution == 'replied':
            self.mail_replied = True
            self.mail_opened = True
        elif execution == 'bounced':
            self.mail_bounced = True
        for activity_next in activity:
            activity_line = self.participant_id.test_activity_ids.filtered(
                lambda line: line.activity_id == activity_next)
            if activity_next.activity_trigger_type == 'hour':
                activity_next.test_date_started = (
                        fields.datetime.now() + relativedelta(
                    hours=activity_next.
                    activity_trigger))
            elif activity_next.activity_trigger_type == 'week':
                activity_next.test_date_started = (
                        fields.datetime.now() + relativedelta(
                    weeks=activity_next.
                    activity_trigger))
            elif activity_next.activity_trigger_type == 'day':
                activity_next.test_date_started = (
                        fields.datetime.now() + relativedelta(
                    days=activity_next.
                    activity_trigger))
            elif activity_next.activity_trigger_type == 'month':
                activity_next.test_date_started = (
                        fields.datetime.now() + relativedelta(
                    months=activity_next.
                    activity_trigger))
            activity_line.activity_another_trigger = True
            action = self.env.ref(
                'cyllo_marketing_automation.ir_cron_marketing_automation_run_activity')
            action._trigger(
                at=activity_next.campaign_id.convert_date_object(activity_next))
