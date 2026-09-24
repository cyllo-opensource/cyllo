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


class TestSaleOrderLine(TestProjectProductBase):
    """Tests for SaleOrderLine extensions added by cyllo_project_product."""

    # ------------------------------------------------------------------
    # Field defaults
    # ------------------------------------------------------------------

    def test_project_task_product_id_defaults_false(self):
        """project_task_product_id defaults to False on a new line."""
        line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
        })
        self.assertFalse(line.project_task_product_id)

    # ------------------------------------------------------------------
    # Field assignment
    # ------------------------------------------------------------------

    def test_project_task_product_id_can_be_set(self):
        """project_task_product_id links correctly to a task."""
        line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 2,
            'project_task_product_id': self.task.id,
        })
        self.assertEqual(line.project_task_product_id, self.task)

    def test_project_task_product_id_can_be_cleared(self):
        """project_task_product_id can be unset after being assigned."""
        line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 2,
            'project_task_product_id': self.task.id,
        })
        line.project_task_product_id = False
        self.assertFalse(line.project_task_product_id)

    def test_multiple_lines_different_tasks_same_product(self):
        """Two lines with the same product can reference different tasks."""
        task2 = self.env['project.task'].create({
            'name': 'Task Two',
            'project_id': self.project.id,
        })
        line1 = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'project_task_product_id': self.task.id,
        })
        line2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 3,
            'project_task_product_id': task2.id,
        })
        self.assertEqual(line1.project_task_product_id, self.task)
        self.assertEqual(line2.project_task_product_id, task2)

    def test_line_without_task_coexists_with_task_line(self):
        """A regular line (no task) and a task line for the same product coexist."""
        line_regular = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 5,
        })
        line_task = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 2,
            'project_task_product_id': self.task.id,
        })
        self.assertFalse(line_regular.project_task_product_id)
        self.assertEqual(line_task.project_task_product_id, self.task)
