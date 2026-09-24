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
import base64
import logging
from datetime import timedelta

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

# ir.config_parameter keys
PARAM_CLIENT_ID = 'cyllo_zoom.zoom_client'
PARAM_CLIENT_SECRET = 'cyllo_zoom.zoom_client_secret'
PARAM_REDIRECT_URI = 'cyllo_zoom.zoom_redirect_uri'
PARAM_REFRESH_TOKEN = 'cyllo_zoom.zoom_refresh_token'
PARAM_ACCESS_TOKEN = 'cyllo_zoom.zoom_token'
PARAM_TOKEN_EXPIRY = 'cyllo_zoom.zoom_token_expiry'
PARAM_STATUS = 'cyllo_zoom.zoom_status'
PARAM_RECORDINGS = 'cyllo_zoom.zoom_recordings'


class ResConfigSettings(models.TransientModel):
    """Extend General Settings with a global Zoom Integration block."""
    _inherit = 'res.config.settings'

    zoom_client = fields.Char(
        string='Client ID',
        help='Zoom Developer Console Client ID',
        config_parameter=PARAM_CLIENT_ID,
    )
    zoom_client_secret = fields.Char(
        string='Client Secret',
        help='Zoom Developer Console Client Secret',
        config_parameter=PARAM_CLIENT_SECRET,
    )
    zoom_redirect_uri = fields.Char(
        string='Authorized Redirect URI',
        help='Zoom Authorized Redirect URI',
        default='http://localhost:8017/zoom/callback',
        config_parameter=PARAM_REDIRECT_URI,
    )
    zoom_refresh_token = fields.Char(
        string='Refresh Token',
        help='Zoom Refresh Token (populated automatically after connecting)',
        config_parameter=PARAM_REFRESH_TOKEN,
    )
    zoom_token = fields.Char(
        string='Access Token',
        readonly=True,
        help='Current Zoom access token (auto-populated)',
        config_parameter=PARAM_ACCESS_TOKEN,
    )
    zoom_token_expiry = fields.Char(
        string='Token Expiry',
        readonly=True,
        help='Zoom access token expiry datetime (ISO string)',
        config_parameter=PARAM_TOKEN_EXPIRY,
    )
    zoom_status = fields.Selection(
        selection=[
            ('not_connected', 'Not Connected'),
            ('connected', 'Connected'),
        ],
        string='Connection Status',
        config_parameter=PARAM_STATUS,
    )
    zoom_recordings = fields.Char(
        string='Zoom Recording Location',
        help='Local filesystem path where Zoom recordings are saved.',
        default='/home/cybrosys/Documents/Zoom',
        config_parameter=PARAM_RECORDINGS,
    )

    def action_connect_zoom(self):
        """Redirect the administrator to Zoom's OAuth authorization page."""
        self.ensure_one()
        client_id = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_CLIENT_ID)
        redirect_uri = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_REDIRECT_URI)

        if not client_id:
            raise UserError(_('Please configure the Zoom Client ID first and save settings.'))
        if not redirect_uri:
            raise UserError(_('Please configure the Zoom Redirect URI first and save settings.'))

        # Save first so param values are up-to-date
        self.execute()

        # Re-read after save
        client_id = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_CLIENT_ID)
        redirect_uri = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_REDIRECT_URI)

        base_url = 'https://zoom.us/oauth/authorize'
        zoom_url = (
            f"{base_url}"
            f"?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state=global"
        )
        return {
            'type': 'ir.actions.act_url',
            'url': zoom_url,
            'target': 'current',
        }

    def action_zoom_meet_refresh_token(self):
        """Manually refresh the global Zoom access token using the refresh token."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        client_id = ICPSudo.get_param(PARAM_CLIENT_ID)
        client_secret = ICPSudo.get_param(PARAM_CLIENT_SECRET)
        refresh_token = ICPSudo.get_param(PARAM_REFRESH_TOKEN)

        if not client_id:
            raise UserError(_('Client ID is not configured. Please set it in General Settings → Zoom Integration.'))
        if not client_secret:
            raise UserError(_('Client Secret is not configured. Please set it in General Settings → Zoom Integration.'))
        if not refresh_token:
            raise UserError(_('Refresh Token is not configured. Please connect Zoom first or enter the refresh token manually.'))

        b64 = base64.b64encode(
            f"{client_id}:{client_secret}".encode('utf-8')
        ).decode('utf-8')

        data = {
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }

        try:
            response = requests.post(
                'https://zoom.us/oauth/token',
                data=data,
                headers={
                    'Authorization': f'Basic {b64}',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout=TIMEOUT,
            )
            resp_json = response.json()
            _logger.info("Zoom global refresh response: %s", resp_json)

            if resp_json.get('access_token'):
                expiry = (
                    fields.Datetime.to_string(
                        fields.Datetime.now() + timedelta(
                            seconds=resp_json.get('expires_in', 3599)
                        )
                    )
                )
                ICPSudo.set_param(PARAM_ACCESS_TOKEN,
                                  resp_json.get('access_token'))
                ICPSudo.set_param(PARAM_TOKEN_EXPIRY, expiry)
                ICPSudo.set_param(PARAM_STATUS, 'connected')
                new_refresh = resp_json.get('refresh_token')
                if new_refresh:
                    ICPSudo.set_param(PARAM_REFRESH_TOKEN, new_refresh)

                _logger.info("Zoom global token refreshed. Expiry: %s", expiry)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Zoom Token Refreshed Successfully'),
                        'type': 'success',
                        'sticky': True,
                        'next': {'type': 'ir.actions.act_window_close'},
                    },
                }
            else:
                error_reason = resp_json.get('reason', resp_json)
                raise UserError(
                    _('Zoom token refresh failed: %s') % error_reason)

        except requests.exceptions.RequestException as e:
            _logger.exception("HTTP request to Zoom failed: %s", e)
            raise UserError(
                _('Zoom token refresh failed due to a network error.'))

    @api.model
    def _cron_check_and_refresh_zoom_tokens(self):
        """Scheduled action: refresh the global Zoom access token when connected."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        status = ICPSudo.get_param(PARAM_STATUS)
        expiry_str = ICPSudo.get_param(PARAM_TOKEN_EXPIRY)

        if status != 'connected':
            _logger.info(
                "Zoom cron: status is '%s', skipping token refresh.", status)
            return

        # Check if refresh is actually needed (e.g., expires in less than 15 mins)
        if expiry_str:
            expiry_date = fields.Datetime.from_string(expiry_str)
            if expiry_date > (fields.Datetime.now() + timedelta(minutes=15)):
                _logger.info("Zoom token still valid until %s. Skipping refresh.", expiry_str)
                return

        _logger.info("Zoom cron: refreshing global access token …")
        try:
            # Call the refresh method on the model
            self.action_zoom_meet_refresh_token()
        except Exception as e:
            _logger.warning(
                "Zoom cron: token refresh failed: %s", e)
