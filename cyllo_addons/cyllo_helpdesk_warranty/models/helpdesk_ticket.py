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

    use_product_warranty = fields.Boolean(
        related='team_id.use_product_warranty', string="Use Product Warranty")
    warranty_status = fields.Selection([
        ('none', 'No Warranty'),
        ('under_warranty', 'Under Warranty'),
        ('expired', 'Warranty Expired')
    ], compute='_compute_warranty_status', string="Warranty Status Evaluation")
    is_under_warranty_evaluation = fields.Boolean(
        related='sale_order_line_id.is_under_warranty',
        string="Is Under Warranty",
        help="Shows if the selected product is currently under warranty."
    )

    @api.depends('sale_order_line_id', 'use_product_warranty')
    def _compute_warranty_status(self):
        today = fields.Date.today()
        for ticket in self:
            if not ticket.use_product_warranty or not ticket.sudo().sale_order_line_id:
                ticket.warranty_status = False
                continue
            expiration_date = ticket.sudo().sale_order_line_id.warranty_expiration_date
            if not expiration_date:
                ticket.warranty_status = 'none'
            elif expiration_date > today:
                ticket.warranty_status = 'under_warranty'
            else:
                ticket.warranty_status = 'expired'
