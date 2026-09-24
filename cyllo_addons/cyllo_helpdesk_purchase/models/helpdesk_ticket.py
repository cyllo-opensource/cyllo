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

    customer_purchase_order_count = fields.Integer(
        compute='_compute_customer_purchase_order_count',
        string='Customer Purchase Orders',
    )

    @api.depends('customer_id')
    def _compute_customer_purchase_order_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_purchase_order_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            ticket.customer_purchase_order_count = self.env[
                'purchase.order'].search_count(
                [('partner_id', 'child_of', commercial_partner.id)])

    def action_view_customer_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_form_action")
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('purchase.purchase_order_view_tree').id, 'tree')]
        return action
