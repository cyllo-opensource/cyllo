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


class WarrantyExtensionWizard(models.TransientModel):
    _inherit = 'warranty.extension.wizard'

    order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        readonly=True,
    )
    line_ids = fields.Many2many(
        'sale.order.line',
        string="Sale Order Lines",
        domain="[('order_id', '=', order_id), ('is_under_warranty', '=', True)]",
    )

    def action_confirm(self):
        res = super(WarrantyExtensionWizard, self).action_confirm()
        extra_days = self._extension_to_days()
        for line in self.line_ids:
            line.warranty_extension_days += extra_days
        return res
