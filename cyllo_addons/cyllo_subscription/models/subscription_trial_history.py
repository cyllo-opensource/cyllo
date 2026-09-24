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
from odoo import models, fields

class SubscriptionTrialHistory(models.Model):
    """
    Model to track the history of subscription trials used by partners.
    This helps in preventing multiple trial usages for the same product by the same customer.
    """
    _name = 'subscription.trial.history'
    _description = 'Subscription Trial Usage History'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    time_based_price_id = fields.Many2one('time.based.price', string='Plan', required=True)
    subscription_order_id = fields.Many2one('subscription.order', string='Source Subscription')
    date_started = fields.Datetime(string='Trial Start Date', default=fields.Datetime.now)
    date_trial_end = fields.Datetime(string='Trial End Date')

    _sql_constraints = [
        ('unique_trial', 'unique(partner_id, time_based_price_id)',
         'This customer has already used a trial for this product!')
    ]
