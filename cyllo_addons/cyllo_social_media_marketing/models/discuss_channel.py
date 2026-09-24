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


class DiscussChannel(models.Model):
    """This class extends the 'discuss.channel' model in Cyllo to include a new field for storing the
    Instagram Page ID."""
    _inherit = 'discuss.channel'


    def action_enable_social(self,partner,facebook,instagram):
        customer=self.env['res.partner'].sudo().browse(partner)
        channel=self.env['discuss.channel'].sudo().search([('channel_type', '=', 'chat'),('channel_partner_ids', 'in', customer.ids)])
        if facebook:
            channel.sudo().write({
                'fb_partner_number':customer.unique_fb_number,
            })
        if instagram:
            channel.sudo().write({
                'insta_partner_number':customer.unique_ig_number,
            })

