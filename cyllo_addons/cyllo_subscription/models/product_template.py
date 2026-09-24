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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """Inheriting the model to add some fields and can choose it
    subscription or not"""
    _inherit = "product.template"

    is_subscription = fields.Boolean(string="Subscription Product",
                                     help='If the product is recurring product enable the field')
    time_based_ids = fields.One2many('time.based.price', 'product_template_id',
                                     string='Time Based Price',
                                     help='Time based pricing')

    @api.model_create_multi
    def create(self, vals_list):
        """ If the product being created is marked as a subscription and does
            not have any associated time-based pricing (time_based_ids), a
            ValidationError is raised, indicating that time-based pricing
            should be added.
            :param vals_list: List of dictionaries, each containing field-value
             pairs for creating multiple records.
            :raise ValidationError: If a product being created is a
             subscription and has no time-based pricing.
            :return: Result of the super().create() method.
        """
        for vals in vals_list:
            if ('is_subscription' in vals and vals[
                'is_subscription'] and 'time_based_ids' in vals and not
            vals['time_based_ids']):
                raise ValidationError(
                    _('Please add Time Based Pricing, because the product is a subscription product'))
            return super().create(vals_list)

    def write(self, vals):
        """ If the product is marked as a subscription and does not have any
            associated time-based pricing (time_based_ids), a ValidationError
            is raised, indicating that time-based pricing should be added.
            :param vals: Dictionary of field-value pairs to be updated.
            :raise ValidationError: If the product is a subscription and has no
             time-based pricing.
            :return: Result of the super().write() method.
            """
        res = super().write(vals)
        for rec in self:
            if rec.is_subscription and not rec.time_based_ids:
                raise ValidationError(
                    _('Please add Time Based Pricing, because the product is a subscription product'))

        return res
