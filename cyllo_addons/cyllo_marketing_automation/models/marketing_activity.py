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
from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.osv.expression import AND


class MarketingActivity(models.Model):
    """
        This model is used to define various marketing activities that can be
        part of a marketing campaign. Each activity is associated with a type
        and can have specific triggers, conditions,and actions.
    """
    _name = "marketing.activity"
    _description = "Marketing Activity"

    name = fields.Char(string="Activity", help="Enter a name for you activity",
                       required=True)
    type = fields.Selection([('mail', 'Mail'),
                             ('server', 'Server Action')],
                            string="Activity Type",
                            help="Choose your activity type", required=True,
                            default='mail')
    campaign_id = fields.Many2one('marketing.campaign',
                                  ondelete='Cascade',
                                  required=True,
                                  help='Campaign related to activity')
    activity_trigger = fields.Integer(string="Trigger",
                                      help="Choose the time need to trigger your activity",
                                      default='1', required=True)
    activity_trigger_type = fields.Selection(
        [('hour', 'Hour'), ('day', 'Day'), ('week', 'Week'),
         ('month', 'Month')],
        string="Type", help="Choose the activity trigger type", default='hour',
        required=True)

    trigger_schedule_type = fields.Selection([
        ('begin', 'beginning of workflow'),
        ('activity_another', 'another activity'),
        ('mail_open', 'Mail: opened'), ('mail_not_open', 'Mail: not opened'),
        ('mail_reply', 'Mail: replied'),
        ('mail_not_reply', 'Mail: not replied'),
        ('mail_click', 'Mail: clicked'),
        ('mail_not_click', 'Mail: not clicked'),
        ('mail_bounce', 'Mail: bounced')], default='begin', required=True,
        string='Trigger Type',
        help='Choose trigger type of the activity')

    model_id = fields.Many2one('ir.model', related='campaign_id.model_id',
                               help='Activity Model')
    model_name = fields.Char(related='model_id.model', help='Model name')
    mailing_mailing_id = fields.Many2one('mailing.mailing',
                                         string='Marketing Template',
                                         domain=[('cy_automation_template', '=',
                                                  True),
                                                 ('mailing_type', '=', 'mail')],
                                         help='Choose your mail template \n Note: Choose different template for each '
                                              'activity. Otherwise may cause to duplicate mailing')
    server_action_id = fields.Many2one('ir.actions.server',
                                       help='Set your server action')
    domain_activity = fields.Char(default="[]", string='Domain',
                                  help="Set domain to filter the records")
    domain = fields.Char(store=True, compute='_compute_domain', recursive=True,
                         help="Applied domain for records")
    parent_activity_id = fields.Many2one('marketing.activity',
                                         help="Main parent activity",
                                         ondelete='Cascade')
    sub_parent_activity_id = fields.Many2one('marketing.activity',
                                             string='Sub Parent',
                                             ondelete='Cascade',
                                             help='Parent activity of the corresponding activity',
                                             readonly=True)
    participant_id = fields.Many2one('marketing.participant',
                                     help='Participant related to activity')
    test_date_started = fields.Datetime(string='Date',
                                        help='Created date and time')
    h_level_css = fields.Char(string='Hierarchy Style',
                              help='Hierarchical style')
    state = fields.Selection(
        [('schedule', 'SCHEDULED'), ('processed', 'PROCESSED'),
         ('cancel', 'CANCELLED'),
         ('reject', 'REJECTED')], default='schedule',
        help='status of the activity')

    @api.depends('domain_activity', 'campaign_id.filter',
                 'parent_activity_id.domain')
    def _compute_domain(self):
        """
            Compute the 'domain' field based on 'domain_activity', '
            campaign_id.filter', and 'parent_activity_id.domain'.
            This method is triggered when 'domain_activity',
            'campaign_id.filter', or 'parent_activity_id.domain' changes.
            Returns:
                None
        """
        for record in self:
            final_filter_domain = AND([literal_eval(record.domain_activity),
                                       literal_eval(record.campaign_id.filter)])
            parent_id = record.parent_activity_id
            while parent_id:
                final_filter_domain = AND([final_filter_domain, literal_eval(
                    parent_id.domain_activity)])
                parent_id = parent_id.parent_activity_id
            record.domain = final_filter_domain

    @api.onchange('activity_trigger', 'activity_trigger_type')
    def _onchange_activity_trigger(self):
        """
            Compute the test date started based on the activity trigger and
            type.

            This method is triggered whenever the 'activity_trigger' or
            'activity_trigger_type' fields are changed. It calculates the
            'test_date_started' based on the provided trigger value and type.

            Returns:
                None
        """
        for record in self:
            record.test_date_started = self.get_test_date_start(
                record.activity_trigger_type, record.activity_trigger)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            trigger_type = vals.get('activity_trigger_type', False)
            activity_trigger = vals.get('activity_trigger', False)
            if activity_trigger and trigger_type:
                vals['test_date_started'] = self.get_test_date_start(
                    trigger_type, activity_trigger)
        return super().create(vals_list)

    @staticmethod
    def get_test_date_start(trigger_type, activity_trigger):
        response_date = ''
        if trigger_type == 'hour':
            response_date = (fields.datetime.now() + relativedelta(
                hours=activity_trigger))
        elif trigger_type == 'week':
            response_date = (fields.datetime.now() + relativedelta(
                weeks=activity_trigger))
        elif trigger_type == 'day':
            response_date = (fields.datetime.now() + relativedelta(
                days=activity_trigger))
        elif trigger_type == 'month':
            response_date = (fields.datetime.now() + relativedelta(
                months=activity_trigger))
        return response_date

    def marketing_execute(self):
        """
           Execute marketing actions for participants in the current campaign.
           This method retrieves marketing participants for the current
           campaign and iterates over them,
           executing actions for each participant using the 'execute_actions'
           method.
           Returns:
               None
       """
        batch_size = 20
        marketing_participant = self.env['marketing.participant'].search(
            [('is_test_participant', '!=', True),
             ('campaign_id', '=', self.campaign_id.id)])
        for batch_start in range(0, len(marketing_participant), batch_size):
            participants_batch = marketing_participant[
                batch_start:batch_start + batch_size]
            self._execute_actions_batch(participants_batch)

    def _execute_actions_batch(self, participants_batch):
        """
            Execute marketing actions for a batch of participants.

            This internal helper method loops through a batch of marketing participants
            and calls the `execute_actions` method for each one.

            Args:
                participants_batch (list): A list of marketing.participant records to process.

            Returns:
                None
            """
        for participant in participants_batch:
            self.execute_actions(participant)

    def execute_actions(self, participant):
        """
            Execute marketing actions for a given participant.

            This method processes the marketing actions for the specified
            participant based on their marketing activity lines.

            Args:
                participant (marketing.participant): The participant for whom
                marketing actions are executed.

            Returns:
                None
        """
        marketing_activity_line = participant.test_activity_ids.filtered(
            lambda rec: rec.state == "schedule")
        activity_ids = marketing_activity_line.mapped("activity_id")
        for index in range(len(marketing_activity_line)):
            activity_id = activity_ids[index]
            activity_line = marketing_activity_line[index]
            method_function = getattr(self, '_execute_%s' % activity_id.type)
            if activity_id.domain_activity == "[]":
                if activity_id.trigger_schedule_type == "begin" and activity_line.state == 'schedule':
                    mail = method_function(participant,
                                           activity_line.activity_id,
                                           activity_line,
                                           participant.is_test_participant)
                    parent_children = (participant.test_activity_ids.filtered(
                        lambda rec: rec.activity_id.
                                    sub_parent_activity_id == activity_id))
                    if (
                            mail and parent_children.activity_id.trigger_schedule_type in
                            ['activity_another', 'mail_not_open',
                             'mail_not_reply', 'mail_not_click'] and
                            parent_children.state == 'schedule'):
                        participant.write({
                            'activity_executed_ids': [(4, mail.id)]
                        })
                    activity_another_ids = activity_ids.filtered(
                        lambda rec: rec.sub_parent_activity_id == activity_id)
                    if activity_another_ids:
                        self.generate_schedule_trigger_next_activity(
                            activity_another_ids, participant)
                elif (activity_id.trigger_schedule_type in ['activity_another',
                                                            'mail_not_open',
                                                            'mail_not_reply',
                                                            'mail_not_click']
                      and activity_line.state == 'schedule'):
                    if (
                            activity_id.test_date_started <= fields.Datetime.now().replace(
                            second=0) or
                            participant.is_test_participant):
                        if (
                                participant.activity_executed_ids and activity_id.trigger_schedule_type !=
                                'activity_another' and participant.activity_executed_ids.filtered(
                            lambda trace: trace.marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id)):
                            if participant.activity_executed_ids.filtered(
                                    lambda trace: trace.marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id).marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id and \
                                    participant.activity_executed_ids.filtered(
                                        lambda trace: trace.marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id).marketing_activity_line_id.participant_id == participant and \
                                    participant.activity_executed_ids.filtered(
                                        lambda trace: trace.marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id).trace_status in [
                                'open', 'reply']:
                                if activity_id.trigger_schedule_type == 'mail_not_click' and participant.activity_executed_ids.filtered(
                                        lambda trace: trace.marketing_activity_line_id.activity_id == activity_id.sub_parent_activity_id).links_click_datetime:
                                    activity_line.write({
                                        'state': 'cancel',
                                        'mail_failure_message': 'Mail Clicked'
                                    })
                                else:
                                    activity_line.write({
                                        'state': 'cancel',
                                        'mail_failure_message': 'Mail Opened'
                                    })
                            else:
                                method_function(participant,
                                                activity_line.activity_id,
                                                activity_line,
                                                participant.is_test_participant)
                        else:
                            method_function(participant,
                                            activity_line.activity_id,
                                            activity_line,
                                            participant.is_test_participant)
                    activity_another_ids = activity_ids.filtered(
                        lambda rec: rec.sub_parent_activity_id == activity_id)
                    if activity_another_ids:
                        self.generate_schedule_trigger_next_activity(
                            activity_another_ids, participant)
                elif (activity_id.trigger_schedule_type in ['mail_click',
                                                            'mail_open',
                                                            'mail_repy',
                                                            'mail_bounce'] and
                      activity_line.state == 'schedule' and activity_line.activity_another_trigger):
                    method_function(participant, activity_line.activity_id,
                                    activity_line,
                                    participant.is_test_participant)

    def test_participant_trigger(self, participant, activity_line):
        """
            Trigger a test participant for a specific marketing activity.

            This method retrieves the method function for the specified
            marketing activity type and executes it for the given participant
            and activity line, simulating the action.

            Args:
                participant (marketing.participant): The participant for whom
                the test action is triggered.activity_line
                (marketing.activity.line): The marketing activity line for
                which the test action is triggered.

            Returns:
                mail.activity.mail: The simulated mail activity created during
                the test.
        """
        method_function = getattr(self, '_execute_%s' % (
            activity_line.activity_id.type))
        mail = method_function(participant, activity_line.activity_id,
                               activity_line, True)
        return mail

    def generate_schedule_trigger_next_activity(self, activity_another_ids,
                                                participant):
        """
            Generate and trigger the next scheduled activities based on a set
            of related activities.

            This method processes a set of related activities
            (activity_another_ids) for a participant.
            For each activity, it checks the trigger_schedule_type and, if
            applicable, triggers the next scheduled activities.

            Args:
                activity_another_ids (list): List of marketing activity records
                related to the current activity.
                participant (marketing.participant): The participant for whom
                the next scheduled activities are triggered.

            Returns:
                None
        """
        cron = {}
        for activity in activity_another_ids:
            marketing_activity_line = participant.test_activity_ids.filtered(
                lambda rec: rec.activity_id == activity)
            if (marketing_activity_line.activity_id.trigger_schedule_type in [
                'activity_another', 'mail_not_open',
                'mail_not_reply', 'mail_not_click']):
                action = self.env.ref(
                    'cyllo_marketing_automation.ir_cron_marketing_automation_run_activity')
                cron = action._trigger(
                    at=marketing_activity_line.activity_id.campaign_id.
                    convert_date_object(marketing_activity_line.activity_id))
        return cron

    def _execute_server(self, participant, activity, activity_line, test=None):
        """
            Execute a server action for a participant in the context of a
            marketing activity.

            This method prepares and runs a server action associated with the
            specified marketing activity for the given participant. It handles
            the timing of the action based on the activity's
            'test_date_started' and whether it is a test run.

            Args:
                participant (marketing.participant): The participant for whom
                    the server action is executed.
                activity (marketing.activity): The marketing activity
                    associated with the server action.
                activity_line (marketing.activity.line): The marketing activity
                    line corresponding to the execution.
                test (bool): If True, indicates that the execution is a test
                    run (default is None).
            Returns:
                None
        """
        server_action = activity.server_action_id.with_context(
            active_ids=[participant.record_id],
            active_id=participant.record_id,
            active_model=activity.model_name)
        try:
            if test or activity.test_date_started <= fields.Datetime.now().replace(
                    second=0):
                participant.is_inactive = True
                server_action.run()
                activity_line.write({
                    'state': 'processed'
                })
                participant.record_count -= 1
                if not test and participant.record_count == 0:
                    participant.write({
                        'state': 'completed'
                    })
        except Exception as e:
            activity_line.write({
                'state': 'error',
                'mail_failure_message': _(e),
            })
        return True

    def _execute_mail(self, participant, activity, activity_line, test=None):
        """
            Execute a mail action for a participant in the context of a
            marketing activity.

            This method prepares and sends an email associated with the
            specified marketing activity for the given participant. It handles
            the timing of the action based on the activity's
            'test_date_started' and whether it is a test run.

            Args:
                participant (marketing.participant): The participant for whom
                    the mail action is executed.
                activity (marketing.activity): The marketing activity
                    associated with the mail action.
                activity_line (marketing.activity.line): The marketing activity
                    line corresponding to the execution.
                test (bool): If True, indicates that the execution is a test
                    run (default is None).

            Returns:
                mailing.trace: The mailing trace record associated with the
                    mail action.
        """
        mail_status = None
        if test or activity.test_date_started <= fields.Datetime.now().replace(
                second=0):
            record_id = [participant.record_id]
            new_dict = {'default_marketing_activity_id': activity.id,
                        'active_ids': record_id, **activity._context}
            mail = activity.mailing_mailing_id.with_context(new_dict)
            mail.body_html = mail.body_arch
            try:
                mail.action_send_mail(record_id)
            except Exception as e:
                activity_line.write({
                    'state': 'error',
                    'mail_failure_message': _(e),
                })
            else:
                for trace_id in activity_line.mail_trace_ids:
                    mail_status = self.env['mailing.trace'].sudo().browse(
                        trace_id.id)
                    activity_line.mail_failure_message = (
                        mail_status.get_display_value(mail_status.failure_type))
                    status_to_state = {'cancel': 'cancel', 'sent': 'processed',
                                       'error': 'error', 'bounce': 'error',
                                       'outgoing': 'processed'}
                    new_state = status_to_state.get(mail_status.trace_status,
                                                    False)
                    if new_state:
                        activity_line.write({'state': new_state})
                participant.record_count -= 1
                if not test and participant.record_count == 0:
                    participant.write({'state': 'completed'})
                return mail_status
