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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'



    create_vendor_bills = fields.Boolean(
        config_parameter='cyllo_intercompany_transfer.create_vendor_bills',
        default=False,
        help="Automatically create a Vendor Bill from related intercompany Customer Invoice.",
    )

    create_sale_orders = fields.Boolean(
        config_parameter='cyllo_intercompany_transfer.create_sale_orders',
        default=False,
        help="Create a corresponding Sales Order for confirmed intercompany Purchase Orders.",
    )

    create_purchase_orders = fields.Boolean(
        config_parameter='cyllo_intercompany_transfer.create_purchase_orders',
        default=False,
        help="Create a corresponding Purchase Order for confirmed intercompany Sales Orders.",
    )

    synchronize_stock_moves = fields.Boolean(
        config_parameter='cyllo_intercompany_transfer.synchronize_stock_moves',
        default=False,
        help="Synchronize intercompany deliveries and receipts.",
    )
