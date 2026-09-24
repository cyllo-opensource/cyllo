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
from odoo import api, fields, models


class AccountMove(models.Model):
    """Customization of the account.move model to add partner_ids field."""
    _inherit = "account.move"

    partner_ids = fields.Many2many('res.partner')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Onchange method triggered when the partner_id field changes."""
        if self.move_type == "out_invoice" or self.move_type == "out_refund":
            self.partner_ids = self.partner_id.search(
                [('is_customer', '=', True)]).ids
        elif self.move_type == "in_invoice" or self.move_type == "in_refund":
            self.partner_ids = self.partner_id.search(
                [('is_vendor', '=', True)]).ids
        else:
            self.partner_ids = self.partner_id.search([]).ids
