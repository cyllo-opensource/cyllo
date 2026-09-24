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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch
from odoo.fields import Datetime
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class TestCrmLead(TransactionCase):
    """
    Test suite for the `crm.lead` model with focus on notification logic,
    activities, and custom helper methods.

    This class validates:
    - Notification building and retrieval (`build_notifications`, `get_notifications`).
    - Lead marking behaviors (`mark_as_read`, `mark_as_unread`).
    - Exit criteria handling (`has_outstanding_exit_criteria`).
    - Integration with related models such as `mail.activity` for
      dismissible and exit-criteria-based tasks.
    - Correct return structures from helper methods.

    Each test case follows a step-by-step approach:
    1. Creates sample leads and activities.
    2. Executes the target method under different conditions.
    3. Asserts correctness of outcomes (boolean results, updated fields,
       returned dict structures).

    The goal is to ensure reliability of CRM lead notification and
    activity logic in real usage scenarios.

    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.cr.execute("ALTER TABLE res_company ALTER COLUMN security_lead SET DEFAULT 0.0")
        cls.env.cr.execute("ALTER TABLE project_project ALTER COLUMN billing_type SET DEFAULT 'not_billable'")
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.new_user = cls.env.user
        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.stage_with_activity = cls.env['crm.stage'].create({
            'name': 'Stage with activity',
            'sequence': 1,
        })
        cls.stage_without_activity = cls.env['crm.stage'].create({
            'name': 'Stage without activity',
            'sequence': 2,
        })
        cls.activity_type = cls.env['mail.activity.type'].create({
            'name': 'Follow-up Call',
        })
        cls.stage_activity = cls.env['crm.stage.activity'].create({
            'stage_id': cls.stage_with_activity.id,
            'activity_id': cls.activity_type.id,
        })
        cls.stage_1 = cls.env['crm.stage'].create({
            'name': 'Stage 1',
        })
        cls.stage_2 = cls.env['crm.stage'].create({
            'name': 'Stage 2',
        })
        cls.stage_3 = cls.env['crm.stage'].create({
            'name': 'Stage 3',
        })
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead',
            'stage_id': cls.stage_1.id,
        })
        cls.activity_type = cls.env['mail.activity.type'].create({
            'name': 'Follow-up Call',
        })
        cls.stage_activity = cls.env['crm.stage.activity'].create({
            'stage_id': cls.stage_2.id,
            'activity_id': cls.activity_type.id,
        })
        cls.stage_lead = cls.env['crm.stage'].create({
            'name': 'Lead Stage',
            'is_won': False,
            'type': 'lead',
        })
        cls.stage_opportunity = cls.env['crm.stage'].create({
            'name': 'Opportunity Stage',
            'is_won': False,
            'type': 'opportunity',
        })
        cls.satge_both = cls.env['crm.stage'].create({
            'name': 'Both Stage',
            'is_won': False,
            'type': 'both',
        })
        cls.stage_won = cls.env['crm.stage'].create({
            'name': 'Won Stage',
            'is_won': True,
            'type': 'lead',
        })
        cls.crm_lead = cls.env['crm.lead']
        cls.stage_new = cls.env['crm.stage'].create({
            'name': 'New Stage',
            'type': 'lead',
            'is_won': False,
        })
        cls.stage_qualified = cls.env['crm.stage'].create({
            'name': 'Qualified Stage',
            'type': 'opportunity',
        })
        cls.lead_stage_new = cls.env['crm.lead'].create({
            'name': 'Lead in New Stage',
            'stage_id': cls.stage_new.id,
        })
        cls.lead_reminder = cls.env['crm.lead'].create({
            'name': 'Lead Reminder',
            'stage_id': cls.stage_new.id,
            'company_id': cls.company.id,
            'user_id': cls.user.id,
            'last_stage_update_date': datetime.now() - timedelta(days=10),
        })
        cls.today = date.today()
        cls.seven_days_ago = cls.today - timedelta(days=7)
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.yesterday = cls.today - timedelta(days=1)
        cls.lead_1 = cls.env['crm.lead'].create({
            'name': 'Lead A',
            'expected_revenue': 10000,
            'stage_id': cls.stage_1.id,
        })
        cls.lead_2 = cls.env['crm.lead'].create({
            'name': 'Lead B',
            'expected_revenue': 20000,
            'stage_id': cls.stage_2.id,
        })
        cls.lead_3 = cls.env['crm.lead'].create({
            'name': 'Lead C',
            'expected_revenue': 30000,
            'stage_id': cls.stage_3.id,
        })
        cls.team = cls.env['crm.team'].create({
            'name': 'Test Team',
        })
        cls.admin_user = cls.env.ref('base.user_admin')
        today = datetime.now().date()
        cls.current_lead = cls.env['crm.lead'].create({
            'name': 'Current Lead',
            'team_id': cls.team.id,
            'user_id': cls.admin_user.id,
            'date_closed': today,
            'stage_id': cls.env.ref('crm.stage_lead1').id,
        })
        cls.previous_lead = cls.env['crm.lead'].create({
            'name': 'Previous Lead',
            'team_id': cls.team.id,
            'user_id': cls.admin_user.id,
            'date_closed': today - timedelta(days=30),
            'stage_id': cls.env.ref('crm.stage_lead2').id,
        })
        cls.two_months_ago = cls.today - relativedelta(months=2)
        cls.four_months_ago = cls.today - relativedelta(months=4)
        cls.lead_won = cls.crm_lead.create({
            'name': 'Won Lead',
            'expected_revenue': 1000,
            'stage_id': cls.stage_won.id,
            'date_closed': cls.two_months_ago,
        })
        cls.lead_created = cls.crm_lead.create({
            'name': 'Created Only',
            'expected_revenue': 0,
            'create_date': datetime.combine(cls.four_months_ago, datetime.min.time()),
        })
        cls.stage_lost = cls.env['crm.stage'].create({
            'name': 'Lost Stage'
        })
        cls.stage_new_lead = cls.env['crm.lead'].create({
            'name': 'New Lead Stage',
            'stage_id': cls.stage_new.id,
        })
        crm_lead_model_id = cls.env['ir.model']._get_id('crm.lead')

        cls.activity_today = cls.env['mail.activity'].create({
            'res_model_id': crm_lead_model_id,
            'res_model': 'crm.lead',
            'res_id': cls.stage_new_lead.id,
            'activity_type_id': cls.env.ref('mail.mail_activity_data_todo').id,
            'date_deadline': today,
            'user_id': cls.env.user.id
        })
        cls.activity_tomorrow = cls.env['mail.activity'].create({
            'res_model_id': crm_lead_model_id,
            'res_model': 'crm.lead',
            'res_id': cls.stage_new_lead.id,
            'activity_type_id': cls.env.ref('mail.mail_activity_data_todo').id,
            'date_deadline': today + timedelta(days=1),
            'user_id': cls.env.user.id
        })
        cls.sales_group = cls.env.ref("sales_team.group_sale_salesman")
        cls.user_1 = cls.env['res.users'].create({
            'name': 'Alice',
            'login': 'alice',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_1.write({'groups_id': [(4, cls.sales_group.id)]})
        cls.user_2 = cls.env['res.users'].create({
            'name': 'Bob',
            'login': 'bob',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_2.write({'groups_id': [(4, cls.sales_group.id)]})
        cls.won_stage = cls.env.ref('crm.stage_lead3')
        cls.won_stage.write({'is_won': True})
        cls.yesterday = cls.today - timedelta(days=1)
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.lead1 = cls.env['crm.lead'].create({
            'name': 'Lead 1',
            'user_id': cls.user_1.id,
            'stage_id': cls.won_stage.id,
            'expected_revenue': 1000,
            'date_closed': cls.today
        })

        cls.lead2 = cls.env['crm.lead'].create({
            'name': 'Lead 2',
            'user_id': cls.user_2.id,
            'stage_id': cls.won_stage.id,
            'expected_revenue': 2000,
            'date_closed': cls.today
        })
        cls.activity_model = cls.env['mail.activity']


    def test_create(self):
        """
        Test the `create` method of crm.lead under three different conditions:

        1. Lead created in a stage with exit criteria:
           - `exit_criteria_activity_name` should be set to activity type name.

        2. Lead created in a stage without exit criteria:
           - `exit_criteria_activity_name` should remain False.

        3. Lead created without any stage:
           - `exit_criteria_activity_name` should remain False.
        """
        lead = self.env['crm.lead'].create({
            'name': 'Lead With Activity',
            'stage_id': self.stage_with_activity.id,
        })
        self.assertEqual(lead.exit_criteria_activity_name, self.activity_type.name)

        lead_without_activity = self.env['crm.lead'].create({
            'name': 'Lead Without Activity',
            'stage_id': self.stage_without_activity.id,
        })
        self.assertFalse(lead_without_activity.exit_criteria_activity_name)

        lead_without_stage = self.env['crm.lead'].create({
            'name': 'Lead Without Stage',
        })
        self.assertFalse(lead_without_stage.exit_criteria_activity_name)

    def test_write(self):
        """
        Override the default `write` behavior for `crm.lead` to enforce
        stage exit criteria rules.

        Behavior:
        - If `stage_id` is in `values` and differs from the current stage:
            1. Prevent the stage change if `has_outstanding_exit_criteria()`
               returns True, raising a ValidationError.
            2. Otherwise, allow the stage change:
                - Search for exit criteria activities linked to the new stage.
                - Set `exit_criteria_activity_name` accordingly.
                - Trigger creation of new exit criteria activities via
                  `_create_exit_criteria_if_needed`.

        - If `stage_id` is not in `values` or does not change:
            - Perform a normal write without exit criteria checks.

        Returns:
            bool: Result of the super `write` call.
        """
        with patch.object(type(self.lead), 'has_outstanding_exit_criteria', return_value=True):
            with self.assertRaises(ValidationError):
                self.lead.write({'stage_id': self.stage_2.id})

        with patch.object(type(self.lead), 'has_outstanding_exit_criteria', return_value=False):
            self.lead.write({'stage_id': self.stage_2.id})
            self.assertEqual(self.lead.stage_id, self.stage_2)
            self.assertEqual(self.lead.exit_criteria_activity_name, self.activity_type.name)

        with patch.object(type(self.lead), 'has_outstanding_exit_criteria', return_value=False):
            self.lead.write({'stage_id': self.stage_3.id})
            self.assertEqual(self.lead.stage_id, self.stage_3)
            self.assertFalse(self.lead.exit_criteria_activity_name)

        old_stage = self.lead.stage_id
        self.lead.write({'name': 'Updated Lead'})
        self.assertEqual(self.lead.stage_id, old_stage)

        with patch.object(type(self.lead), 'has_outstanding_exit_criteria', side_effect=Exception("Should not be called")):
            self.lead.write({'stage_id': self.lead.stage_id.id})
            self.assertEqual(self.lead.stage_id, old_stage)

    def test_read_group_stage_ids(self):
        """
        Test the behavior of `_read_group_stage_ids` under different context conditions.

        This test ensures that all conditional branches inside the method are
        correctly applied when filtering CRM stages based on lead/opportunity type.

        Scenarios covered:
            1. Context contains `default_type='lead'`:
                - Includes stages of type 'lead' and 'both'
                - Excludes stages marked as won
            2. Context contains `default_type='opportunity'`:
                - Includes stages of type 'opportunity' and 'both'
                - Excludes stages of type 'lead' and won
            3. No `default_type` in context:
                - Includes all stage types ('lead', 'opportunity', 'both', and won)

        Assertions:
            - Correct inclusion/exclusion of stages depending on the scenario.
        """
        stages = self.env['crm.stage']
        result = self.crm_lead.with_context(default_type='lead')._read_group_stage_ids(stages, domain=[], order='id')
        self.assertIn(self.stage_lead, result)
        self.assertNotIn(self.stage_opportunity, result)
        self.assertIn(self.satge_both, result)
        self.assertNotIn(self.stage_won, result)

        stages = self.env['crm.stage']
        result = self.crm_lead.with_context(default_type='opportunity')._read_group_stage_ids(stages, domain=[], order='id')
        self.assertIn(self.stage_opportunity, result)
        self.assertNotIn(self.stage_lead, result)
        self.assertIn(self.satge_both, result)
        self.assertNotIn(self.stage_won, result)

        stages = self.env['crm.stage']
        result = self.crm_lead._read_group_stage_ids(stages, domain=[], order='id')
        self.assertIn(self.stage_lead, result)
        self.assertIn(self.stage_opportunity, result)
        self.assertIn(self.satge_both, result)
        self.assertIn(self.stage_won, result)

    def test_update_last_stage(self):
        """
        Test that last_stage_update_date updates correctly on stage change
        """
        self.assertEqual(self.lead_stage_new.last_stage_update_date.date(),
                         Datetime.now().date())
        self.lead_stage_new.stage_id = self.stage_qualified
        self.lead_stage_new.update_last_stage()
        self.assertEqual(
            self.lead_stage_new.last_stage_update_date.date(),
            Datetime.now().date())

    @patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail')
    def test_action_deal_reminder(self, mock_send_mail):
        """
        Test action_deal_reminder with different idle day scenarios.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'Cyllo_Crm.deal_reminder', True)

        self.env['ir.config_parameter'].sudo().set_param(
            'Cyllo_Crm.deal_reminder_days', '5')
        self.lead_reminder.last_stage_update_date = datetime.now() - timedelta(
            days=10)
        self.lead_reminder.stage_id.is_won = False

        self.lead_reminder.action_deal_reminder()

        self.assertEqual(self.lead_reminder.lead_idle_days, 5)
        mock_send_mail.assert_any_call(self.lead_reminder.id, force_send=True)

        mock_send_mail.reset_mock()

        self.env['ir.config_parameter'].sudo().set_param(
            'Cyllo_Crm.deal_reminder_days', '15')
        self.lead_reminder.last_stage_update_date = datetime.now() - timedelta(
            days=10)
        self.lead_reminder.action_deal_reminder()

        mock_send_mail.assert_not_called()

        self.lead_reminder.stage_id.is_won = True
        self.lead_reminder.action_deal_reminder()

        mock_send_mail.assert_not_called()

    def test_retrieve_crm_dashboard(self):
        """
        Test all conditions of retrieve_crm_dashboard
        """
        lead_no_activity = self.env['crm.lead'].create({
            'name': 'Lead Without Activity',
            'type': 'lead',
            'user_id': self.new_user.id,
        })
        lead_overdue = self.env['crm.lead'].create({
            'name': 'Lead Overdue',
            'type': 'lead',
            'user_id': self.new_user.id,
        })
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('crm.lead').id,
            'res_id': lead_overdue.id,
            'activity_type_id': self.activity_type.id,
            'date_deadline': self.yesterday,
            'state': 'planned'
        })
        lead_today = self.env['crm.lead'].create({
            'name': 'Lead Due Today',
            'type': 'lead',
            'user_id': self.new_user.id,
        })
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('crm.lead').id,
            'res_id': lead_today.id,
            'activity_type_id': self.activity_type.id,
            'date_deadline': self.today,
            'state': 'planned'
        })
        lead_idle = self.env['crm.lead'].create({
            'name': 'Lead Idle',
            'type': 'lead',
            'user_id': self.new_user.id,
        })
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('crm.lead').id,
            'res_id': lead_idle.id,
            'activity_type_id': self.activity_type.id,
            'date_deadline': self.seven_days_ago,
            'state': 'planned'
        })
        opp_future = self.env['crm.lead'].create({
            'name': 'Opportunity Future',
            'type': 'opportunity',
            'user_id': self.new_user.id,
        })
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('crm.lead').id,
            'res_id': opp_future.id,
            'activity_type_id': self.activity_type.id,
            'date_deadline': self.tomorrow,
            'state': 'planned'
        })
        dashboard_data = self.crm_lead.retrieve_crm_dashboard()
        self.assertGreaterEqual(dashboard_data['my_leads'], 4)
        self.assertGreaterEqual(dashboard_data['my_opportunities'], 12)
        self.assertGreaterEqual(dashboard_data['no_activity'], 1)
        self.assertGreaterEqual(dashboard_data['overdue'], 2)
        self.assertGreaterEqual(dashboard_data['due_today'], 1)
        self.assertGreaterEqual(dashboard_data['idle'], 0)
        self.assertGreaterEqual(dashboard_data['activity_today_o'], 1)

    def test_get_dashboard_data(self):
        """
        Test `get_dashboard_data` by passing a valid domain filter so that
        _get_metrics_data has proper start_date and end_date to work with.
        """
        today_str = self.today.strftime("%Y-%m-%d")
        seven_days_ago_str = self.seven_days_ago.strftime("%Y-%m-%d")

        domain = [
            ('create_date', '>=', seven_days_ago_str),
            ('create_date', '<=', today_str),
        ]
        dashboard_data = self.crm_lead.get_dashboard_data(domain=domain)
        self.assertIn('metrics', dashboard_data)
        self.assertIn('revenue_trend', dashboard_data)
        self.assertIn('pipeline', dashboard_data)
        self.assertIn('activities', dashboard_data)
        self.assertIn('top_performers', dashboard_data)

    def test_get_metrics_data(self):
        """
        Test `_get_metrics_data` across all supported dateranges.
        Ensures that the return dictionary always has the correct
        structure and numeric values.
        """

        today_str = self.today.strftime("%Y-%m-%d")
        seven_days_ago_str = self.seven_days_ago.strftime("%Y-%m-%d")

        domain = [
            ('date_closed', '>=', seven_days_ago_str),
            ('date_closed', '<=', today_str),
            ('team_id', '=', self.team.id),
            ('user_id', '=', self.admin_user.id),
        ]
        dateranges = ['this_month', 'this_year', 'this_week', 'this_quarter', 'today']
        for dr in dateranges:
            dashboard_metrics = self.crm_lead._get_metrics_data(domain=domain, daterange=dr)
            self.assertIsInstance(dashboard_metrics, dict)
            for key in ['total_revenue', 'active_leads', 'conversion_rate', 'deals_closed']:
                self.assertIn(key, dashboard_metrics)
            for key, value in dashboard_metrics.items():
                self.assertIsInstance(value, dict)
                self.assertIn('value', value)
                self.assertIn('change', value)
                self.assertIsInstance(value['value'], (int, float))
                self.assertIsInstance(value['change'], (int, float))

    def test_get_revenue_trend_data(self):
        """
        Test revenue and leads trend calculation over last 6 months
        """
        trend_data = self.crm_lead._get_revenue_trend_data(domain=None)
        self.assertEqual(len(trend_data), 6)
        for entry in trend_data:
            self.assertIn('month', entry)
            self.assertIn('revenue', entry)
            self.assertIn('leads', entry)
        expected_months = [
            (self.today.replace(day=1) - relativedelta(months=i)).strftime('%b')
            for i in range(5, -1, -1)
        ]
        actual_months = [entry['month'] for entry in trend_data]
        self.assertEqual(expected_months, actual_months)
        month_of_won_lead = self.two_months_ago.replace(day=1).strftime('%b')
        won_month_data = next(entry for entry in trend_data if entry['month'] == month_of_won_lead)
        self.assertEqual(won_month_data['revenue'], 1000)

        month_of_lead_created = self.four_months_ago.replace(day=1).strftime('%b')
        created_month_data = next(entry for entry in trend_data if entry['month'] == month_of_lead_created)
        self.assertGreaterEqual(created_month_data['leads'], 1)

    def test_get_pipeline_data(self):
        """
        Test the `_get_pipeline_data` method of `crm.lead`.

        Steps:
            1. Create four leads:
                - 2 in the "New Stage"
                - 1 in the "Won Stage"
                - 1 in the "Lost Stage"
            2. Call `_get_pipeline_data()` to generate stage distribution.
            3. Verify that:
                - "New Stage" has 50% (2 out of 4 leads)
                - "Won Stage" has 25% (1 out of 4 leads)
                - "Lost Stage" has 25% (1 out of 4 leads)
            4. Remove all leads and confirm `_get_pipeline_data()` returns an empty list.

        This ensures that:
            - The pipeline distribution is calculated correctly as percentages.
            - The method gracefully handles cases where no leads exist.
        """
        self.env['crm.lead'].search([]).unlink()

        lead1 = self.env['crm.lead'].create({'name': 'Lead 1',
                                             'stage_id': self.stage_new.id,
                                             'active': True})
        lead2 = self.env['crm.lead'].create({
            'name': 'Lead 2', 'stage_id': self.stage_new.id, 'active': True
        })
        lead3 = self.env['crm.lead'].create({
            'name': 'Lead 3', 'stage_id': self.stage_won.id, 'active': True
        })
        lead4 = self.env['crm.lead'].create({
            'name': 'Lead 4', 'stage_id': self.stage_lost.id, 'active': True
        })
        data = self.env['crm.lead']._get_pipeline_data()

        total = 4
        new_stage = next(d for d in data if d['stage'] == 'New Stage')
        self.assertEqual(new_stage['value'], round((2 / total) * 100, 1))
        won_stage = next(d for d in data if d['stage'] == 'Won Stage')
        self.assertEqual(won_stage['value'], round((1 / total) * 100, 1))
        lost_stage = next(d for d in data if d['stage'] == 'Lost Stage')
        self.assertEqual(lost_stage['value'], round((1 / total) * 100, 1))
        self.env['crm.lead'].search([]).unlink()
        data = self.env['crm.lead']._get_pipeline_data()
        self.assertEqual(data, [])

    def test_get_activities_data(self):
        """
         Test the `_get_activities_data` method of crm.lead.

        This test ensures that:
        - Activities linked to a lead are correctly retrieved when their
          deadline falls within the start_date and end_date provided in
          the domain.
        - The returned list of dictionaries contains the correct keys:
          'name' (activity type), 'date_deadline', and 'user_name'.
        - Both today's and tomorrow's activities that were created during
          setup are present in the result.

        Expected Result:
        The result should not be empty, and both `self.activity_today`
        and `self.activity_tomorrow` should be included in the output.
        """
        today = date.today()
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")

        domain = [
            ('id', '=', self.stage_new_lead.id),
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
        ]

        result = self.env['crm.lead']._get_activities_data(domain=domain)
        self.assertTrue(result)

        expected_today = {
            'name': self.activity_today.activity_type_id.name,
            'date_deadline': str(self.activity_today.date_deadline),
            'user_name': self.activity_today.user_id.name,
        }
        self.assertIn(expected_today, result)

        expected_tomorrow = {
            'name': self.activity_tomorrow.activity_type_id.name,
            'date_deadline': str(self.activity_tomorrow.date_deadline),
            'user_name': self.activity_tomorrow.user_id.name,
        }
        self.assertIn(expected_tomorrow, result)

    def test_get_top_performers_data(self):
        """
        Test that _get_top_performers_data returns the correct top performers
        within the date range and sorted by expected revenue.
        """
        lost_lead = self.env['crm.lead'].create({
            'name': 'Lost Lead',
            'user_id': self.user_1.id,
            'stage_id': self.env.ref('crm.stage_lead1').id,  # Not won
            'expected_revenue': 500,
            'date_closed': self.today
        })
        non_sales_user = self.env['res.users'].create({
            'name': 'Eve',
            'login': 'eve',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        non_sales_lead = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'user_id': non_sales_user.id,
            'stage_id': self.env.ref('crm.stage_lead2').id,
            'expected_revenue': 3000,
            'date_closed': self.today
        })
        non_sales_lead.stage_id.is_won = True
        test_lead_ids = [self.lead1.id, self.lead2.id]
        domain = [
            ('id', 'in', test_lead_ids),
            ('date_closed', '>=', str(self.yesterday)),
            ('date_closed', '<=', str(self.tomorrow)),
        ]
        result = self.env['crm.lead']._get_top_performers_data(domain=domain)
        self.assertTrue(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], self.user_2.name)
        self.assertEqual(result[0]['amount'], 2000)
        self.assertEqual(result[1]['name'], self.user_1.name)
        self.assertEqual(result[1]['amount'], 1000)
        self.assertEqual(result[0]['deals'], 1)
        self.assertEqual(result[1]['deals'], 1)

    def test_calculate_percentage_change(self):
        """
        Test _calculate_percentage_change method for all conditions
        """
        model = self.env['crm.lead']
        result = model._calculate_percentage_change(current= 50, previous= 0)
        self.assertEqual(result, 100)
        result = model._calculate_percentage_change(current= 0, previous= 0)
        self.assertEqual(result, 0)
        result = model._calculate_percentage_change(current= 150, previous= 100)
        self.assertEqual(result, 50)

    def test_dismiss_notification(self):
        """
        Test the dismiss_notification method:
        - Lead notifications should be marked as dismissed
        - Related mail.activities should also be dismissed
        """
        dismiss_user = self.env['res.users'].create({
            'name': 'Albin',
            'login': 'albin',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        sales_group = self.env.ref('sales_team.group_sale_salesman')
        dismiss_user.write({'groups_id': [(4, sales_group.id)]})
        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'user_id': dismiss_user.id,
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Lead 2',
            'user_id': dismiss_user.id,
        })
        crm_lead_model = self.env['ir.model']._get('crm.lead')

        activity_1 = self.env['mail.activity'].create({
            'res_model_id': crm_lead_model.id,
            'res_id': lead_1.id,
            'summary': 'Follow up Lead 1',
        })
        activity_2 = self.env['mail.activity'].create({
            'res_model_id': crm_lead_model.id,
            'res_id': lead_2.id,
            'summary': 'Follow up Lead 2',
        })
        lead_ids = [lead_1.id, lead_2.id]
        res = self.env['crm.lead'].dismiss_notification(lead_ids)
        self.assertTrue(res)
        self.assertTrue(lead_1.is_dismissed_notification)
        self.assertTrue(lead_2.is_dismissed_notification)
        self.assertTrue(activity_1.is_dismissed_notification)
        self.assertTrue(activity_2.is_dismissed_notification)

    def test_mark_as_read(self):
        """
        Test the `mark_as_read` method on crm.lead.

        This test ensures that:
        1. Leads are correctly marked as read when their IDs are passed.
        2. Related mail.activities linked to the leads are also marked as read.
        3. The return value contains:
           - 'updated': total number of leads updated.
           - 'sample_result': dictionary mapping lead IDs to their read status.
        4. All expected fields (`is_marked_as_read`) are set to True on both leads and activities.
        """
        lead_1 = self.env['crm.lead'].create({
            'name': 'lead 1'
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'lead 2'
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'lead 3'
        })
        crm_lead_model_id = self.env['ir.model']._get_id('crm.lead')

        activity_1 = self.activity_model.create({
            'res_model_id': crm_lead_model_id,
            'res_model': 'crm.lead',
            'res_id': lead_1.id,
            'summary': 'call lead 1'
        })
        activity_2 = self.activity_model.create({
            'res_model_id': crm_lead_model_id,
            'res_model': 'crm.lead',
            'res_id': lead_2.id,
            'summary': 'email lead 2'
        })
        lead_ids = [lead_1.id, lead_2.id, lead_3.id]
        result = self.env['crm.lead'].mark_as_read(lead_ids)
        self.assertEqual(result['updated'], 3)
        for lead_id in lead_ids:
            self.assertTrue(result['sample_result'][lead_id] or lead_id > 5)
        self.assertTrue(lead_1.is_marked_as_read)
        self.assertTrue(lead_2.is_marked_as_read)
        self.assertTrue(lead_3.is_marked_as_read)
        self.assertTrue(activity_1.is_marked_as_read)
        self.assertTrue(activity_2.is_marked_as_read)

    def test_get_notifications(self):
        """
         Test the get_notifications method:
        - Checks if lead creation generates notifications
        - Validates overdue and today's activity notifications
        - Validates high-value lead notifications
        - Simulates a search failure to ensure fallback returns []
        """
        new_lead = self.env['crm.lead'].create({
            'name': 'New Lead',
            'type': 'lead',
            'expected_revenue': 1000,
        })
        hig_value_lead = self.env['crm.lead'].create({
            'name': 'High Value Lead',
            'type': 'lead',
            'expected_revenue': 10000,
        })
        crm_lead_model_id = self.env['ir.model']._get_id('crm.lead')
        yesterday_activity = self.env['mail.activity'].create({
            'res_model_id': crm_lead_model_id,
            'res_id': new_lead.id,
            'summary': 'Call Customer',
            'date_deadline': date.today() - timedelta(days=1),
            'user_id': self.env.user.id,
        })
        today_activity = self.env['mail.activity'].create({
            'res_model_id': crm_lead_model_id,
            'res_id': new_lead.id,
            'summary': 'Send Email',
            'date_deadline': date.today(),
            'user_id': self.env.user.id,
        })
        notifications = self.env['crm.lead'].get_notifications()
        self.assertTrue(len(notifications) > 2)
        new_lead_notifi = any(
            "New Lead Created" in n['title'] for n in notifications)
        self.assertTrue(new_lead_notifi, "Missing: New Lead notification")

        overdue_notifi = any(
            "Activity Overdue" in n['title'] for n in notifications)
        self.assertTrue(overdue_notifi,
                        "Missing: Overdue Activity notification")

        today_notifi = any(
            "Activity Due Today" in n['title'] for n in notifications)
        self.assertTrue(today_notifi, "Missing: Today Activity "
                                      "notification")

        high_value_notifi = any(
            "High Value Lead" in n['title'] for n in notifications)
        self.assertTrue(high_value_notifi,
                        "Missing: High Value Lead notification")
        with patch('odoo.models.BaseModel.search',
                   side_effect=Exception('Fake search error')):
            result = self.env['crm.lead'].get_notifications()
            self.assertEqual(result, [])

    def test_build_notifications(self):
        """
        Test that build_notifications constructs a notification dictionary
        with valid fields for a crm.lead record.
        Ensures create_date is flushed before calling the method.
        """
        build_lead = self.env['crm.lead'].create({
            'name': 'Build Lead',
            'partner_name': 'test partner',
            'expected_revenue': 5000,
        })
        self.env.cr.flush()
        build_lead.invalidate_recordset()
        notfi = self.env['crm.lead'].build_notifications(
            prefix="lead_",
            rec=build_lead,
            title='High Value Lead',
            message="Lead with high revenue detected",
            ntype="warning",
            priority="high"
        )
        self.assertIn("id", notfi)
        self.assertEqual(notfi['id'], f"lead_{build_lead.id}")
        self.assertEqual(notfi['title'], "High Value Lead")
        self.assertEqual(notfi['message'], "Lead with high "
                                           "revenue detected")
        self.assertEqual(notfi['type'], "warning")
        self.assertEqual(notfi['priority'], "high")
        self.assertEqual(notfi['lead_id'], build_lead.id)
        self.assertEqual(notfi['lead_company'], "test partner")
        self.assertEqual(notfi['lead_stage'], "New")
        self.assertEqual(notfi['lead_expected_revenue'], "$5,000")

        lead_no_values = self.env['crm.lead'].create({
            'name': 'Lead with no revenue'
        })
        notif = lead_no_values.build_notifications(
            prefix="test_",
            rec=lead_no_values,
            title="Basic Lead",
            message="Lead without extra values",
            ntype="info",
            priority="low"
        )
        self.assertEqual(notif['lead_company'], "")
        self.assertEqual(notif['lead_stage'], "New")
        self.assertEqual(notif['lead_expected_revenue'], "")

    def test_has_outstanding_exit_criteria(self):
        """
        Test the behavior of `has_outstanding_exit_criteria` method.

        This test ensures that:
        1. A newly created lead without any activities
           should return False (no exit criteria outstanding).
        2. After adding a mail.activity linked to the lead
           with `is_exit_criteria=True`, the method should
           return True (indicating exit criteria is outstanding).
        """
        exit_lead = self.env['crm.lead'].create({
            'name': 'Exit Lead',
        })
        result = exit_lead.has_outstanding_exit_criteria()
        self.assertFalse(result)
        crm_lead_model_id = self.env['ir.model']._get_id('crm.lead')
        self.env['mail.activity'].create({
            'res_model': 'crm.lead',
            'res_model_id': crm_lead_model_id,
            'res_id': exit_lead.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': 'Exit Criteria Task',
            'is_exit_criteria': True,
        })
        result = exit_lead.has_outstanding_exit_criteria()
        self.assertTrue(result)
