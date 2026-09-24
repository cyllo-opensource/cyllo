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
from .common import TestProjectProductBase


class TestSaleOrder(TestProjectProductBase):
    """Tests for SaleOrder extensions added by cyllo_project_product."""

    # ------------------------------------------------------------------
    # Field defaults
    # ------------------------------------------------------------------

    def test_task_id_defaults_false(self):
        """task_id field defaults to False on a new sale order."""
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertFalse(so.task_id)

    def test_is_task_extra_quotation_defaults_false(self):
        """is_task_extra_quotation defaults to False."""
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertFalse(so.is_task_extra_quotation)

    # ------------------------------------------------------------------
    # _get_product_catalog_record_lines — task context
    # ------------------------------------------------------------------

    def _add_sol(self, order, product, qty, task=None):
        vals = {
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
        }
        if task:
            vals['project_task_product_id'] = task.id
        return self.env['sale.order.line'].create(vals)

    def test_catalog_lines_filtered_by_task(self):
        """_get_product_catalog_record_lines returns only lines for the given task."""
        task2 = self.env['project.task'].create({
            'name': 'Other Task',
            'project_id': self.project.id,
            'partner_id': self.partner.id,
        })
        line_task1 = self._add_sol(self.sale_order, self.product_a, 2, self.task)
        line_task2 = self._add_sol(self.sale_order, self.product_a, 5, task2)

        result = self.sale_order._get_product_catalog_record_lines(
            [self.product_a.id],
            project_task_id=self.task.id,
        )
        lines_for_task1 = result.get(self.product_a)
        self.assertIn(line_task1, lines_for_task1)
        self.assertNotIn(line_task2, lines_for_task1)

    def test_catalog_lines_fallback_to_super_without_task(self):
        """Without a task context, the parent implementation is called."""
        self._add_sol(self.sale_order, self.product_a, 3)
        result = self.sale_order._get_product_catalog_record_lines(
            [self.product_a.id],
        )
        # super() behaviour returns lines — just verify the product key is present
        self.assertIn(self.product_a, result)

    def test_catalog_lines_excludes_display_type_lines(self):
        """Section / note lines (display_type set) are excluded from catalog."""
        self._add_sol(self.sale_order, self.product_a, 1, self.task)
        # Add a section line
        self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'display_type': 'line_section',
            'name': 'A Section',
        })
        result = self.sale_order._get_product_catalog_record_lines(
            [self.product_a.id],
            project_task_id=self.task.id,
        )
        # Only product_a key present; section did not pollute the dict
        self.assertEqual(list(result.keys()), [self.product_a])

    # ------------------------------------------------------------------
    # _update_order_line_info — task context
    # ------------------------------------------------------------------

    def test_update_creates_line_for_task(self):
        """_update_order_line_info creates a new SOL tagged to the task."""
        self.sale_order._update_order_line_info(
            self.product_a.id, 4,
            project_task_id=self.task.id,
        )
        line = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_a
                      and l.project_task_product_id == self.task
        )
        self.assertTrue(line)
        self.assertEqual(line.product_uom_qty, 4)

    def test_update_updates_existing_line_for_task(self):
        """_update_order_line_info updates qty on an existing task line."""
        self._add_sol(self.sale_order, self.product_a, 2, self.task)
        self.sale_order._update_order_line_info(
            self.product_a.id, 7,
            project_task_id=self.task.id,
        )
        line = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_a
                      and l.project_task_product_id == self.task
        )
        self.assertEqual(line.product_uom_qty, 7)

    def test_update_deletes_line_when_qty_zero_draft(self):
        """Setting qty to 0 in draft state removes the line."""
        self._add_sol(self.sale_order, self.product_a, 3, self.task)
        self.assertEqual(self.sale_order.state, 'draft')
        self.sale_order._update_order_line_info(
            self.product_a.id, 0,
            project_task_id=self.task.id,
        )
        remaining = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_a
                      and l.project_task_product_id == self.task
        )
        self.assertFalse(remaining)

    def test_update_sets_qty_zero_when_confirmed_and_zero(self):
        """Setting qty to 0 on a confirmed order sets qty=0 instead of deleting."""
        self._add_sol(self.sale_order, self.product_a, 3, self.task)
        self.sale_order.action_confirm()
        self.sale_order._update_order_line_info(
            self.product_a.id, 0,
            project_task_id=self.task.id,
        )
        line = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_a
                      and l.project_task_product_id == self.task
        )
        self.assertTrue(line)
        self.assertEqual(line.product_uom_qty, 0)

    def test_update_returns_zero_when_no_existing_line_and_qty_zero(self):
        """Returns 0 when qty=0 and no existing line for the task."""
        result = self.sale_order._update_order_line_info(
            self.product_a.id, 0,
            project_task_id=self.task.id,
        )
        self.assertEqual(result, 0)

    def test_update_fallback_to_super_without_task(self):
        """Without task context, the parent _update_order_line_info is used."""
        # Should not raise; parent creates a regular line
        self.sale_order._update_order_line_info(self.product_b.id, 2)
        line = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_b
        )
        self.assertTrue(line)

    def test_update_context_task_id_used_when_kwarg_absent(self):
        """project_task_product_id from context is honoured when kwarg is absent."""
        so_ctx = self.sale_order.with_context(
            default_project_task_product_id=self.task.id
        )
        so_ctx._update_order_line_info(self.product_a.id, 5)
        line = self.sale_order.order_line.filtered(
            lambda l: l.product_id == self.product_a
                      and l.project_task_product_id == self.task
        )
        self.assertTrue(line)
