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
from odoo.exceptions import UserError


def unique_data_list(records):
    """
        Return a list containing unique elements from the input list.

        This function takes a list of elements as input and returns a new list
        containing only the unique elements from the input list. It uses a set
        to efficiently eliminate duplicate values while preserving the original
        order.

        Args:
            records (list): The input list containing elements.

        Returns:
            list: A new list containing unique elements from the input list.
    """
    unique_list = list(set(records))
    return unique_list


class MarketingCampaign(models.Model):
    """
        This model is used to define and manage marketing campaigns. Each
        campaign can have various associated activities, participants, and
        templates.
    """
    _name = "marketing.campaign"
    _description = "Marketing Campaign"
    _inherit = "mail.thread"

    name = fields.Char(help="Enter a name for the campaign", required=True,
                       tracking=True)
    user_id = fields.Many2one("res.users", string="Responsible User",
                              default=lambda self: self.env.user.id,
                              help="Choose the responsible user for this campaign", )
    model_id = fields.Many2one("ir.model", string="Target",
                               help="Choose a target model to generate campaign",
                               default=lambda self: self.env.ref(
                                   'base.model_res_partner').id,
                               domain=[('is_mail_thread', '=', True)],
                               tracking=True)
    model_name = fields.Char(related='model_id.model', store=True,
                             help='Model name of the model')
    filter = fields.Char(string="Domain",
                         help="Set domain to filter the records",
                         compute='_compute_filter',
                         readonly=False, store=True)
    marketing_filter_id = fields.Many2one('marketing.filter',
                                          string="Favourite",
                                          help="Choose any predefined template"
                                               "to apply the filter for the domain",
                                          compute='_compute_marketing_filter_id',
                                          readonly=False, store=True,
                                          domain="[('model_name','=',model_name)]")
    marketing_filter_domain = fields.Char('Favorite filter domain',
                                          related='marketing_filter_id.domain',
                                          help='domain for the participants')
    state = fields.Selection(
        [('draft', 'New'), ('running', 'Running'),
         ('stopped', 'Stopped')]
        , string='Status', default='draft', help='State of the campaign',
        group_expand='read_group_stage_ids', tracking=True)
    activity_count = fields.Integer(help='Activity count',
                                    compute='_compute_activity_count')
    test_count = fields.Integer(compute='_compute_test_count',
                                string='Test Records Count')
    participant_count = fields.Integer(compute='_compute_participant_count',
                                       help='Participants Count')
    activity_ids = fields.One2many('marketing.activity',
                                   'campaign_id',
                                   copy=False, string='Activities',
                                   help='Activities of the current campaign')
    template_count = fields.Integer(compute='_compute_template_count',
                                    help='Template count')
    company_id = fields.Many2one('res.company',
                                 required=True,
                                 default=lambda self: self.env.company)

    @api.depends('marketing_filter_id')
    def _compute_filter(self):
        """
            Compute the filter attribute based on the marketing filter
            associated with the record.

            This method is triggered when the marketing filter
            (marketing_filter_id) is changed. It computes the 'filter'
            attribute, which represents the domain of the associated marketing
            filter. If no marketing filter is selected, it sets the 'filter'
            attribute to represent an empty domain.

            Returns:
                None
        """
        for rec in self:
            if rec.marketing_filter_id:
                rec.filter = rec.marketing_filter_id.domain
            else:
                rec.filter = repr([])

    @api.depends('model_name')
    def _compute_marketing_filter_id(self):
        """
            Compute the marketing filter ID based on the model name associated
            with the record.

            This method is triggered when the model name ('model_name') is
            changed. It computes the 'marketing_filter_id' attribute,
            representing the associated marketing filter. In this case,
            it sets the 'marketing_filter_id' to False, indicating no marketing
            filter is associated.

            Returns:
                None
        """
        for record in self:
            record.marketing_filter_id = False

    def _compute_activity_count(self):
        """
            Compute the count of marketing activities for each marketing
            campaign.

            This method calculates the number of marketing activities
            associated with each marketing campaign and updates the
            'activity_count' field accordingly.

            Returns:
                None
        """
        for activity in self:
            activity.activity_count = len(activity.activity_ids)

    def _compute_test_count(self):
        """
            Compute the count of test participants for the current marketing
            campaign.

            This method calculates the number of test participants associated
            with the current marketing campaign and updates the 'test_count'
            field accordingly.

            Returns:
                None
        """
        for tests in self:
            tests.test_count = self.env['marketing.participant'].search_count(
                [('campaign_id', '=', tests.id),
                 ('is_test_participant', '=', True)])

    def _compute_participant_count(self):
        """
            Compute the count of marketing participants for each marketing
            campaign.

            This method calculates the number of marketing participants
            associated with each marketing campaign and updates the
            'participant_count' field accordingly.

            Returns:
                None
        """
        for participants in self:
            participants.participant_count = self.env[
                'marketing.participant'].search_count(
                [('campaign_id', '=', participants.id),
                 ('is_test_participant', '=', False)])

    def _compute_template_count(self):
        """
            Compute the count of marketing templates for each marketing
            campaign.

            This method calculates the number of marketing templates associated
            with each marketing campaign and updates the 'template_count' field
            accordingly.

            Returns:
                None
        """
        for templates in self:
            templates.template_count = self.env['mailing.mailing'].search_count(
                [('cy_automation_template', '=', True),
                 ('campaign_id', '=', templates.id)])

    def unlink(self):
        """Preventing the deletion of the record which is not
        in the draft sate """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _("You can not delete a campaign which is not in draft stage."))
        return super().unlink()

    def action_start_campaign(self):
        """
            Start the marketing campaign by initializing participants and
            scheduling activities.

            This method initiates the marketing campaign by setting its state
            to 'running'. It creates marketing participants for records that
            meet the campaign's filter criteria and associates activities with
            these participants. The scheduling of activities is also triggered
            for each participant.

            Raises:
                UserError: If no activities are defined for the campaign.

            Returns:
                None
        """
        self.ensure_one()
        if not self.activity_ids:
            raise UserError("You must create an activity.")
        self.state = 'running'
        marketing_participant = self.env['marketing.participant']
        record_model = self.env[self.model_name]
        record_data = record_model.search(literal_eval(self.filter or '[]'))
        record_sets = {rec.id for rec in record_data}
        participant_records = marketing_participant.search_read(
            [('campaign_id', '=', self.id),
             ('is_test_participant', '=', False)], ['record_id'])
        current_record = set(
            rec_participants['record_id'] for rec_participants in
            participant_records)
        new_list = record_sets - current_record
        for rec_id in new_list:
            new_participant = {
                'record': f"{self.model_name},{rec_id}",
                'campaign_id': self.id,
                'record_id': rec_id,
                'state': 'running',
                'is_test_participant': False,
                'record_count': len(self.activity_ids),
                'test_activity_ids': [
                    fields.Command.create({'activity_id': item}) for item in
                    self.activity_ids.ids]
            }
            marketing_participant |= marketing_participant.create(
                new_participant)
        for rec in marketing_participant.test_activity_ids.activity_id:
            self.create_schedule_trigger(rec)

    def action_marketing_test(self):
        """
           Open a window to display marketing test participants for the current
           marketing campaign.

           This method returns an action to open a window displaying the
           marketing test participants associated with the current marketing
           campaign. The participants are filtered based on the campaign ID and
           the 'is_test_participant' field.

           Returns:
               dict: Action dictionary to open the window for marketing test
               participants.
       """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participants',
            'view_mode': 'tree,form',
            'res_model': 'marketing.participant',
            'domain': [('campaign_id', '=', self.id),
                       ('is_test_participant', '=', True)],
            'context': {
                'create': False,
            }
        }

    def action_marketing_participant(self):
        """
            Open a window to display marketing participants for the current
            marketing campaign.

            This method returns an action to open a window displaying the
            marketing participants associated with the current marketing
            campaign. The participants are filtered based on the campaign ID
            and the 'is_test_participant' field.

            Returns:
                dict: Action dictionary to open the window for marketing
                participants.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participants',
            'view_mode': 'tree,form',
            'res_model': 'marketing.participant',
            'domain': [('campaign_id', '=', self.id),
                       ('is_test_participant', '=', False)],
            'context': {'create': False}
        }

    def action_marketing_templates(self):
        """
           Open a window to display marketing templates for the current
           marketing campaign.

           This method returns an action to open a window displaying the
           marketing templates associated with the current marketing campaign.
           The templates are filtered based on the campaign ID and the
           'cy_automation_template' field.

           Returns:
               dict: Action dictionary to open the window for marketing
               templates.
       """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Templates',
            'view_mode': 'tree,form',
            'views': [[self.env.ref(
                'cyllo_marketing_automation.view_mailing_mailing_tree').id,
                       'tree'], [self.env.ref(
                'cyllo_marketing_automation.view_mailing_mailing_form').id,
                                 'form']],
            'res_model': 'mailing.mailing',
            'domain': [('campaign_id', '=', self.id),
                       ('cy_automation_template', '=', True)],
            'context': {
                'create': False,
            }
        }

    def action_stop_campaign(self):
        """
            Stop the marketing campaign.

            This method sets the state of the marketing campaign to 'stopped',
            indicating that the campaign has been stopped and no further
            activities will be executed.

            Returns:
                None
        """
        self.state = 'stopped'

    def create_schedule_trigger(self, record):
        """
            Create a schedule trigger for a specific marketing activity.

            This method creates a schedule trigger for the given marketing
            activity record based on its 'trigger_schedule_type'. If the
            trigger type is 'begin', it triggers the specified action
            ('cyllo_marketing_automation.ir_cron_marketing_automation_run_activity') at the
            scheduled time.

            Args:
                record (marketing.activity): The marketing activity record for
                which to create the schedule trigger.

            Returns:
                None
        """
        if record.trigger_schedule_type == 'begin':
            action = self.env.ref(
                'cyllo_marketing_automation.ir_cron_marketing_automation_run_activity')
            action._trigger(at=self.convert_date_object(record))

    def run_marketing_activities(self):
        """
            Run marketing activities for all running marketing campaigns.

            This method identifies all marketing campaigns in the 'running'
            state and executes their
            marketing activities by calling the 'marketing_execute' method for
            each campaign's activities.

            Returns:
                None
        """
        marketing_campaign = self.search([('state', '=', 'running')])
        for campaigns in marketing_campaign:
            campaigns.activity_ids.marketing_execute()

    def convert_date_object(self, record):
        """
            Convert the date object based on the trigger type and trigger value

            This method takes a marketing activity record and calculates the
            'test_date_started' based on the trigger type and trigger value.
            It uses a base date-time, either from the sub-parent activity or
            the current date-time if no sub-parent activity exists.

            Args:
                record (marketing.activity): The marketing activity record for
                which to calculate the date.

            Returns:
                datetime: The calculated 'test_date_started'.
        """
        trigger_types = {
            'hour': 'hours',
            'week': 'weeks',
            'day': 'days',
            'month': 'months',
        }
        trigger_type = trigger_types.get(record.activity_trigger_type, None)
        if trigger_type:
            base_datetime = (
                record.sub_parent_activity_id.test_date_started.replace(
                    second=0, microsecond=0)) \
                if record.sub_parent_activity_id else (
                fields.datetime.now().replace(second=0, microsecond=0))
            record.test_date_started = base_datetime + relativedelta(
                **{trigger_type: record.activity_trigger})
        return record.test_date_started

    def read_group_stage_ids(self, states, domain, order):
        """
            Get the list of stage IDs for reading group stages.

            This method retrieves the stage IDs from the 'state' selection
            field in the current model.

            Args:
                states (list): List of states to consider for the reading group
                domain (list): List of domain conditions to filter the states.
                order (list): List of order conditions for sorting the states.

            Returns:
                list: A list of stage IDs from the 'state' selection field.
        """
        return [key for key, _ in self._fields['state'].selection]
