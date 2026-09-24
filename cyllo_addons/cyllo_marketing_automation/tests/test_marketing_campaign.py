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
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

_logger = logging.getLogger(__name__)

class TestMailingTrace(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_campaign.

            Creates a marketing filter, campaign, and related records.
        """
        super().setUpClass()
        cls.filter_record = cls.env['marketing.filter'].create(
            {'name': 'Filter 1',
             'model_id': cls.env.ref('base.model_res_partner').id,
             'model_name': 'res.partner',
             'domain': '["&", ("id", ">=", 1), ("id", "<=", 10)]'})
        cls.campaign = cls.env['marketing.campaign'].create(
            {'name': 'Campaign 1',
             'marketing_filter_id': cls.filter_record.id,
             'filter': '[]',
             'model_name': 'res.partner',
             'state': 'running'
             })

    def test_read_group_stage_ids(self):
        """
            Test the read_group_stage_ids method.

            Checks if the method returns the expected states.
        """
        _logger.info('Starts test_read_group_stage_ids')
        states = []
        domain = []
        order = []
        result = self.campaign.read_group_stage_ids(states, domain, order)
        expected_states = ['draft', 'running', 'stopped']
        self.assertEqual(result, expected_states)
        _logger.info('Ends test_read_group_stage_ids')

    def test_compute_filter(self):
        """
            Test the compute_filter method.

            Checks if the filter field is correctly computed.
        """
        _logger.info('Starts test_compute_filter')
        self.campaign._compute_filter()
        self.assertEqual(self.campaign.filter,
                         '["&", ("id", ">=", 1), ("id", "<=", 10)]')
        _logger.info('Ends test_compute_filter')

    def test_compute_marketing_filter_id(self):
        """
            Test the compute_marketing_filter_id method.

            Checks if the marketing_filter_id field is correctly computed.
        """
        _logger.info('Starts test_compute_marketing_filter_id')
        self.campaign._compute_marketing_filter_id()
        self.assertFalse(self.campaign.marketing_filter_id)
        _logger.info('Ends test_compute_marketing_filter_id')

    def test_action_start_campaign(self):
        """
            Test the action_start_campaign method.

            Checks if the campaign state is set to 'running' and participants
            are created.
            Also checks if an error is raised when trying to start a campaign
            with no activities.
        """
        _logger.info('Starts test_action_start_campaign')
        self.campaign.write({
            'activity_ids': [(0, 0, {'name': 'Activity 1'})]
        })
        self.campaign.action_start_campaign()
        self.assertEqual(self.campaign.state, 'running')
        participants = self.env['marketing.participant'].search(
            [('campaign_id', '=', self.campaign.id)])
        self.assertTrue(participants)
        campaign_with_no_activities = self.env['marketing.campaign'].create({
            'name': 'Test Campaign',
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        with self.assertRaises(UserError) as validation:
            campaign_with_no_activities.action_start_campaign()
        self.assertEqual(validation.exception.args[0],
                         'You must create an activity.')
        _logger.info('Ends test_action_start_campaign')

    def test_action_marketing_test(self):
        """
            Test the action_marketing_test method.

            Checks if the method returns the expected dictionary for the action
            window.
        """
        _logger.info('Starts test_action_marketing_test')
        result = self.campaign.action_marketing_test()
        expected_keys = {'type', 'name', 'view_mode', 'res_model', 'domain',
                         'context'}
        self.assertSetEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Participants')
        self.assertEqual(result['res_model'], 'marketing.participant')
        self.assertEqual(result['view_mode'], 'tree,form')
        self.assertEqual(result['domain'],
                         [('campaign_id', '=', self.campaign.id),
                          ('is_test_participant', '=', True)])
        self.assertEqual(result['context'], {'create': False})
        _logger.info('Ends test_action_marketing_test')

    def test_action_marketing_participant(self):
        """
            Test the action_marketing_participant method.

            Checks if the method returns the expected dictionary for the action
             window.
        """
        _logger.info('Starts test_action_marketing_participant')
        result = self.campaign.action_marketing_participant()
        expected_keys = {'type', 'name', 'view_mode', 'res_model', 'domain',
                         'context'}
        self.assertSetEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Participants')
        self.assertEqual(result['res_model'], 'marketing.participant')
        self.assertEqual(result['view_mode'], 'tree,form')
        self.assertEqual(result['domain'],
                         [('campaign_id', '=', self.campaign.id),
                          ('is_test_participant', '=', False)])
        self.assertEqual(result['context'], {'create': False})
        _logger.info('Ends test_action_marketing_participant')

    def test_action_marketing_templates(self):
        """
            Test the action_marketing_templates method.

            Checks if the method returns the expected dictionary for the action
            window.
        """
        _logger.info('Starts test_action_marketing_templates')
        result = self.campaign.action_marketing_templates()
        expected_keys = {'type', 'name', 'view_mode', 'res_model', 'domain','views',
                         'context'}
        self.assertSetEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Templates')
        self.assertEqual(result['res_model'], 'mailing.mailing')
        self.assertEqual(result['view_mode'], 'tree,form')
        self.assertEqual(result['domain'],
                         [('campaign_id', '=', self.campaign.id),
                          ('cy_automation_template', '=', True)])
        self.assertEqual(result['context'], {'create': False})
        _logger.info('Ends test_action_marketing_templates')

    def test_compute_test_count(self):
        """
            Test the compute_test_count method.

            Checks if the test_count field is correctly computed.
        """
        _logger.info('Starts test_compute_test_count')
        self.campaign._compute_test_count()
        self.assertEqual(self.campaign.test_count, 0)
        self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': True,
        })
        self.campaign._compute_test_count()
        self.assertEqual(self.campaign.test_count, 1)
        _logger.info('Ends test_compute_test_count')

    def test_compute_participant_count(self):
        """
            Test the compute_participant_count method.

            Checks if the participant_count field is correctly computed.
        """
        _logger.info('Starts test_compute_participant_count')
        self.campaign._compute_participant_count()
        self.assertEqual(self.campaign.participant_count, 0)
        self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False,
        })
        self.campaign._compute_participant_count()
        self.assertEqual(self.campaign.participant_count, 1)
        _logger.info('Ends test_compute_participant_count')

    def test_compute_activity_count(self):
        """
            Test the compute_activity_count method.

            Checks if the activity_count field is correctly computed.
        """
        _logger.info('Starts test_compute_activity_count')
        self.campaign._compute_activity_count()
        self.assertEqual(self.campaign.activity_count, 0)
        self.env['marketing.activity'].create({
            'campaign_id': self.campaign.id,
            'name': 'Activity 1'
        })
        self.campaign._compute_activity_count()
        self.assertEqual(self.campaign.activity_count, 1)
        _logger.info('Ends test_compute_activity_count')

    def test_compute_template_count(self):
        """
            Test the compute_template_count method.

            Checks if the template_count field is correctly computed.
        """
        _logger.info('Starts test_compute_template_count')
        self.campaign._compute_template_count()
        self.assertEqual(self.campaign.template_count, 0)
        _logger.info('Ends test_compute_template_count')

    def test_action_stop_campaign(self):
        """
            Test the action_stop_campaign method.

            Checks if the campaign state is set to 'stopped'.
        """
        _logger.info('Starts test_action_stop_campaign')
        self.campaign.action_stop_campaign()
        self.assertEqual(self.campaign.state, 'stopped')
        _logger.info('Ends test_action_stop_campaign')

    def test_convert_date_object(self):
        """
            Test the convert_date_object method.

            Checks if the test_date_started field of the sub-parent activity is
            correctly used to set the test_date_started field of the activity
            based on the activity_trigger.
        """
        _logger.info('Starts test_convert_date_object')
        activity = self.env['marketing.activity'].create({
            'name': 'Test Activity',
            'campaign_id': self.campaign.id,
            'activity_trigger_type': 'day',
            'activity_trigger': 3,
        })
        sub_parent_activity = self.env['marketing.activity'].create({
            'name': 'Sub-Parent Activity',
            'campaign_id': self.campaign.id,
            'test_date_started': fields.datetime.now(),
        })
        activity.sub_parent_activity_id = sub_parent_activity
        self.campaign.convert_date_object(activity)
        date = sub_parent_activity.test_date_started + timedelta(
            days=3)
        expected_date = date.replace(second=0, microsecond=0)
        self.assertEqual(activity.test_date_started, expected_date)
        _logger.info('Ends test_convert_date_object')

    def test_run_marketing_activities(self):
        """
            Test the run_marketing_activities method of the marketing.campaign
            model.

            This test sets up a marketing campaign with a server activity,
            creates a participant associated with the campaign, and an activity
            line in the 'schedule' state linked to the campaign's activity. The
            run_marketing_activities method is then called on the campaign,
            and it is asserted that the activity line state changes to
            'processed'.

            Returns:
                None
        """
        _logger.info('Starts test_run_marketing_activities')
        self.campaign.write({
            'activity_ids': [
                (0, 0, {'name': 'Activity 1',
                        'campaign_id': self.campaign.id,
                        'type': 'server',
                        'trigger_schedule_type': 'begin',
                        'test_date_started': fields.datetime.now().replace(
                            second=0, microsecond=0)})]
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': self.campaign.activity_ids.id,
            'participant_id': participant.id,
            'state': 'schedule'
        })
        self.campaign.run_marketing_activities()
        self.assertEqual(activity_line.state, 'processed')
        _logger.info('Ends test_run_marketing_activities')
