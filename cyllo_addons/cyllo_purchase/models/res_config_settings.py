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
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Inheriting this module to install cyllo_budget_management module when
    the budget management in settings is checked """
    _inherit = 'res.config.settings'

    module_cyllo_warranty_purchase = fields.Boolean(
        string="Enable Product Warranty")

    is_extend_warranty_purchase = fields.Boolean(
        string="Extend Warranty",
        config_parameter='cyllo_purchase.is_extend_warranty_purchase'
    )
    module_cyllo_purchase_digitization = fields.Boolean(string="Purchase Digitization")
    three_way_matching = fields.Boolean(
        string="3-Way Matching",
        config_parameter='cyllo_purchase.three_way_matching',
        help="Compare purchase orders, receptions, and bills"
    )

