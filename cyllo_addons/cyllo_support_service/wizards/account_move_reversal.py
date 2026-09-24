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


class AccountMoveReversal(models.TransientModel):
    """ Class to add credit note for the sale order """
    _inherit = 'account.move.reversal'

    sale_order_id = fields.Many2one('sale.order', help="Sale order",
                                    required=True)
    ticket_id = fields.Many2one('support.service.ticket',
                                string="Support Service Ticket")
    account_move_ids = fields.Many2many('account.move', 'account_moves')
    move_ids = fields.Many2many('account.move', 'account_move_reversal_move',
                                'reversal_id', 'move_id',
                                related="sale_order_id.invoice_ids",
                                domain="[('state', '=', 'posted'), ('id', 'in', account_move_ids)]")

    @api.onchange('account_move_ids')
    def _onchange_account_move_ids(self):
        """
        Update the 'account_move_ids' field based on the invoice IDs of the related sale order.

        This onchange method is triggered when the 'account_move_ids' field is changed.
        It sets 'account_move_ids' to the invoice IDs of the related sale order.

        :return: None
        """
        self.account_move_ids = [(6, 0, self.sale_order_id.invoice_ids.ids)]
