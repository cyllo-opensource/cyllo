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
from collections import defaultdict
from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    task_id = fields.Many2one(
        'project.task',
        string="Source Task",
        copy=False,
    )
    is_task_extra_quotation = fields.Boolean(
        string="Task Extra Quotation",
        copy=False,
        help="Technical field to identify quotations created from the task New Quotation button.",
    )

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        """Retrieve sale order lines grouped by product for a specific task."""
        task_id = kwargs.get('project_task_id') or self.env.context.get('default_project_task_product_id')
        if task_id:
            grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
            for line in self.order_line:
                if line.display_type or line.product_id.id not in product_ids:
                    continue
                if line.project_task_product_id.id == task_id:
                    grouped_lines[line.product_id] |= line
            return grouped_lines
        return super()._get_product_catalog_record_lines(product_ids, **kwargs)

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """Create, update, or remove task-specific sale order lines."""
        task_id = kwargs.pop('project_task_id', None) or self.env.context.get('default_project_task_product_id')
        if task_id:
            sol = self.order_line.filtered(lambda line: line.product_id.id == product_id and line.project_task_product_id.id == task_id)
            if sol:
                if quantity != 0:
                    sol.product_uom_qty = quantity
                elif self.state in ['draft', 'sent']:
                    price_unit = self.pricelist_id._get_product_price(
                        product=sol.product_id,
                        quantity=1.0,
                        currency=self.currency_id,
                        date=self.date_order,
                        **kwargs,
                    )
                    sol.unlink()
                    return price_unit
                else:
                    sol.product_uom_qty = 0
                return sol.price_unit
            elif quantity > 0:
                sol = self.env['sale.order.line'].create({
                    'order_id': self.id,
                    'product_id': product_id,
                    'product_uom_qty': quantity,
                    'project_task_product_id': task_id,
                    'sequence': ((self.order_line and self.order_line[-1].sequence + 1) or 10),
                })
                return sol.price_unit
            return 0
        return super()._update_order_line_info(product_id, quantity, **kwargs)
