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
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    coupon_ids = fields.Many2many('loyalty.card', 'helpdesk_ticket_coupon_rel',
                                  string='Coupons',
                                  domain=[('program_id.program_type', '=', 'coupons')])
    coupon_count = fields.Integer(compute='_compute_counts')
    gift_card_ids = fields.Many2many('loyalty.card', 'helpdesk_ticket_gift_card_rel',
                                     string='Gift Cards',
                                     domain=[('program_id.program_type', '=', 'gift_card')])
    gift_card_count = fields.Integer(compute='_compute_counts')

    @api.depends('coupon_ids', 'gift_card_ids')
    def _compute_counts(self):
        for ticket in self:
            ticket.coupon_count = len(ticket.sudo().coupon_ids)
            ticket.gift_card_count = len(ticket.sudo().gift_card_ids)

    def action_create_coupon(self):
        self.ensure_one()
        program = self.env['loyalty.program'].search(
            [('program_type', '=', 'coupons')], limit=1)
        if not program:
            raise UserError(
                _("No coupon program is configured. Create a coupon loyalty program first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_generate_wizard_action")
        action['context'] = {
            'active_id': program.id,
            'default_program_id': program.id,
            'default_mode': 'selected' if self.customer_id else 'anonymous',
            'default_customer_ids': [
                (6, 0, [self.customer_id.id])] if self.customer_id else [],
            'default_coupon_qty': 1,
            'default_helpdesk_ticket_id': self.id,
        }
        self._message_log(body=_("Coupon generation initiated."))
        return action

    def _get_loyalty_action(self, domain):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_card_action")
        action['view_mode'] = 'list,form'
        action['domain'] = domain
        return action

    def action_view_coupons(self):
        self.ensure_one()
        return self._get_loyalty_action([('id', 'in', self.coupon_ids.ids)])

    def action_send_gift_card(self):
        self.ensure_one()
        program = self.env['loyalty.program'].search(
            [('program_type', '=', 'gift_card')], limit=1)
        if not program:
            raise UserError(
                _("No gift card program is configured. Create a gift card loyalty program first."))

        action = self.env["ir.actions.actions"]._for_xml_id(
            "loyalty.loyalty_generate_wizard_action")
        action['context'] = {
            'active_id': program.id,
            'default_program_id': program.id,
            'default_mode': 'selected' if self.customer_id else 'anonymous',
            'default_customer_ids': [
                (6, 0, [self.customer_id.id])] if self.customer_id else [],
            'default_coupon_qty': 1,
            'default_helpdesk_ticket_id': self.id,
        }
        self._message_log(body=_("Gift card generation initiated."))
        return action

    def action_view_gift_cards(self):
        self.ensure_one()
        return self._get_loyalty_action([('id', 'in', self.gift_card_ids.ids)])
