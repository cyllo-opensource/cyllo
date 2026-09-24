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

class TestAccountAnalyticLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ensure we have a company
        cls.company = cls.env['res.company'].search([], limit=1)
        if not cls.company:
            cls.company = cls.env['res.company'].create({'name': 'Test Company'})

        # Create an active employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.company.id,
            'user_id': cls.env.user.id
        })

        # Create a project in the same company
        cls.project = cls.env['project.project'].search([], limit=1)
        if not cls.project:
            cls.project = cls.env['project.project'].create({
                'name': 'Test Project',
                'company_id': cls.company.id,
                'billing_type': 'non_billable'
            })

        # Create tasks
        cls.task1 = cls.env['project.task'].create({
            'name': 'Task 1',
            'project_id': cls.project.id
        })
        cls.task2 = cls.env['project.task'].create({
            'name': 'Task 2',
            'project_id': cls.project.id
        })

        # Create analytic account
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test Analytic Account',
            'company_id': cls.company.id,
            'plan_id': cls.env['account.analytic.plan'].search([], limit=1).id
        })

        # Create analytic line with employee
        cls.analytic_line = cls.env['account.analytic.line'].create({
            'name': 'Test Line',
            'account_id': cls.analytic_account.id,
            'project_id': cls.project.id,
            'task_id': cls.task1.id,
            'employee_id': cls.employee.id,  # <-- required
            'unit_amount': 2.0
        })
