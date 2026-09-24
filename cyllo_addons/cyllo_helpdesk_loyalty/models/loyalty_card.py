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
from odoo import fields, models


class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered('helpdesk_ticket_id'):
            if record.program_id.program_type == 'gift_card':
                record.helpdesk_ticket_id.gift_card_ids = [(4, record.id)]
            else:
                record.helpdesk_ticket_id.coupon_ids = [(4, record.id)]
        return records


class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = 'loyalty.generate.wizard'

    def _get_coupon_values(self, partner):
        values = super()._get_coupon_values(partner)
        ticket_id = self.env.context.get('default_helpdesk_ticket_id')
        if ticket_id:
            values['helpdesk_ticket_id'] = ticket_id
        return values
