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


class YoutubeChannel(models.Model):
    """
    Model representing a Social Media YouTube Channel.
    """
    _name = "youtube.channel"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media YouTube Channel"

    name = fields.Char(string='Name Channel', required=True, help="Unique id of channel")
    youtube_account_id = fields.Many2one('youtube.account', string="Related Account", help="Related youtube account")
    youtube_number = fields.Char(string='Id of Channel', required=True, help="Unique id of channel")
    youtube_etag = fields.Char(string='Tag of Channel', required=True, help="Unique Tag of channel")
    customUrl = fields.Char(string='Url of Channel', required=True, help="Unique Url of channel")
    channel_image = fields.Binary(string="Image Channel", help="Image of channel")
    is_active = fields.Boolean(string="Active", help="Represent channel is active or not")
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")

    @api.model
    def get_connected_channels(self):
        channels = self.search([('youtube_account_id.state', '=', 'sync')])

        return [
            {
                "id": ch.id,
                "name": ch.name,
                "account_id": ch.youtube_account_id.id,
                "account_name": ch.youtube_account_id.name,
            }
            for ch in channels
        ]

    @api.model
    def set_default_account_from_channel(self, channel_id):
        channel = self.browse(channel_id).exists()
        if channel and channel.youtube_account_id:
            self.env['ir.config_parameter'].sudo().set_param(
                'social_youtube_account.default_youtube_account_id',
                channel.youtube_account_id.id
            )
        return True
