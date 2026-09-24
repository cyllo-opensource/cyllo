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


class ResConfigSettings(models.TransientModel):
    """class involves adding fields to crm settings"""
    _inherit = 'res.config.settings'

    create_lead_wishlist = fields.Boolean(string='Wishlist Lead',
                                          config_parameter='cyllo_crm_advance_lead.create_lead_wishlist')
    wishlist_days = fields.Integer(string='Days',
                                   config_parameter='cyllo_crm_advance_lead.wishlist_days')

    create_lead_abandoned_cart = fields.Boolean(string='Abandoned Cart Lead',
                                                config_parameter='cyllo_crm_advance_lead.create_lead_abandoned_cart')
    abandoned_cart_days = fields.Integer(string='Days',
                                         config_parameter='cyllo_crm_advance_lead.abandoned_cart_days')
    create_lead_referral = fields.Boolean(string='Referral Lead',
                                          config_parameter='cyllo_crm_advance_lead.create_lead_referral')

    @api.onchange('group_use_lead')
    def _onchange_group_use_lead(self):
        if not self.group_use_lead:
            self.create_lead_wishlist = False
            self.create_lead_abandoned_cart = False
            self.create_lead_referral = False
