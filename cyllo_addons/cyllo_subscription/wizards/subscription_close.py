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
from odoo import _, fields, models


class SubscriptionClose(models.TransientModel):
    """Transient model to call on subscription close button click"""
    _name = 'subscription.close'
    _description = 'Subscription Close'

    close_reason_id = fields.Many2one('subscription.order.close.reason')
    subscription_order_id = fields.Many2one('subscription.order')

    def action_close(self):
        """Method to close subscription"""
        self.subscription_order_id.state_subscription = 'churned'
        self.subscription_order_id.message_post(
                body=_(f'Subscription order is closed due to the reason: {self.close_reason_id.reason}'),
                message_type='comment', subtype_xmlid='mail.mt_comment')
