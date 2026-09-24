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
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    use_subscription = fields.Boolean(
        related='team_id.use_subscription',
        string='Use Subscription',
    )

    customer_subscription_count = fields.Integer(
        compute='_compute_customer_subscription_count',
        string='Customer Subscriptions',
    )

    @api.depends('customer_id')
    def _compute_customer_subscription_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_subscription_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            # Assuming subscription.order model exists in the subscription module
            ticket.customer_subscription_count = self.env[
                'subscription.order'].search_count(
                [('partner_id', 'child_of', commercial_partner.id)])

    def action_view_customer_subscriptions(self):
        self.ensure_one()
        # Assuming the action exists in cyllo_subscription or similar
        try:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "cyllo_subscription.subscription_order_action")
        except ValueError:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Subscriptions',
                'res_model': 'subscription.order',
                'view_mode': 'tree,form',
                'target': 'current',
            }
        
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action
