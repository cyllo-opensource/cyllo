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

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    warranty_period = fields.Integer(
        string="Warranty Period",
        default=0)
    warranty_period_unit = fields.Selection(
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('year', 'Years'),
        ],
        string="Warranty Unit",
        default='month'
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_period = fields.Integer(
        string="Warranty Period",
        default=0)
    warranty_period_unit = fields.Selection(
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('year', 'Years'),
        ],
        string="Warranty Unit",
        default='month',
        required=True
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_warranty_definition(self):
        self.ensure_one()
        template = self.product_tmpl_id
        if template.warranty_period > 0:
            return template.warranty_period, template.warranty_period_unit
        if template.categ_id.warranty_period > 0:
            return template.categ_id.warranty_period, template.categ_id.warranty_period_unit
        return 0, 'month'

    def _get_warranty_expiration_date(self, start_date):
        self.ensure_one()
        if not start_date:
            return False
        period, unit = self._get_warranty_definition()
        if period <= 0:
            return False
        start_date = fields.Date.to_date(start_date)
        if unit == 'day':
            return start_date + relativedelta(days=period)
        if unit == 'year':
            return start_date + relativedelta(years=period)
        return start_date + relativedelta(months=period)
