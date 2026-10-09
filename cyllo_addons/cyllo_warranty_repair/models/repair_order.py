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


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        readonly=False,
        help="Sale Order linked to this repair (filtered by the selected customer).",
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string="Sale Order Line",
        readonly=False,
        help="Sale Order Line linked to this repair (filtered by the selected sale order).",
    )
    warranty_status = fields.Selection([
        ('under_warranty', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
        ('none', 'No Warranty')
    ], compute='_compute_warranty_status', string="Warranty Status Evaluation",
        store=True)

    @api.depends('sale_order_line_id')
    def _compute_warranty_status(self):
        today = fields.Date.today()
        for repair in self:
            if not repair.sale_order_line_id:
                repair.warranty_status = False
                continue

            expiration_date = repair.sale_order_line_id.sale_warranty_expiration_date
            if not expiration_date:
                repair.warranty_status = 'none'
            elif expiration_date >= today:
                repair.warranty_status = 'under_warranty'
            else:
                repair.warranty_status = 'expired'

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            if not self.partner_id or self.partner_id.commercial_partner_id != self.sale_order_id.partner_id.commercial_partner_id:
                self.partner_id = self.sale_order_id.partner_id
            if self.sale_order_line_id and self.sale_order_line_id.order_id != self.sale_order_id:
                self.sale_order_line_id = False
        else:
            self.sale_order_line_id = False

    @api.onchange('sale_order_line_id')
    def _onchange_sale_order_line_id(self):
        if self.sale_order_line_id:
            self.product_id = self.sale_order_line_id.product_id
            today = fields.Date.today()
            expiration_date = self.sale_order_line_id.warranty_expiration_date
            if not expiration_date:
                self.warranty_status = 'none'
                self.under_warranty = False
            elif expiration_date >= today:
                self.warranty_status = 'under_warranty'
                self.under_warranty = True
            else:
                self.warranty_status = 'expired'
                self.under_warranty = False
