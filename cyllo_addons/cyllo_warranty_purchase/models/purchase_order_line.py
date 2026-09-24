# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    purchase_warranty_expiration_date = fields.Date(
        string="Purchase Warranty Expiration Date",
        compute='_compute_purchase_warranty_expiration_date',
        store=True,
    )
    warranty_extension_days = fields.Integer(
        string="Warranty Extension (Days)",
        default=0,
        help="Total number of days added across all warranty extensions.",
    )
    is_under_warranty = fields.Boolean(
        string="Is Under Warranty",
        compute='_compute_is_under_warranty',
        search='_search_is_under_warranty',
    )

    @api.depends(
        'state',
        'order_id.date_approve',
        'order_id.date_order',
        'product_id',
        'product_id.product_tmpl_id.warranty_period',
        'product_id.product_tmpl_id.warranty_period_unit',
        'product_id.product_tmpl_id.categ_id.warranty_period',
        'product_id.product_tmpl_id.categ_id.warranty_period_unit',
        'warranty_extension_days',
    )
    def _compute_purchase_warranty_expiration_date(self):
        for line in self:
            date = line.order_id.date_approve or line.order_id.date_order
            if not date or not line.product_id:
                line.purchase_warranty_expiration_date = False
                continue
            expiration_date = line.product_id._get_warranty_expiration_date(
                date
            )
            if expiration_date and line.warranty_extension_days > 0:
                expiration_date += relativedelta(
                    days=line.warranty_extension_days)
            line.purchase_warranty_expiration_date = expiration_date

    @api.depends('purchase_warranty_expiration_date')
    def _compute_is_under_warranty(self):
        today = fields.Date.context_today(self)
        for line in self:
            line.is_under_warranty = (
                    line.purchase_warranty_expiration_date and
                    line.purchase_warranty_expiration_date >= today
            )

    def _search_is_under_warranty(self, operator, value):
        today = fields.Date.context_today(self)
        if (operator == '=' and value is True) or (
                operator == '!=' and value is False):
            return [('purchase_warranty_expiration_date', '>=', today)]
        return [('purchase_warranty_expiration_date', '<', today)]
