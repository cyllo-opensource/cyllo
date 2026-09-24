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


class MarketingParticipant(models.Model):
    """
        This model is used to store information about participants in marketing
        campaigns. Participants can be associated with specific records,
        campaigns, and activities.
    """
    _name = "marketing.participant"
    _description = "Marketing Participants"
    _rec_name = 'record'

    campaign_id = fields.Many2one('marketing.campaign',
                                  help='Campaign related to participant')
    model_name = fields.Char(related='campaign_id.model_id.name',
                             string='Model', help='Model Name')
    record = fields.Reference(selection='_selection_models',
                              inverse='_inverse_record',
                              help='Reference record of each participants',
                              required=True)
    record_id = fields.Integer(help='Id of the selected record')
    test_activity_ids = fields.One2many('marketing.activity.line',
                                        'participant_id',
                                        string='Activity Lines',
                                        help='Activities for participants')
    is_test_participant = fields.Boolean(string='Test Participant',
                                         help='Check the record is test participant or not')
    test_date_started = fields.Datetime(default=fields.Datetime.now,
                                        string='Date',
                                        help='Date and time of the record created')
    is_inactive = fields.Boolean(string='Inactive',
                                 help='To check whether the participant is executed or not')
    record_count = fields.Integer(help='Count of the activities')
    state = fields.Selection(
        [('running', 'Running'), ('completed', 'Completed')],
        help='Current state of the participant')
    activity_ids = fields.Many2many('marketing.activity',
                                    compute='_compute_activity_ids',
                                    string='Activities',
                                    help='All Activity lists')
    marketing_activity_count = fields.Integer(string='Activity Count',
                                              help='Marketing activity count')
    activity_executed_ids = fields.Many2many('mailing.trace',
                                             string='Mail Trace',
                                             help='Mails delivered from each lines')

    @api.depends('test_activity_ids')
    def _compute_activity_ids(self):
        """
            Compute the list of activity IDs associated with the test
            activities.

            This method calculates the list of activity IDs based on the
            'test_activity_ids' field. It extracts the activity IDs from the
            related test activities and updates the 'activity_ids' field
            accordingly.

            Returns:
                None
        """
        for rec in self:
            rec.activity_ids = rec.test_activity_ids.mapped('activity_id.id')

    def _inverse_record(self):
        """
            Set the 'record_id' field based on the associated record.

            This method iterates through the records in the current set and
            updates the 'record_id' field based on the ID of the associated
            record

            Returns:
                None
        """
        for rec in self.filtered('record'):
            rec.record_id = rec.record.id

    def unlink(self):
        """
            Delete the marketing activities and associated mail traces.

            This method first deletes the associated mail traces for each test
            activity. It then calls the superclass method to perform the
            regular deletion of the marketing activities.

            Returns:
                bool: True if the deletion is successful, False otherwise.
        """
        for rec in self.test_activity_ids.mail_trace_ids:
            trace_id = rec.id
            mail_trace = self.env['mailing.trace'].browse(trace_id)
            mail_trace.unlink()
        res = super().unlink()
        return res

    @api.model
    def _selection_models(self):
        """
            Get a selection of models that are mail threads.

            This method queries the 'ir.model' model to retrieve models that
            are mail threads (have 'is_mail_thread' set to True) and returns
            them in a format suitable for selection fields.

            Returns:
                list: A list of tuples representing model choices, where each
                tuple contains the model name and its display name.
        """
        target = self.env['ir.model'].sudo().search(
            [('is_mail_thread', '=', True)])
        return [(record.model, record.name) for record in target]

    @api.model
    def update_record(self, data):
        """
            Update a marketing participant record and trigger a test activity.

            This method takes a dictionary `data` as input, which should
            contain 'activity_line' and 'participant_id' keys. It uses these
            keys to retrieve the corresponding marketing activity line and
            participant records. The method then triggers a test activity using
            the 'test_participant_trigger' method and updates the 'is_inactive'
            field of the participant record.

            Args:
                data (dict): A dictionary containing 'activity_line' and
                'participant_id' keys.

            Returns:
                dict: The result of the 'test_participant_trigger' method in
                dictionary form.
        """
        activity_line = self.env['marketing.activity.line'].browse(
            data['activity_line'])
        record = self.env['marketing.participant'].browse(
            data['participant_id'])
        activity_line.activity_id.test_participant_trigger(record,
                                                           activity_line)
        if not record.is_inactive:
            record.is_inactive = True

    @api.model
    def create_test_participant(self, data):
        """
            Create a test participant for a marketing campaign.

            This method takes a dictionary `data` as input, which should
            contain keys such as 'campaign_id', 'record', 'record_id',
            'record_count', and 'is_test_participant'. It creates a new
            participant record with the provided information and associates it
            with the specified marketing campaign. The 'test_activity_ids'
            field is populated with activity commands based on the
            activities defined in the campaign.

            Args:
                data (dict): A dictionary containing information for creating
                a test participant.

            Returns:
                int: The ID of the newly created test participant record.
        """
        campaign = self.env['marketing.campaign'].browse(data['campaign_id'])
        new_participant = {
            'record': data['record'],
            'campaign_id': data['campaign_id'],
            'record_id': data['record_id'],
            'state': 'running',
            'record_count': data['record_count'],
            'is_test_participant': data['is_test_participant'],
            'test_activity_ids': [fields.Command.create({'activity_id': item})
                                  for item in campaign.activity_ids.ids]
        }
        return self.create(new_participant).id
