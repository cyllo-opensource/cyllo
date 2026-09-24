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
from odoo import fields, models


class SaleOrderDiscount(models.TransientModel):
    """Inherited Sale Order discount model to add custom functionality
    for Discount """
    _inherit = 'sale.order.discount'

    apply_order_lines = fields.Boolean(
        string="Apply To OrderLines?",
        help="Allows to apply the discount on current order lines")

    def _create_discount_lines(self):
        """ Super the function to apply global discount in orderLines """
        if self.apply_order_lines:
            if self.discount_type == 'so_discount':
                discount_in_percentage = self.discount_percentage * 100
            else:
                if self.sale_order_id.amount_total > 0 and self.discount_amount > 0:
                    discount_in_percentage = self.discount_amount * 100 / self.sale_order_id.amount_total
                else:
                    discount_in_percentage = 0
            for line in self.sale_order_id.order_line:
                line.discount += discount_in_percentage
        else:
            return super()._create_discount_lines()
