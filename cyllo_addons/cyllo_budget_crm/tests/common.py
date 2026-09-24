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


class TestBudgetCrm(TransactionCase):
    """Test methods of the Budget CRM"""

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
        cls.user01 = cls.env['res.users'].create({
            'email': 'user01@gmail.com',
            'login': 'team0user',
            'name': 'User 01',

        })
        cls.sales_team01 = cls.env['crm.team'].create({
            'name': 'sales team 01'
        })

        cls.crm_member01 = cls.env['crm.team.member'].create({
            'user_id': cls.user01.id,
            'crm_team_id': cls.sales_team01.id,
            'start_date': fields.Date.today() + timedelta(days=-6),
            'end_date': fields.Date.today() + timedelta(days=6),
            'target_amount':1000,
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
            'crm_team_member_id': cls.crm_member01.id,
            'budget_id': cls.budget05.id,
            'start_date': cls.budget05.start_date,
            'end_date': cls.budget05.end_date,
            'budget_type': "earn",
            'planned_amount': 1100,
        })
        cls.partner01 = cls.env['res.partner'].create({
            'name': 'partner 01',
        })
        cls.product01 = cls.env['product.product'].create({
            'name': 'product 01'
        })
        cls.product02 = cls.env['product.product'].create({
            'name': 'product 02'
        })
        cls.account_move01 = cls.env['account.move'].create({
            'partner_id': cls.partner01.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': fields.date.today(),
            'amount_residual': 1000,
            'amount_total': 1000,
            'invoice_user_id':cls.user01.id,
            'line_ids': [fields.Command.create({
                'product_id': cls.product01.id,
                'amount_residual_currency': 1000,
            })],
        })
        cls.account_move01.action_post()
        cls.analytic_line01 = cls.env['account.analytic.line'].create({
            'name': 'analytic line 01',
            'date': cls.account_move01.invoice_date,
            'account_id': cls.analytic01.id,
            'move_line_id': cls.account_move01.invoice_line_ids.id,
            'amount': 500,
        })