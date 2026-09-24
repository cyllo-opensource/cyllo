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

from odoo import fields
from odoo.tests.common import TransactionCase


class TestBudgetProject(TransactionCase):
    """Test methods of the Budget Project"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.analytic_plan01 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 01',
        })
        cls.analytic01 = cls.env['account.analytic.account'].create({
            'name': 'analytic 1',
            'plan_id': cls.analytic_plan01.id,
        })
        cls.budget05 = cls.env['budget.budget'].create({
            'name': 'Test Budget05',
            'period_type': False,
            'start_date': fields.Date.today() + timedelta(days=-5),
            'end_date': fields.Date.today() + timedelta(days=5),
            'state': 'draft',
        })
        cls.budget_line02 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 02',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget05.id,
            'start_date': cls.budget05.start_date,
            'end_date': cls.budget05.end_date,
            'budget_type': "earn",
            'planned_amount': 1100,
        })
        cls.partner01 = cls.env['res.partner'].create({
            'name': 'partner 01',
        })
        cls.project01 = cls.env['project.project'].create({
            'name': 'Project X',
        })
        cls.task1 = cls.env['project.task'].create({
            'name': 'Task One',
            'priority': '0',
            'state': '01_in_progress',
            'project_id': cls.project01.id,
        })
        cls.task2 = cls.env['project.task'].create({
            'name': 'Task Two',
            'priority': '1',
            'state': '1_done',
            'project_id': cls.project01.id,
        })
        cls.budget_project01 = cls.env['budget.project.wizard'].create({})
