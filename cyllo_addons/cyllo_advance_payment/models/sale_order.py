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


class SaleOrder(models.Model):
    """Inherit sale.order for adding advance payment option"""
    _inherit = "sale.order"

    advance_payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="sale_id",
                                          help="Advance payments related to this sale order")
    total_advance_amount = fields.Float(compute="_compute_total_advance_amount", store=True,
                                        help="The total advance amount had been paid")

    @api.depends('advance_payment_ids', 'advance_payment_ids.amount')
    def _compute_total_advance_amount(self):
        """Compute total advance payment amount"""
        for rec in self:
            rec.total_advance_amount = 0
            if rec.advance_payment_ids:
                rec.total_advance_amount = sum(rec.advance_payment_ids.mapped('amount'))

    def action_advance_payment(self):
        """ Open Advance Payment Wizard"""
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payment",
            "type": "ir.actions.act_window",
            "context": {"type": 'sale'},
            "target": "new"
        }
