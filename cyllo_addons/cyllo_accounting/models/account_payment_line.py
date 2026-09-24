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


class AccountPaymentLine(models.Model):
    """For multiple invoice payment"""
    _name = "account.payment.line"
    _description = "Payment Item"
    _rec_name = "move_id"

    payment_id = fields.Many2one(comodel_name='account.payment', string="Payment Reference", ondelete='cascade',
                                 index=True, copy=False)
    move_id = fields.Many2one(comodel_name='account.move', string='Invoice', ondelete='cascade', help='Select Invoices')
    partner_id = fields.Many2one(related='move_id.partner_id', store=True, help='Partner of corresponding Invoice')
    total_amount = fields.Monetary(related='move_id.amount_total', store=True, help='Total amount from Invoice')
    pay_amount = fields.Monetary(string='Amount Due', related='move_id.amount_residual', store=True,
                                 help='Pay amount from Invoice')
    paid_amount = fields.Monetary(help='Paid amount from payment', compute='_compute_paid_amount', store=True)
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', store=True,
                                  help='currency of corresponding Invoice')

    @api.depends('move_id')
    def _compute_paid_amount(self):
        """Compute Paid Amount"""
        for rec in self.filtered(lambda x: x.move_id):
            rec.paid_amount = rec.move_id.amount_total - rec.move_id.amount_residual \
                if rec.paid_amount == 0 else rec.paid_amount
