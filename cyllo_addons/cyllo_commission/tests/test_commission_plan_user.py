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

from datetime import date
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCommissionPlanUser(TransactionCase):
    """

    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
        })
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.team = cls.env['crm.team'].create({'name': ' single plan Team'})
        cls.type= cls.env['commission.type'].create({'name': 'Test plan Type'})
        cls.plan = cls.env['commission.plan'].create({
            'name': 'Test plan',
            'team_id': cls.team.id,
            'type_id': cls.type.id,
            'commission_amount': 100,
            'currency_id': cls.currency.id,
        })

    def test_create(self):
        """
        Test that creating a commission.plan.user automatically
        links the plan to the user's plan_ids.
        """
        self.assertFalse(self.plan.user_ids)
        plan_user = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.assertIn(self.plan, self.user.plan_ids)
        self.assertEqual(plan_user.plan_id, self.plan)
        self.assertEqual(plan_user.user_id, self.user)

    def test_unlink(self):
        """
       unlink only removes plan from user if no other links exist.
        """
        link1 = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=7, day=31),
        })
        self.assertIn(self.plan, self.user.plan_ids)
        link2 = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date.today().replace(month=8, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        link1.unlink()
        self.assertIn(self.plan, self.user.plan_ids)
        link2.unlink()
        self.assertNotIn(self.plan, self.user.plan_ids)

    def test_check_dates(self):
        """
        Test _check_dates constraint for commission.plan.user
        """
        record = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
        })
        self.assertEqual(record.date_from, self.plan.date_from)
        self.assertEqual(record.date_to, self.plan.date_to)

        with self.assertRaises(ValidationError):
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date.today().replace(month=12, day=1),
                'date_to': date.today().replace(month=1, day=31),
            })
        with self.assertRaises(ValidationError):
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date.today().replace(month=1, day=1),
                'date_to': date.today().replace(month=12, day=31).replace(year=date.today().year + 1),  # after plan end
            })
        with self.assertRaises(ValidationError):
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date.today().replace(month=12, day=1),
                'date_to': date.today().replace(month=12, day=31).replace(year=date.today().year + 1),
            })

    def test_check_duplicate_user_with_overlap(self):
        """
        Test both:
        1. User's dates must fall within plan's date range.
        2. User cannot have overlapping periods in the same plan.
        """
        valid_record = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date.today().replace(2025, 1, 1),
            'date_to': date.today().replace(2025, 6, 30),
        })
        self.assertIn(valid_record, self.env['commission.plan.user'].search([
            ('user_id', '=', self.user.id),
            ('plan_id', '=', self.plan.id)
        ]))
        with self.assertRaises(ValidationError) as e1:
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date.today().replace(2024, 12, 1),
                'date_to': date.today().replace(2025, 6, 30),
            })
        self.assertIn("should comes in plans start date and end date", str(e1.exception))

        with self.assertRaises(ValidationError) as e2:
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date.today().replace(2025, 6, 1),
                'date_to': date.today().replace(2026, 1, 1),
            })
        self.assertIn("should comes in plans start date and end date", str(e2.exception))

        valid_record2 = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': self.plan.id,
            'date_from': date(2025, 7, 1),
            'date_to': date(2025, 12, 31),
        })
        self.assertIn(valid_record2, self.env['commission.plan.user'].search([
            ('user_id', '=', self.user.id),
            ('plan_id', '=', self.plan.id)
        ]))

        with self.assertRaises(ValidationError) as e3:
            self.env['commission.plan.user'].create({
                'user_id': self.user.id,
                'plan_id': self.plan.id,
                'date_from': date(2025, 6, 15),
                'date_to': date(2025, 8, 15),
            })
        self.assertIn("already has an overlapping period", str(e3.exception))

    def test_onchange_plan_id(self):
        """
        Test that onchange_plan_id sets date_from from the selected plan
        """
        onchange_team = self.env['crm.team'].create({'name': ' onchange plan Team'})

        onchange_type = self.env['commission.type'].create({'name': 'Test Onchange Plan type'})

        onchange_plan = self.env['commission.plan'].create({
            'name': 'Test Onchange Plan',
            'team_id': onchange_team.id,
            'type_id': onchange_type.id,
            'date_from': date.today().replace(month=1, day=1),
            'date_to': date.today().replace(month=12, day=31),
            'commission_amount': 100,
            'currency_id': self.currency.id,
        })
        plan_user = self.env['commission.plan.user'].create({
            'user_id': self.user.id,
            'plan_id': onchange_plan.id,
            'date_from': date.today(),
            'date_to': date.today()
        })
        plan_user._onchange_plan_id()
        self.assertEqual(plan_user.date_from, onchange_plan.date_from)


