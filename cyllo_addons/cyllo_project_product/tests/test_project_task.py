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
from odoo.exceptions import UserError, ValidationError
from .common import TestProjectProductBase


class TestProjectTask(TestProjectProductBase):
    """Tests for ProjectTask extensions added by cyllo_project_product."""

    # ------------------------------------------------------------------
    # Related fields propagation
    # ------------------------------------------------------------------

    def test_allow_task_products_relayed_from_project(self):
        """allow_task_products on task mirrors the project flag."""
        self.assertTrue(self.task.allow_task_products)

    def test_allow_extra_quotations_relayed_from_project(self):
        """allow_extra_quotations on task mirrors the project flag."""
        self.assertTrue(self.task.allow_extra_quotations)

    def test_related_flags_false_when_project_off(self):
        """Related flags are False when the project has them disabled."""
        task = self.env['project.task'].create({
            'name': 'Plain Task',
            'project_id': self.project_plain.id,
        })
        self.assertFalse(task.allow_task_products)
        self.assertFalse(task.allow_extra_quotations)

    # ------------------------------------------------------------------
    # _compute_extra_quotation_count
    # ------------------------------------------------------------------

    def test_extra_quotation_count_zero_initially(self):
        """Fresh task has zero extra quotations."""
        self.assertEqual(self.task.extra_quotation_count, 0)

    def test_extra_quotation_count_increments(self):
        """Count increments when extra quotations are created."""
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': True,
        })
        self.assertEqual(self.task.extra_quotation_count, 1)

    def test_extra_quotation_count_ignores_non_extra(self):
        """Regular sale orders linked to the task are not counted."""
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': False,
        })
        self.assertEqual(self.task.extra_quotation_count, 0)

    def test_extra_quotation_count_multiple(self):
        """Count reflects multiple extra quotations."""
        for _ in range(3):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'task_id': self.task.id,
                'is_task_extra_quotation': True,
            })
        self.assertEqual(self.task.extra_quotation_count, 3)

    # ------------------------------------------------------------------
    # _get_task_extra_quotations
    # ------------------------------------------------------------------

    def test_get_task_extra_quotations_returns_only_extras(self):
        """_get_task_extra_quotations only returns is_task_extra_quotation orders."""
        extra = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': True,
        })
        regular = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': False,
        })
        result = self.task._get_task_extra_quotations()
        self.assertIn(extra, result)
        self.assertNotIn(regular, result)

    # ------------------------------------------------------------------
    # action_view_task_products
    # ------------------------------------------------------------------

    def test_action_view_task_products_raises_without_sale_order(self):
        """ValidationError raised when no sale order is set on the task."""
        self.task_bare.related_sale_order_id = False
        with self.assertRaises(ValidationError):
            self.task_bare.action_view_task_products()

    def test_action_view_task_products_returns_action(self):
        """action_view_task_products returns a dict action when sale order is set."""
        result = self.task.action_view_task_products()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.act_window')

    # ------------------------------------------------------------------
    # _get_product_catalog_sale_order_values
    # ------------------------------------------------------------------

    def test_catalog_values_contain_partner(self):
        """Catalog values include the correct partner_id."""
        vals = self.task._get_product_catalog_sale_order_values(self.partner)
        self.assertEqual(vals['partner_id'], self.partner.id)

    def test_catalog_values_contain_task(self):
        """Catalog values include the task_id."""
        vals = self.task._get_product_catalog_sale_order_values(self.partner)
        self.assertEqual(vals['task_id'], self.task.id)

    def test_catalog_values_analytic_account_when_present(self):
        """Analytic account from project is included if available."""
        plan = self.env['account.analytic.plan'].create({'name': 'Test Plan'})
        analytic = self.env['account.analytic.account'].create({
            'name': 'Test Analytic',
            'plan_id': plan.id,
        })
        self.project.analytic_account_id = analytic
        vals = self.task._get_product_catalog_sale_order_values(self.partner)
        self.assertEqual(vals['analytic_account_id'], analytic.id)

    def test_catalog_values_no_analytic_account_when_missing(self):
        """analytic_account_id is False when the project has no analytic account."""
        self.project.analytic_account_id = False
        vals = self.task._get_product_catalog_sale_order_values(self.partner)
        self.assertFalse(vals['analytic_account_id'])

    # ------------------------------------------------------------------
    # action_task_new_quotation
    # ------------------------------------------------------------------

    def test_new_quotation_raises_without_partner(self):
        """UserError raised when neither task nor project has a partner."""
        project_no_partner = self.env['project.project'].create({
            'name': 'No Partner Project',
            'allow_extra_quotations': True,
        })
        task_no_partner = self.env['project.task'].create({
            'name': 'No Partner Task',
            'project_id': project_no_partner.id,
        })
        with self.assertRaises(UserError):
            task_no_partner.action_task_new_quotation()

    def test_new_quotation_uses_task_partner(self):
        """New quotation uses task's partner when available."""
        result = self.task.action_task_new_quotation()
        so = self.env['sale.order'].browse(result['res_id'])
        self.assertEqual(so.partner_id, self.partner)

    def test_new_quotation_uses_project_partner_fallback(self):
        """New quotation falls back to project partner when task has none."""
        self.task_bare.partner_id = False
        result = self.task_bare.action_task_new_quotation()
        so = self.env['sale.order'].browse(result['res_id'])
        self.assertEqual(so.partner_id, self.project.partner_id)

    def test_new_quotation_is_marked_as_extra(self):
        """Newly created quotation has is_task_extra_quotation=True."""
        result = self.task.action_task_new_quotation()
        so = self.env['sale.order'].browse(result['res_id'])
        self.assertTrue(so.is_task_extra_quotation)

    def test_new_quotation_linked_to_task(self):
        """Newly created quotation is linked back to the originating task."""
        result = self.task.action_task_new_quotation()
        so = self.env['sale.order'].browse(result['res_id'])
        self.assertEqual(so.task_id, self.task)

    def test_new_quotation_action_type(self):
        """action_task_new_quotation returns a window action for sale.order."""
        result = self.task.action_task_new_quotation()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'sale.order')

    # ------------------------------------------------------------------
    # action_view_extra_quotations
    # ------------------------------------------------------------------

    def test_view_extra_quotations_single_returns_form(self):
        """Viewing a single extra quotation opens form view directly."""
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': True,
        })
        result = self.task.action_view_extra_quotations()
        self.assertEqual(result['view_mode'], 'form')

    def test_view_extra_quotations_multiple_returns_tree(self):
        """Viewing multiple extra quotations opens tree/form view."""
        for _ in range(2):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'task_id': self.task.id,
                'is_task_extra_quotation': True,
            })
        result = self.task.action_view_extra_quotations()
        self.assertIn('tree', result['view_mode'])

    def test_view_extra_quotations_domain_filters_correctly(self):
        """Domain in the returned action restricts to this task's quotations."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'task_id': self.task.id,
            'is_task_extra_quotation': True,
        })
        result = self.task.action_view_extra_quotations()
        self.assertIn(so.id, result['domain'][0][2])
