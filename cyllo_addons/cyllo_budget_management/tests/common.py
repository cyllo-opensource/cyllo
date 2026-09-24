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
from datetime import timedelta
from odoo import fields


class TestBudgetManagement(TransactionCase):
    """Test methods of the Budget"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.budget01 = cls.env['budget.budget'].create({
            'name': 'Test Budget01',
            'period_type': 'day',
            'start_date': '2024-04-29',
            'end_date': '2024-05-01',
            'state': 'draft'
        })
        cls.budget02 = cls.env['budget.budget'].create({
            'name': 'Test Budget01',
            'period_type': 'week',
            'start_date': '2024-04-29',
            'end_date': '2024-05-01',
            'state': 'draft'
        })
        cls.budget03 = cls.env['budget.budget'].create({
            'name': 'Test Budget01',
            'period_type': 'month',
            'start_date': '2024-04-29',
            'end_date': '2024-05-01',
            'state': 'draft'
        })
        cls.budget04 = cls.env['budget.budget'].create({
            'name': 'Test Budget01',
            'period_type': 'year',
            'start_date': '2024-04-29',
            'end_date': '2024-05-01',
            'state': 'draft'
        })
        cls.analytic_plan01 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 01',
        })
        cls.analytic_plan02 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 02',
        })
        cls.analytic01 = cls.env['account.analytic.account'].create({
            'name': 'analytic 1',
            'plan_id': cls.analytic_plan01.id,
        })
        cls.account01 = cls.env['account.account'].create({
            'name': 'account 1',
            'code': 'X2020',
            'account_type': 'income',
        })
        cls.analytic02 = cls.env['account.analytic.account'].create({
            'name': 'analytic 2',
            'plan_id': cls.analytic_plan01.id,
            'analytic_account_id': cls.analytic01.id,
        })
        cls.analytic03 = cls.env['account.analytic.account'].create({
            'name': 'analytic 3',
            'plan_id': cls.analytic_plan01.id,
            'analytic_account_id': cls.analytic01.id,
        })
        cls.analytic04 = cls.env['account.analytic.account'].create({
            'name': 'analytic 4',
            'plan_id': cls.analytic_plan01.id,
        })
        cls.analytic05 = cls.env['account.analytic.account'].create({
            'name': 'analytic 5',
            'plan_id': cls.analytic_plan02.id,
            'analytic_account_id': cls.analytic01.id,
        })
        cls.budget_line01 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 01',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget01.id,
            'start_date': cls.budget01.start_date,
            'end_date': cls.budget01.end_date,
            'budget_type': "earn",
            'planned_amount': 1000,
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
        cls.budget_line07 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 07',
            'account_ids': [fields.Command.link(cls.account01.id)],
            'budget_id': cls.budget05.id,
            'start_date': cls.budget05.start_date,
            'end_date': cls.budget05.end_date,
            'budget_type': "earn",
            'planned_amount': 5000,
        })
        cls.budget06 = cls.env['budget.budget'].create({
            'name': 'Test Budget06',
            'period_type': False,
            'start_date': fields.Date.today() + timedelta(days=-10),
            'end_date': fields.Date.today(),
            'state': 'draft',

        })
        cls.budget_line03 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 03',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget06.id,
            'start_date': cls.budget06.start_date,
            'end_date': cls.budget06.end_date,
            'budget_type': "earn",
            'planned_amount': 1100,
        })
        cls.budget07 = cls.env['budget.budget'].create({
            'name': 'Test Budget07',
            'period_type': False,
            'start_date': fields.Date.today() + timedelta(days=1),
            'end_date': fields.Date.today() + timedelta(days=10),
            'state': 'draft',

        })
        cls.budget09 = cls.env['budget.budget'].create({
            'name': 'Test Budget09',
            'period_type': False,
            'start_date': fields.Date.today() + timedelta(days=-5),
            'end_date': fields.Date.today() + timedelta(days=5),
            'state': 'draft',

        })
        cls.budget_line091 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 91',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget09.id,
            'start_date': cls.budget09.start_date,
            'end_date': cls.budget09.end_date,
            'budget_type': "earn",
            'planned_amount': 500,
        })
        cls.budget_line092 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 92',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget09.id,
            'start_date': cls.budget09.start_date,
            'end_date': cls.budget09.end_date,
            'budget_type': "spend",
            'planned_amount': 1000,
        })
        cls.budget_line093 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 93',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget09.id,
            'start_date': cls.budget09.start_date,
            'end_date': cls.budget09.end_date,
            'budget_type': "spend",
            'planned_amount': 500,
        })
        cls.budget_line094 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 94',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget09.id,
            'start_date': cls.budget09.start_date,
            'end_date': cls.budget09.end_date,
            'budget_type': "earn",
            'planned_amount': 1000,
        })
        cls.budget_line04 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 04',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget07.id,
            'start_date': cls.budget07.start_date,
            'end_date': cls.budget07.end_date,
            'budget_type': "earn",
            'planned_amount': 1100,
        })
        cls.budget01.write({
            'budget_line_ids': [fields.Command.link(cls.budget_line01.id)],
        })
        cls.budget05.write({
            'budget_line_ids': [fields.Command.link(cls.budget_line02.id)],
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
            'invoice_date': '2024-05-01',
            'amount_residual': 1000,
            'amount_total': 1000,
            'line_ids': [fields.Command.create({
                'product_id': cls.product01.id,
                'amount_residual_currency': 100,
                'analytic_distribution': {
                    cls.analytic01.id: 100
                }
            })],
        })
        cls.account_move02 = cls.env['account.move'].create({
            'partner_id': cls.partner01.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': fields.date.today(),
            'amount_residual': 1000,
            'amount_total': 1000,
            'line_ids': [fields.Command.create({
                'product_id': cls.product01.id,
                'amount_residual_currency': 100,
                'analytic_distribution': {
                    cls.analytic01.id: 100
                }
            })],
        })
        cls.analytic_line01 = cls.env['account.analytic.line'].create({
            'name': 'analytic line 01',
            'date': cls.account_move01.invoice_date,
            'account_id': cls.analytic01.id,
            'move_line_id': cls.account_move01.invoice_line_ids.id,
            'amount': 500,
        })
        cls.analytic_line02 = cls.env['account.analytic.line'].create({
            'name': 'analytic line 02',
            'date': cls.account_move02.invoice_date,
            'account_id': cls.analytic01.id,
            'move_line_id': cls.account_move02.invoice_line_ids.id,
            'amount': 600,
        })
        cls.budget_line_conf01 = cls.env['budget.lines.configuration'].create({
            'budget_line_id': cls.budget_line02.id,
            'analytic_account_id': cls.analytic02.id,
        })
        cls.budget_line_conf02 = cls.env['budget.lines.configuration'].create({
            'budget_line_id': cls.budget_line02.id,
            'analytic_account_id': cls.analytic03.id,
        })
        cls.budget_line11 = cls.env['budget.lines'].create({
            'display_name': 'Budget Line 11',
            'analytic_account_id': cls.analytic01.id,
            'budget_id': cls.budget05.id,
            'start_date': cls.budget05.start_date,
            'end_date': cls.budget05.end_date,
            'budget_type': "spend",
            'planned_amount': -1000,
        })
        cls.budget_line_conf03 = cls.env['budget.lines.configuration'].create({
            'budget_line_id': cls.budget_line11.id,
            'analytic_account_id': cls.analytic03.id,
        })
        cls.debt_01 = cls.env['debt.management'].create({
            'display_name': 'Debt 01',
            'debt_type': 'lend',
            'person_id': cls.partner01.id,
            'amount': 1000,
            'date': fields.date.today(),
            'payback_date': fields.date.today() + timedelta(7),
            'state': 'lend_borrow'
        })
        cls.debt_02 = cls.env['debt.management'].create({
            'display_name': 'Debt 02',
            'debt_type': 'borrow',
            'person_id': cls.partner01.id,
            'amount': 400,
            'date': fields.date.today(),
            'payback_date': fields.date.today() + timedelta(7),
            'state': 'draft'
        })
        cls.debt_03 = cls.env['debt.management'].create({
            'display_name': 'Debt 03',
            'debt_type': 'lend',
            'person_id': cls.partner01.id,
            'amount': 500,
            'date': fields.date.today(),
            'payback_period': 'week',
            'payback_date': fields.date.today() + timedelta(7),
            'state': 'draft'
        })
        cls.debt_04 = cls.env['debt.management'].create({
            'display_name': 'Debt 04',
            'debt_type': 'lend',
            'person_id': cls.partner01.id,
            'amount': 500,
            'date': fields.date.today(),
            'payback_period': 'month',
            'payback_date': fields.date.today(),
            'state': 'draft'
        })
        cls.payment01 = cls.env['account.payment'].create({
            'amount': 1000,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': cls.partner01.id,
            'ref': cls.debt_01.display_name,
        })
