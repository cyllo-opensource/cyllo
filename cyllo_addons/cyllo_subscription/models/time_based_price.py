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


class TimeBasedPrice(models.Model):
    """Model for time-based pricing"""
    _name = "time.based.price"
    _description = 'Time Based Price'

    name = fields.Char(string='Subscription Name', required=True,
                       help='Subscription reference number')
    subscription_unit = fields.Selection(
        selection=[('weeks', 'Weeks'), ('months', 'Months'),
                   ('years', 'Years')], required=True, string='Unit',
        help='Unit for the subscription')
    duration = fields.Integer(help='Duration of the subscription', default=1)
    currency_id = fields.Many2one('res.currency', string='Company Currency',
                                  required=True,
                                  help="Currency of current company",
                                  default=lambda
                                      self: self.env.user.company_id.currency_id)
    cost = fields.Monetary(string='Price', help='Cost of the product')
    product_template_id = fields.Many2one('product.template', string='Product',
                                          help='Product id store here')
    trial_period = fields.Integer(help='Trial period for the product (Only integers are supported.)')
    trial_unit = fields.Selection(string='Trial Unit',
                                  selection=[('weeks', 'Weeks'), ('months', 'Months'), ('days', 'Days')],
                                  help='Unit for the trial period')

    trial_pricing_type = fields.Selection(
        selection=[
            ('fixed_price', 'Fixed Price'),
            ('percentage_discount', 'Percentage Discount'),
        ],
        string='Trial Pricing Type',
        help='Pricing rule that applies during the trial_period window. '
             'Leave empty for a classic free-trial.')
    trial_value = fields.Monetary(
        string='Trial Value',
        currency_field='currency_id',
        help='Fixed price or flat discount amount during the trial window.')
    trial_percentage = fields.Float(
        string='Trial Discount (%)',
        digits=(5, 2),
        help='Percentage discount applied during the trial window.')

    @api.constrains('duration')
    def _check_duration(self):
        """Validate that the duration is 0 or not.
        raises ValidationError: If the duration is 0 raise validation error."""
        for record in self:
            if record.duration < 1:
                raise ValidationError(
                    _("Invalid duration. Please enter a valid duration number"))

    @api.constrains('trial_period', 'trial_unit')
    def _check_trial_configuration(self):
        """Validate trial period and unit configuration."""
        for record in self:
            if record.trial_unit and record.trial_period == 0:
                raise ValidationError(
                    _('Trial period should be greater than zero if there is trial unit'))
            elif record.trial_period > 0 and not record.trial_unit:
                raise ValidationError(
                    _('If Trial Period is added then Unit should be added'))
