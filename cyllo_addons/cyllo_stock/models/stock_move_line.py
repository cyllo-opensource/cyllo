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
import re
from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._update_sale_line_discounts()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['lot_id', 'quantity', 'state']):
            self._update_sale_line_discounts()
        return res

    def _update_sale_line_discounts(self):
        if 'sale_line_id' not in self.env['stock.move']._fields:
            return

        sale_lines = self.mapped('move_id.sale_line_id')

        for line in sale_lines:
            move_lines = line.move_ids.mapped('move_line_ids').filtered(
                lambda ml: ml.state != 'cancel'
            )
            discounts = move_lines.mapped('lot_id.default_discount')
            valid_discounts = [d for d in discounts if d]
            discount = (
                max(valid_discounts)
                if valid_discounts
                else (line.product_id.default_discount or 0.0)
            )

            line.discount = discount

            name = line.name or ''
            name = re.sub(r'\n\(Expiry Discount: \d+(?:\.\d+)?%\)', '', name)
            if discount:
                name += f"\n(Expiry Discount: {discount:g}%)"
            line.name = name
