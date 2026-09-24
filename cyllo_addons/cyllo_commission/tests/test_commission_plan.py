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

from datetime import date, timedelta
from psycopg2 import IntegrityError
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from unittest.mock import patch
from odoo.tools import mute_logger
from odoo.addons.mail.models.mail_template import MailTemplate



class TestCommissionPlan(TransactionCase):
    """
    Test suite for commission plan validation rules.

    This test ensures:
    - Commission plans cannot have overlapping date ranges.
    - Plans must have unique names.
    - Start dates must be before end dates.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        cls.team = cls.env['crm.team'].create({
            'name': 'Test Team',
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Test User 1',
            'login': 'test_user_1@example.com',
        })
        cls.type_record = cls.env['commission.type'].create({
            'name': 'target',
        })

        cls.plan = cls.env['commission.plan'].create({
            'name': 'Test Plan',
            'team_id': cls.team.id,
            'type_id': cls.type_record.id,
            'user_type': 'team',
            'user_ids': [(0, 0, {
                'user_id': cls.user.id,
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31),
            })],
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })

        cls.commission_type = cls.env['commission.type'].create({
            'name': 'Targets Secondary'
        })
        cls.user1 = cls.env['res.users'].create({
            'name': 'Sale User 1',
            'login': 'sales1',
            'email': 'sales1@example.com'
        })

        cls.user2 = cls.env['res.users'].create({
            'name': 'Sale User 2',
            'login': 'sales2',
            'email': 'sales2@example.com'
        })
        cls.env['crm.team.member'].create({
            'crm_team_id': cls.team.id,
            'user_id': cls.user1.id,
        })
        cls.env['crm.team.member'].create({
            'crm_team_id': cls.team.id,
            'user_id': cls.user2.id,
        })

        cls.CommissionPlan = cls.env['commission.plan']
        cls.TargetCommissionType = cls.env['commission.type']
        cls.TargetCommission = cls.env['commission.plan.target.commission']
        cls.type_record = cls.env['commission.type'].create({'name': 'Test Type'})
        cls.team = cls.env['crm.team'].create({'name': 'Test Sales Team'})
        cls.plan_model = cls.env['commission.plan']




    def test_unique_name_constrains(self):
        """It should not allow duplicate commission plan names."""
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['commission.plan'].create({
                    'name': 'Test Plan',
                    'team_id': self.team.id,
                    'user_ids': [(0, 0, {'user_id': self.user.id})],
                    'date_from': date.today(),
                    'date_to': date.today(),
                })

    def test_send_remainder_action(self):
        """It should set plan state to 'done' when date_to is in the past."""
        new_team = self.env['crm.team'].create({'name': 'Other Team'})

        old_plan = self.env['commission.plan'].create({
            'name': 'Past Plan',
            'team_id': new_team.id,
            'type_id': self.type_record.id,
            'user_ids': [(0, 0, {
                'user_id': self.user.id,
                'date_from': date.today() - timedelta(days=60),
                'date_to': date.today() - timedelta(days=1),
            })],
            'date_from': date.today() - timedelta(days=60),
            'date_to': date.today() - timedelta(days=1),
        })
        self.assertNotEqual(old_plan.state, 'done')
        old_plan._send_reminder_action()
        self.assertEqual(old_plan.state, 'done')

    def test_write_unlink_commission_report(self):
        """
        It should unlink commission report when commission amount is changed.
        """
        self.report = self.env['commission.report'].create({
            'plan_id': self.plan.id,
            'user_id': self.user.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })

        self.assertTrue(self.plan.commission_report_ids)
        self.plan.write({'commission_amount': 5000})
        self.assertFalse(self.plan.commission_report_ids)

    def test_compute_commission_report_ids(self):
        """"""
        self.plan.state = 'draft'
        self.plan._compute_commission_report_ids()
        self.assertFalse(self.plan.commission_report_ids)

        self.plan.state = 'approved'
        self.plan.user_type = 'team'

        with patch.object(type(self.plan), '_get_related_order_lines_and_orders', return_value={
            'orders': self.env['sale.order'],
            'order_lines': self.env['sale.order.line'],
        }):
            self.plan._compute_commission_report_ids()
            self.assertFalse(self.plan.commission_report_ids)
        self.salesperson = self.env['res.users'].create({
            'name': 'Salesperson User 1',
            'login': 'salesperson_user_1',
            'email': 'salesperson@example.com'
        })


        self.plan.write({
            'state': 'approved',
            'type': 'target',
            'user_type': 'person',
            'user_ids': [(5, 0, 0), (0, 0, {
                'user_id': self.salesperson.id,
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31),
            })],
        })

        # Create a matching sale order
        sale_order = self.env['sale.order'].create({
            'name': 'SO001',
            'team_id': self.team.id,
            'user_id': self.salesperson.id,
            'partner_id': self.user.partner_id.id,
            'state': 'sale',
        })

        report = self.env['commission.report'].create({
            'plan_id': self.plan.id,
            'user_id': self.salesperson.id,
            'order_id': sale_order.id,
        })
        self.plan._compute_commission_report_ids()
        self.assertTrue(self.plan.commission_report_ids)
        self.assertIn(report, self.plan.commission_report_ids)

        self.plan.state = 'approved'
        self.plan.team_id = self.team.id
        self.plan.user_type = 'team'
        duplicate_user = self.user
        self.plan.duplicate_user_ids = [(4, duplicate_user.id)]
        model_name = self.env['crm.team.member']._name
        CrmTeamMemberModel = self.env['crm.team.member'].__class__

        with patch.object(CrmTeamMemberModel, 'search', return_value=self.env['crm.team.member'].browse([])):
            self.plan._compute_commission_report_ids()
            self.assertFalse(self.plan.commission_report_ids)

        self.plan.state = 'approved'
        self.plan.team_id = self.team.id
        salesperson_user = self.env['res.users'].create({
            'name': 'New Salesperson User',
            'login': 'new_salesperson_user',
            'email': 'new_salesperson@example.com'
        })
        self.plan.user_ids = [(5, 0, 0), (0, 0, {
            'user_id': salesperson_user.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })]
        self.plan.user_type = 'person'

        salespeople = self.plan.user_ids.filtered(lambda p: p.user_id == salesperson_user)
        self.assertTrue(salespeople, "Salesperson entry must exist")

        period = self.env['commission.plan.frequency'].create({
            'name': 'Monthly',
            'plan_id': self.plan.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.plan.commission_frequency_ids = [(4, period.id)]

        target_commission = self.env['commission.plan.target.commission'].create({
            'plan_id': self.plan.id,
            'target_rate': 0.5,
            'amount': 5000.0,
        })
        self.plan.target_commission_ids = [(4, target_commission.id)]

        self.plan._compute_commission_report_ids()

        user_salesperson = self.plan.user_ids.filtered(lambda p: p.user_id == salesperson_user)
        self.assertEqual(user_salesperson.date_from, date.today().replace(month=1, day=1))
        self.assertEqual(user_salesperson.date_to, date.today().replace(month=12, day=31))
        self.plan.user_ids = [(5, 0, 0)]
        self.plan._compute_commission_report_ids()
        self.assertFalse(self.plan.user_ids)
        self.assertTrue(self.plan.commission_frequency_ids)
        self.assertTrue(self.plan.target_commission_ids)

    def test_compute_sales_people_user_ids(self):
        """Test that sales_people_user_ids is computed correctly
        both when assigned via team and via person assignment.
        """
        self.plan._compute_sales_people_user_ids()
        self.assertIn(self.user1, self.plan.sales_people_user_ids, "User1 should be in sales_people_user_ids")
        self.assertIn(self.user2, self.plan.sales_people_user_ids, "User2 should be in sales_people_user_ids")
        self.assertEqual(
            len(self.plan.sales_people_user_ids), 2)
        self.plan.user_ids = [(0, 0, {
            'user_id': self.user1.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })]
        self.plan.user_type = 'person'
        self.plan._compute_sales_people_user_ids()

        self.assertIn(self.user1, self.plan.sales_people_user_ids)
        self.assertEqual(
            len(self.plan.sales_people_user_ids),
            1)

    def test_compute_duplicate_user_ids(self):
        user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a',
        })
        user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b',
        })
        commission_type = self.env['commission.type'].create({
            'name': 'Test Type',
        })
        start_date = date.today().replace(month=1, day=1)
        end_date = date.today().replace(month=12, day=31)
        plan_a = self.env['commission.plan'].create({
            'name': 'Plan A',
            'user_type': 'person',
            'type': 'target',
            'type_id': commission_type.id,
            'type_ids': [(6, 0, [commission_type.id])],
            'user_ids': [(0, 0, {
                'user_id': user_a.id,
                'date_from': start_date,
                'date_to': end_date,
            })],
            'date_from': start_date,
            'date_to': end_date,
            'state': 'approved',
        })

        plan_b = self.env['commission.plan'].create({
            'name': 'Plan B',
            'user_type': 'person',
            'type': 'target',
            'type_id': commission_type.id,
            'type_ids': [(6, 0, [commission_type.id])],
            'user_ids': [(0, 0, {
                'user_id': user_b.id,
                'date_from': start_date,
                'date_to': end_date,
            })],
            'date_from': start_date,
            'date_to': end_date,
            'state': 'approved',
        })
        plan_b = plan_b.with_context(bypass_duplicate_check=True).sudo()
        plan_b.sales_people_user_ids = [(6, 0, [user_a.id, user_b.id])]
        plan_b._compute_duplicate_user_ids()
        self.assertIn(user_a, plan_b.duplicate_user_ids,
                      "User A should be marked as duplicate in Plan B")

    def test_bonus_commission_flag(self):
        """It should set is_bonus_commission = True when any target line has amount_rate > 1"""

        CommissionPlan = self.CommissionPlan
        TargetCommission = self.TargetCommission
        CommissionType = self.env['commission.type']

        plan_no_bonus = CommissionPlan.create({
            'name': 'No Bonus Plan',
            'team_id': self.team.id,
            'type_id': self.type_record.id,
            'state': 'approved',
            'user_type': 'team',
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.assertEqual(plan_no_bonus.ensure_one().id, plan_no_bonus.id)

        self.env['commission.plan.target.commission'].create({
            'plan_id': plan_no_bonus.id,
            'target_rate': 100,
            'amount_rate': 1.0,
        })

        plan_no_bonus._compute_is_bonus_commission()
        self.assertFalse(
            plan_no_bonus.is_bonus_commission,
            f"Expected no bonus, but got True. Fields = {plan_no_bonus.read()[0]}"
        )
        bonus_type = CommissionType.create({'name': 'Bonus Type'})[0]
        self.assertEqual(bonus_type.ensure_one().id, bonus_type.id)

        plan_with_bonus = CommissionPlan.create({
            'name': 'Bonus Plan',
            'team_id': self.team.id,
            'type_id': bonus_type.id,
            'state': 'approved',
            'user_type': 'team',
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.assertEqual(plan_with_bonus.ensure_one().id, plan_with_bonus.id)

        self.env['commission.plan.target.commission'].create({
            'plan_id': plan_with_bonus.id,
            'target_rate': 100,
            'amount_rate': 1.2,
        })

        plan_with_bonus._compute_is_bonus_commission()
        self.assertTrue(
            plan_with_bonus.is_bonus_commission,
            f"Expected bonus, got False. Fields = {plan_with_bonus.read()[0]}"
        )
        mixed_type = CommissionType.create({'name': 'Mixed Type'})[0]
        self.assertEqual(mixed_type.ensure_one().id, mixed_type.id)

        plan_mixed = CommissionPlan.create({
            'name': 'Mixed Plan',
            'team_id': self.team.id,
            'type_id': mixed_type.id,
            'state': 'approved',
            'user_type': 'team',
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.assertEqual(plan_mixed.ensure_one().id, plan_mixed.id)
        self.env['commission.plan.target.commission'].create({
            'plan_id': plan_mixed.id,
            'target_rate': 100,
            'amount_rate': 1.0,
        })
        self.env['commission.plan.target.commission'].create({
            'plan_id': plan_mixed.id,
            'target_rate': 100,
            'amount_rate': 1.5,
        })

        plan_mixed._compute_is_bonus_commission()
        self.assertTrue(
            plan_mixed.is_bonus_commission,
            f"Expected mixed plan bonus, got False. Fields = {plan_mixed.read()[0]}"
        )
    def test_compute_type_ids(self):
        """
        Test the computation and validation of `type_ids` in commission plans.

        """
        self.type_a = self.env['commission.type'].create({'name': 'Type A'})
        self.type_b = self.env['commission.type'].create({'name': 'Type B'})
        sales_team = self.env['crm.team'].create({'name': 'Sales Team A'})
        plan = self.env['commission.plan'].create({
            'name': 'Target Plan',
            'type': 'target',
            'type_id': self.type_a.id,
            'team_id': sales_team.id,
        })
        self.assertEqual(plan.type_ids, self.type_a)
        contribution_plan = self.env['commission.plan'].create({
            'name': 'Contribution Plan',
            'type': 'contribution',
            'contribution_ids': [(0, 0, {
                'type_id': self.type_b.id,
            })],
            'team_id': sales_team.id,
        })
        self.assertEqual(contribution_plan.type_ids, self.type_b)
        with self.assertRaises(UserError) as e:
            self.env['commission.plan'].create({
                'name': 'Contribution Plan Test',
                'type': 'contribution',
            })
        self.assertIn("Please add contribution type to the commission plan.", str(e.exception))

    def test_compute_total_commission(self):
        """
        Test the computation of `total_commission` in commission plans.

        """
        plan_type = self.env['commission.type'].create({
            'name': 'Target Type',
        })
        sales_team = self.env['crm.team'].create({'name': 'Sales Team B'})

        plan = self.env['commission.plan'].create({
            'name': 'Target A Plan',
            'type_id': plan_type.id,
            'type': 'target',
            'team_id': sales_team.id,
        })
        report_1 = self.env['commission.report'].create({
            'plan_id': plan.id,
            'commission_amount': 150.00,
        })
        report_2 = self.env['commission.report'].create({
            'plan_id': plan.id,
            'commission_amount': 200.00,
        })
        self.assertEqual(plan.total_commission, 350.00)
        report_2.unlink()
        self.assertEqual(plan.total_commission, 150.00)
        report_1.unlink()
        self.assertEqual(plan.total_commission, 0.00)

    def test_check_user_type(self):
        """
        Test the validation of `user_type` in commission plans.
        """
        self.sales_team = self.env['crm.team'].create({'name': 'Test Sales Team'})

        plan = self.env['commission.plan'].new({
            'name':'New Test Plan A',
            'user_type': 'team',
        })
        with self.assertRaises(UserError) as e:
            plan._check_user_type()

        plan = self.env['commission.plan'].new({
            'name': 'Team Plan',
            'user_type': 'team',
            'team_id': self.sales_team.id,
        })
        plan._check_user_type()
        self.assertFalse(plan.user_ids)
        plan = self.env['commission.plan'].new({
            'name': 'User Plan',
            'user_type': 'user',
        })
        with self.assertRaises(UserError) as e:
            plan._check_user_type()

    def test_check_type_id(self):
        """
        Test the _check_type_id constraint for commission plans:
        """
        type_a = self.env['commission.type'].create({'name': 'Type A'})
        type_b = self.env['commission.type'].create({'name': 'Type B'})
        target_plan_invalid = self.env['commission.plan'].new({
            'name': 'Invalid Target Plan',
            'type': 'target',
        })
        with self.assertRaises(UserError) as e1:
            target_plan_invalid._check_type_id()
        self.assertIn("Please add Type to the commission plan.", str(e1.exception))

        contribution_plan_invalid = self.env['commission.plan'].new({
            'name': 'Invalid Contribution Plan',
            'type': 'contribution',
        })
        with self.assertRaises(UserError) as e2:
            contribution_plan_invalid._check_type_id()
        self.assertIn("Please add contribution type to the commission plan.", str(e2.exception))

        target_plan_valid = self.env['commission.plan'].new({
            'name': 'Valid Target Plan',
            'type': 'target',
            'type_id': type_a.id,
        })
        target_plan_valid._check_type_id()

        contribution_plan_valid = self.env['commission.plan'].new({
            'name': 'Valid Contribution Plan',
            'type': 'contribution',
            'contribution_ids': [(0, 0, {
                'type_id': type_b.id,
            })],
        })
        contribution_plan_valid._check_type_id()
    def test_check_similar_commission(self):
        """
        Test that duplicate users or teams in the same plan type are not allowed.
        """
        plan_type = self.env['commission.type'].create({
            'name': 'Test Type',
        })
        sales_team = self.env['crm.team'].create({'name': 'Sales Team A'})
        user1 = self.env['res.users'].create({
            'name': 'User 1',
            'login': 'user_1',
        })
        user2 = self.env['res.users'].create({
            'name': 'User 2',
            'login': 'user_2',
        })
        plan_team_1 = self.env['commission.plan'].create({
            'name': 'Team Plan 1',
            'type': 'target',
            'type_id': plan_type.id,
            'user_type': 'team',
            'team_id': sales_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        with self.assertRaises(ValidationError) as e_team:
            plan_team_2 = self.env['commission.plan'].create({
                'name': 'Team Plan 2',
                'type': 'target',
                'type_id': plan_type.id,
                'user_type': 'team',
                'team_id': sales_team.id,
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31),
            })
        self.assertIn("Sales Team with  plan types Test Type already exists", str(e_team.exception))

        plan_user_1 = self.env['commission.plan'].create({
            'name': 'User Plan 1',
            'type': 'target',
            'type_id': plan_type.id,
            'user_type': 'person',
            'user_ids': [(0, 0, {
                'user_id': user1.id,
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31),
            })],
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        with self.assertRaises(ValidationError) as e_user:
            plan_user_2 = self.env['commission.plan'].create({
                'name': 'User Plan 2',
                'type': 'target',
                'type_id': plan_type.id,
                'user_type': 'person',
                'user_ids': [(0, 0, {
                    'user_id': user1.id,
                    'date_from': date.today().replace(month=1, day=1),
                    'date_to': date.today().replace(month=12, day=31),
                })],
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31),
            })
        self.assertIn("Sales people: User 1 already exists in the Plan Type: Test Type.",
                      str(e_user.exception))

    def test_onchange_fill_default_commissions(self):
        """
        Test the onchange method of commission plans to fill default commissions.
        """
        plan_type = self.env['commission.type'].create({'name': 'Test Type'})
        sales_team = self.env['crm.team'].create({'name': 'Sales Team A'})
        plan = self.env['commission.plan'].create({
            'name': 'Target Plan',
            'type': 'target',
            'commission_amount': 1000,
            'type_id': plan_type.id,
            'team_id': sales_team.id,
            'contribution_ids': [(0, 0, {'type_id': plan_type.id})],
            'type_ids': [],
        })
        plan._onchange_fill_default_commissions()
        self.assertTrue(plan.target_commission_ids)
        self.assertEqual(len(plan.contribution_ids), 0)
        plan = self.env['commission.plan'].new({
            'name': 'Contribution Plan',
            'type': 'contribution',
        })
        plan._onchange_fill_default_commissions()
        self.assertEqual(len(plan.target_commission_ids), 0)
        self.assertFalse(plan.type_ids)
    def test_onchange_commission_amount(self):
        """
        Test that changing `commission_amount` updates target commission lines correctly.
        """
        plan_type = self.env['commission.type'].create({'name': 'Test Type'})
        sales_team_B = self.env['crm.team'].create({'name': 'Sales Team B'})
        plan = self.env['commission.plan'].create({
            'name': 'Target Plan',
            'type': 'target',
            'commission_amount': 1000,
            'type_id': plan_type.id,
            'team_id': sales_team_B.id,
        })
        line1 = self.env['commission.plan.target.commission'].create({
            'plan_id': plan.id,
            'amount': 100,
            'amount_rate': 1.0,
        })
        line2 = self.env['commission.plan.target.commission'].create({
            'plan_id': plan.id,
            'amount': 50,
            'amount_rate': 0.5,
        })
        plan.commission_amount = 1500
        plan._onchange_commission_amount()
        self.assertEqual(line1.amount, 1500)
        self.assertNotEqual(line2.amount, 1500)

    def test_onchange_commission_frequency(self):
        """
        Test that commission frequencies are created according to frequency type.
        """
        new_pan_type = self.env['commission.type'].create({'name': 'New Type Plan A'})
        new_sales_team = self.env['crm.team'].create({'name':'New sales team'})
        plan = self.plan_model.create({
            'name': 'Frequency test Plan',
            'type_id': new_pan_type.id,
            'team_id': new_sales_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        plan.frequency = 'monthly'
        plan._onchange_commission_frequency()
        self.assertEqual(len(plan.commission_frequency_ids), 12)

        plan.frequency = 'quarterly'
        plan._onchange_commission_frequency()
        self.assertEqual(len(plan.commission_frequency_ids), 4)

        plan.frequency = 'yearly'
        plan._onchange_commission_frequency()
        self.assertEqual(len(plan.commission_frequency_ids), 1)

    def test_action_approve(self):
        """Test that action_approve sets state and triggers mail sending"""
        plan = self.env['commission.plan'].create({
            'name': 'New Test Plan',
            'type_id': self.type_record.id,
            'type': 'target',
            'team_id': self.team.id,
        })

        user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a@test.com',
            'email': 'user_a@test.com',
        })
        user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b@test.com',
            'email': 'user_b@test.com',
        })

        plan.write({
            'sales_people_user_ids': [(6, 0, [user_a.id, user_b.id])],
            'duplicate_user_ids': [(6, 0, [user_a.id])],
        })

        with patch.object(MailTemplate, 'send_mail', return_value=True) as mock_send:
            plan.action_approve()

            self.assertEqual(plan.state, 'approved', "Plan state should change to approved")
            self.assertGreaterEqual(mock_send.call_count, 2,
                                    "At least 2 emails should be sent (duplicate + welcome)")

    def test_action_reject(self):
        """
        Test that action_reject sets the state to 'rejected'
        """
        plan = self.env['commission.plan'].create({
            'name': 'New Test Reject Plan',
            'type_id': self.type_record.id,
            'type': 'target',
            'team_id': self.team.id,
            'state': 'draft'
        })
        self.assertEqual(plan.state, 'draft')
        plan.action_reject()
        self.assertEqual(plan.state,'rejected')

    def test_action_done(self):
        """
        Test that action_done sets the state to 'done'
        """
        plan = self.env['commission.plan'].create({
            'name': 'New Test Done Plan',
            'type_id': self.type_record.id,
            'type': 'target',
            'team_id': self.team.id,
            'state': 'draft'
        })
        self.assertEqual(plan.state, 'draft')
        plan.action_done()
        self.assertEqual(plan.state, 'done')

    def test_action_draft(self):
        """
        Test that action_draft sets the state to 'draft'
        """
        plan = self.env['commission.plan'].create({
            'name': 'New Test draft Plan',
            'type_id': self.type_record.id,
            'type': 'target',
            'team_id': self.team.id,
            'state': 'done'
        })
        self.assertEqual(plan.state,'done')
        plan.action_draft()
        self.assertEqual(plan.state, 'draft')

    def test_action_open_commission(self):
        """
        Test action_open_commission for target and contribution type
        """
        self.plan_target = self.env['commission.plan'].create({
            'name': "Target Plan",
            'type': 'target',
            'type_id': self.type_record.id,
            'team_id': self.team.id,
        })

        contribution_type = self.env['commission.type'].create({
            'name': 'Contribution Type',
            'type': 'crm',
        })
        contribution = self.env['commission.contribution'].create({
            'type_id': contribution_type.id,
        })

        self.plan_contribution = self.env['commission.plan'].create({
            'name': 'Contribution Plan',
            'type': 'contribution',
            'contribution_ids': [(6, 0, [contribution.id])],
            'team_id': self.team.id,
        })

        action = self.plan_target.action_open_commission()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'commission.report')
        self.assertIn((self.env.ref('cyllo_commission.view_target_commission_report_plan_tree').id,
                       'tree'), action['views'])
        self.assertIn((self.env.ref('cyllo_commission.view_target_commission_report_form').id,
                       'form'), action['views'])
        self.assertEqual(action['domain'], [('plan_id', '=', self.plan_target.id)])
        self.assertEqual(action['context']['default_plan_id'], self.plan_target.id)
        action = self.plan_contribution.action_open_commission()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'commission.report')
        self.assertIn((self.env.ref('cyllo_commission.view_contribution_commission_report_plan_tree').id,
                       'tree'), action['views'])
        self.assertIn((self.env.ref('cyllo_commission.view_contribution_commission_report_form').id,
                       'form'), action['views'])
        self.assertEqual(action['domain'], [('plan_id', '=', self.plan_contribution.id)])
        self.assertEqual(action['context']['default_plan_id'], self.plan_contribution.id)

    def test_prepare_default_commission_line(self):
        """
        Test the prepare_default_commission_lines method of a commission plan.
        This test verifies that the method returns a list of commission lines with
        the expected default values for target_rate, amount, amount_rate, and currency_id
        when given a specific amount.

        It checks that:
        - Three commission lines are returned.
        - The first line has zero rates and amount.
        - The second line has a target_rate and amount_rate of 0.5, with zero amount.
        - The third line has a target_rate and amount_rate of 1.0, with the full amount.
        - All lines use the company's currency.
        """
        self.plan = self.env['commission.plan'].create({
            'name': 'Test Prepare Plan',
            'type': 'target',
            'type_id': self.env['commission.type'].create({'name': 'Test Type'}).id,
            'team_id': self.env['crm.team'].create({'name': 'Test Team'}).id,
        })
        amount = 1000.00
        lines = self.plan.prepare_default_commission_lines(amount)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0][2]['target_rate'], 0.0)
        self.assertEqual(lines[0][2]['amount'], 0.0)
        self.assertEqual(lines[0][2]['amount_rate'], 0.0)
        self.assertEqual(lines[0][2]['currency_id'], self.env.company.currency_id.id)
        self.assertEqual(lines[1][2]['target_rate'], 0.5)
        self.assertEqual(lines[1][2]['amount'], 0.0)
        self.assertEqual(lines[1][2]['amount_rate'], 0.5)
        self.assertEqual(lines[1][2]['currency_id'], self.env.company.currency_id.id)
        self.assertEqual(lines[2][2]['target_rate'], 1.0)
        self.assertEqual(lines[2][2]['amount'], amount)
        self.assertEqual(lines[2][2]['amount_rate'], 1.0)
        self.assertEqual(lines[2][2]['currency_id'], self.env.company.currency_id.id)

    def test_prepare_monthly_frequencies(self):
        """

        """
        plan = self.env['commission.plan'].create({
            'name': 'Monthly Frequencies Plan',
            'type': 'target',
            'type_id': self.env['commission.type'].create({'name': 'Test Type'}).id,
            'team_id': self.env['crm.team'].create({'name': 'Test Team'}).id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=3, day=31),
        })
        frequencies = plan.prepare_monthly_frequencies()
        self.assertEqual(len(frequencies), 3)
        self.assertEqual(frequencies[0][2]['name'], 'Jan 2025')
        self.assertEqual(frequencies[0][2]['date_from'], date.today().replace(month=1, day=1))
        self.assertEqual(frequencies[0][2]['date_to'], date.today().replace(month=1, day=31))

        self.assertEqual(frequencies[1][2]['name'], 'Feb 2025')
        self.assertEqual(frequencies[1][2]['date_from'], date.today().replace(month=2, day=1))
        self.assertEqual(frequencies[1][2]['date_to'],date.today().replace(month=2, day=28))

        self.assertEqual(frequencies[2][2]['name'], 'Mar 2025')
        self.assertEqual(frequencies[2][2]['date_from'], date.today().replace(month=3, day=1))
        self.assertEqual(frequencies[2][2]['date_to'], date.today().replace(month=3, day=31))

    def test_prepare_quarterly_frequencies_full(self):
        """Test prepare_quarterly_frequencies for full year, partial quarters, and single-quarter plans"""

        year = date.today().year
        team = self.env['crm.team'].create({'name': 'Test Team'})
        commission_type = self.env['commission.type'].create({'name': 'Test Type'})

        plan_full_year = self.env['commission.plan'].create({
            'name': 'Full Year Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 12, 31),
        })
        frequencies_full = plan_full_year.prepare_quarterly_frequencies()
        self.assertEqual(len(frequencies_full), 4)
        self.assertEqual(frequencies_full[0][2]['name'], f'{year} Q1')
        self.assertEqual(frequencies_full[0][2]['date_from'], date(year, 1, 1))
        self.assertEqual(frequencies_full[0][2]['date_to'], date(year, 3, 31))
        self.assertEqual(frequencies_full[3][2]['name'], f'{year} Q4')
        self.assertEqual(frequencies_full[3][2]['date_from'], date(year, 10, 1))
        self.assertEqual(frequencies_full[3][2]['date_to'], date(year, 12, 31))

        team_partial = self.env['crm.team'].create({'name': 'Test partial Team'})
        plan_partial = self.env['commission.plan'].create({
            'name': 'Partial Quarter Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team_partial.id,
            'date_from': date(year, 2, 15),  # mid Q1
            'date_to': date(year, 5, 10),  # mid Q2
        })
        frequencies_partial = plan_partial.prepare_quarterly_frequencies()

        self.assertEqual(len(frequencies_partial), 2)
        self.assertEqual(frequencies_partial[0][2]['date_from'], date(year, 1, 1))
        self.assertEqual(frequencies_partial[0][2]['date_to'], date(year, 3, 31))
        self.assertEqual(frequencies_partial[1][2]['date_from'], date(year, 4, 1))
        self.assertEqual(frequencies_partial[1][2]['date_to'], date(year, 5, 10))

        team_single = self.env['crm.team'].create({'name': 'Test singlee Team'})

        plan_single = self.env['commission.plan'].create({
            'name': 'Single Quarter Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team_single.id,
            'date_from': date(year, 7, 10),
            'date_to': date(year, 9, 20),
        })
        frequencies_single = plan_single.prepare_quarterly_frequencies()
        self.assertEqual(len(frequencies_single), 1)
        self.assertEqual(frequencies_single[0][2]['name'], f'{year} Q3')
        self.assertEqual(frequencies_single[0][2]['date_from'], date(year, 7, 1))
        self.assertEqual(frequencies_single[0][2]['date_to'], date(year, 9, 20))

    def test_prepare_yearly_frequencies(self):
        """
        prepare yearly_frequency for single year
        """
        year = date.today().year
        team = self.env['crm.team'].create({'name': 'Test year Team'})
        commission_type = self.env['commission.type'].create({'name': 'Test Type'})

        plan = self.env['commission.plan'].create({
            'name': 'Yearly Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 12, 31),
        })
        frequencies_single = plan.prepare_yearly_frequencies()
        self.assertEqual(len(frequencies_single), 1)
        self.assertEqual(frequencies_single[0][2]['name'], str(year))
        self.assertEqual(frequencies_single[0][2]['date_from'], date(year, 1, 1))
        self.assertEqual(frequencies_single[0][2]['date_to'], date(year, 12, 31))

        team_mid = self.env['crm.team'].create({'name': 'Test year mid Team'})

        plan_mid = self.env['commission.plan'].create({
            'name': 'Mid year Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team_mid.id,
            'date_from': date(year, 3, 15),
            'date_to': date(year, 12, 30),
        })
        frequencies_mid = plan_mid.prepare_yearly_frequencies()
        self.assertEqual(frequencies_mid[0][2]['date_from'], date(year, 3, 15))
        self.assertEqual(frequencies_mid[0][2]['date_to'], date(year, 12, 30))

        team_end_mid = self.env['crm.team'].create({'name': 'Test year end mid Team'})

        plan_mid_end = self.env['commission.plan'].create({
            'name': 'End mid year Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team_end_mid.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 8, 20),
        })
        frequency_end_mid = plan_mid_end.prepare_yearly_frequencies()
        self.assertEqual(frequency_end_mid[0][2]['date_from'], date(year, 1, 1))
        self.assertEqual(frequency_end_mid[0][2]['date_to'], date(year, 8, 20))

        team_multi_year = self.env['crm.team'].create({'name': 'Test multi year Team'})
        plan_multi_year = self.env['commission.plan'].create({
            'name': 'Multi year Plan',
            'type': 'target',
            'type_id': commission_type.id,
            'team_id': team_multi_year.id,
            'date_from': date(year, 1, 1),
            'date_to': date(year+2, 12, 31),
        })
        frequency_multi = plan_multi_year.prepare_yearly_frequencies()
        self.assertEqual(len(frequency_multi), 3)
        self.assertEqual(frequency_multi[0][2]['date_from'], date(year, 1, 1))
        self.assertEqual(frequency_multi[-1][2]['date_to'], date(year+2, 12, 31))

    def test_prepare_commission_reports(self):
        """
        Test commission report preparation:
        - Creates target and contribution plans.
        - Ensures new reports are generated correctly.
        - Validates updates when a report already exists.
        """
        commission_team = self.env['crm.team'].create({'name':'commission '})
        plan_contribution_type = self.env['commission.type'].create({
            'name': 'Contribution Plan Type',
            'type': 'crm',
        })
        contribution = self.env['commission.contribution'].create({
            'type_id': plan_contribution_type.id,
        })
        plan_target = self.env['commission.plan'].create({
            'name': 'Target Plan',
            'type': 'target',
            'type_id': self.type_record.id,
            'team_id': commission_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        contribution_team = self.env['crm.team'].create({'name': 'Contribution Team'})
        plan_contribution = self.env['commission.plan'].create({
            'name': 'Contribution Plan',
            'type': 'contribution',
            'contribution_ids': [(6, 0, [contribution.id])],
            'type_id': self.type_record.id,
            'team_id': contribution_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        period = self.env['commission.plan.frequency'].create({
            'name': 'Q1 2025',
            'plan_id': plan_target.id,
            'amount': 1000.00,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),

        })
        order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'sample'}).id,
            'date_order': date.today().replace(month=1, day=1),
        })
        reports = []
        plan_target.prepare_commission_reports(
            plan=plan_target,
            user=self.user,
            period=period,
            total_amount=5000,
            target_rate=0.5,
            commission_amount=250,
            order=order,
            commission_reports=reports,
            source_orders=[order.id],
            source_orderlines=[]
        )
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][2]['target_amount'], 1000.0)
        reports = []
        plan_contribution.prepare_commission_reports(
            plan=plan_contribution,
            user=self.user,
            period=period,
            total_amount=7000.0,
            target_rate = 0.7,
            commission_amount = 500.0,
            order=order,
            commission_reports=reports,
            source_orders=[order.id],
            source_orderlines=[]
        )
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][2]['target_amount'], 0.0)
        existing_report = self.env['commission.report'].create({
            'plan_id': plan_target.id,
            'user_id': self.user.id,
            'period_id': period.id,
            'period_name': period.name,
            'achieve_amount': 1000,
            'commission_amount': 100,
            'achieve_rate': 0.1,
            'order_id': order.id,
            'order_ids': [(6, 0, [order.id])],
            'orderline_ids': [],
            'date': order.date_order,
            'target_amount': period.amount,
        })
        reports = []
        plan_target.prepare_commission_reports(
            plan=plan_target,
            user=self.user,
            period=period,
            total_amount=9999,
            target_rate=0.99,
            commission_amount=999,
            order=order,
            commission_reports=reports,
            source_orders=[order.id],
            source_orderlines=[]
        )
        self.assertEqual(existing_report.achieve_amount, 9999)
        self.assertEqual(len(reports), 0)

    def test_is_valid_commission_period(self):
        """
        Test _is_valid_commission_period for monthly, quarterly, yearly and invalid cases.
        """
        commission_team = self.env['crm.team'].create({'name': 'commission valid plan '})
        plan_valid_commission = self.env['commission.plan'].create({
            'name': 'Valid Commission Plan',
            'type': 'target',
            'type_id': self.type_record.id,
            'team_id': commission_team.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.today = date.today()
        to_date = date.today()
        res = plan_valid_commission._is_valid_commission_period('monthly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(month=5, day=31)
        res = plan_valid_commission._is_valid_commission_period('monthly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(month=12, day=31)
        res = plan_valid_commission._is_valid_commission_period('monthly', to_date, self.today)
        self.assertFalse(res)

        to_date = date.today().replace(year=2022 ,month=1, day=1)
        res = plan_valid_commission._is_valid_commission_period('monthly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(month=4, day=1)
        res = plan_valid_commission._is_valid_commission_period('quarterly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(month=7, day=31)
        res = plan_valid_commission._is_valid_commission_period('quarterly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(month=10, day=31)
        res = plan_valid_commission._is_valid_commission_period('quarterly', to_date, self.today)
        self.assertFalse(res)

        to_date = date.today().replace(year=2022, month=1, day=1)
        res = plan_valid_commission._is_valid_commission_period('yearly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(year=2025, month=1, day=1)
        res = plan_valid_commission._is_valid_commission_period('yearly', to_date, self.today)
        self.assertTrue(res)

        to_date = date.today().replace(year=2026, month=1, day=1)
        res = plan_valid_commission._is_valid_commission_period('yearly', to_date, self.today)
        self.assertFalse(res)

        to_date = date.today().replace(month=1, day=1)
        res = plan_valid_commission._is_valid_commission_period('invalid', to_date, self.today)
        self.assertFalse(res)

