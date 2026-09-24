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
    _inherit = 'res.config.settings'

    access_token = fields.Char(
        string='Access Token',
        config_parameter='cyllo_google.access_token',
        help='Access token from Google'
    )
    client_id = fields.Char(
        string='Client ID',
        config_parameter='cyllo_google.client_id',
        help='Client ID from Google'
    )
    client_secret = fields.Char(
        string='Client Secret',
        config_parameter='cyllo_google.client_secret',
        help='Client Secret from Google'
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        config_parameter='cyllo_google.refresh_token',
        help='Refresh Token from Google'
    )

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_google.access_token', self.access_token or ''
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_google.client_id', self.client_id or ''
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_google.client_secret', self.client_secret or ''
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_google.refresh_token', self.refresh_token or ''
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            access_token=params.get_param('cyllo_google.access_token', ''),
            client_id=params.get_param('cyllo_google.client_id', ''),
            client_secret=params.get_param('cyllo_google.client_secret', ''),
            refresh_token=params.get_param('cyllo_google.refresh_token', ''),
        )
        return res