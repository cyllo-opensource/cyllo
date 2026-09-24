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
import secrets
from datetime import timedelta
import requests
from werkzeug import urls
from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import datetime


class YoutubeAccount(models.Model):
    """
    Model representing a Social Media YouTube Account.
    """

    _name = "youtube.account"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Social Media YouTube Account"

    client_number = fields.Char(string="Client Id", required=True, help="Client id")
    client_secret = fields.Char(
        string="Client secret ", required=True, help="Client secret",
        groups="cyllo_social_media_marketing.group_social_media_administrator",
    )
    name = fields.Char(
        string="Account Name", required=True, help="Any preferable name of the account"
    )
    access_token = fields.Char(
        help="Access token for this account ",
        groups="cyllo_social_media_marketing.group_social_media_administrator",
    )
    refresh_token = fields.Char(
        string="Refresh Token of Account", help="Refresh token for this account ",
        groups="cyllo_social_media_marketing.group_social_media_administrator",
    )
    channel_count = fields.Integer(
        string="Number of channel", help="Number of channels related to this account"
    )
    state = fields.Selection(
        [("new", "Not Connected"), ("sync", "Connected"), ("expired", "Expired")],
        "Status",
        readonly=True,
        index=True,
        default="new",
        help="State of youtube account",
    )
    token_expiry_date = fields.Datetime(
        string="Validity of Token", help="Validity of access token"
    )
    oauth_nonce = fields.Char(
        readonly=True,
        copy=False,
        help="One-time random token proving the OAuth callback for this account "
        "was actually triggered by us - the old state (a plain {id, url_return} "
        "JSON blob) let anyone forge a valid-looking callback with an arbitrary "
        "account id AND an arbitrary redirect target (open redirect). Cleared "
        "once the callback consumes it.",
    )
    company_id = fields.Many2one(
        string="Related Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
        index=True,
        help="The company associated with the social media account.",
    )
    channel_ids = fields.One2many(
        "youtube.channel", "youtube_account_id", string="Channels"
    )
    is_default = fields.Boolean(
        string="Default Account", help="The default YouTube account"
    )

    def action_get_authorization_url(self):
        """
        Get the authorization URL for connecting to YouTube API.
        """
        scopes = [
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.readonly",
        ]
        authority = "https://accounts.google.com/o/oauth2/auth"
        nonce = secrets.token_urlsafe(32)
        self.oauth_nonce = nonce
        encoded_params = urls.url_encode(
            {
                "client_id": self.client_number,
                "redirect_uri": self.env["ir.config_parameter"].get_param(
                    "web.base.url"
                )
                + "/odoo_youtube",
                "response_type": "code",
                "state": nonce,
                "scope": " ".join(scopes),
                "prompt": "consent",
                "access_type": "offline",
            }
        )
        auth_url = "%s?%s" % (authority, encoded_params)
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": auth_url,
        }

    def authenticate_with_youtube(self, authorization_code):
        """
        Authenticate with YouTube API using authorization code.
        """
        self = self.sudo()
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": authorization_code,
            "client_id": self.client_number,
            "client_secret": self.client_secret,
            "redirect_uri": self.env["ir.config_parameter"].get_param("web.base.url")
            + "/odoo_youtube",
            "grant_type": "authorization_code",
            "access_type": "offline",
        }
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            access_token = response.json().get("access_token")
            self.access_token = access_token
            self.refresh_token = response.json().get("refresh_token")
            self.state = "sync"
            self.token_expiry_date = (
                datetime.datetime.now()
                + timedelta(seconds=(response.json().get("expires_in") - 1500))
                if response.json().get("expires_in")
                else False
            )
            self.action_refresh_access_token()
            channels = self.env["youtube.channel"].search(
                [("youtube_account_id", "=", self.id)]
            )
            for channel in channels:
                channel.write({"is_active": True})
        else:
            error_message = response.json().get(
                "error_description", "Unknown error occurred."
            )
            raise ValidationError(
                _("Failed to authenticate with YouTube: %s") % error_message
            )

    def action_refresh_access_token(self):
        """
        Refresh the access token for the YouTube account.
        """
        self = self.sudo()
        token_url = "https://oauth2.googleapis.com/token"
        scopes = [
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.readonly",
        ]
        data = {
            "client_id": self.client_number,
            "client_secret": self.client_secret,
            "scope": " ".join(scopes),
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "access_type": "offline",
        }
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.token_expiry_date = (
                datetime.datetime.now()
                + timedelta(seconds=(response.json().get("expires_in") - 1500))
                if response.json().get("expires_in")
                else False
            )
        else:
            error_message = response.json().get(
                "error_description", "Unknown error occurred."
            )
            raise ValidationError(
                _("Failed to refresh access token: %s") % error_message
            )

    def action_disconnect(self):
        """
        Function for disconnecting the YouTube account.
        """
        channels = self.env["youtube.channel"].search(
            [("youtube_account_id", "=", self.id)]
        )
        for channel in channels:
            channel.write({"is_active": False})
        self.write({"state": "new"})

    def action_get_channel_details(self):
        """
        Get details of channels associated with the YouTube account.
        """
        self = self.sudo()
        if not self.token_expiry_date:
            self.action_refresh_access_token()
        elif self.token_expiry_date <= datetime.datetime.now():
            self.action_refresh_access_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        params = {"part": "snippet,brandingSettings", "mine": "true"}
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        response = requests.get(channel_url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            channels_data = response.json().get("items", [])
            self.channel_count = len(channels_data)
            for channel in channels_data:
                channel_temp = (
                    self.env["youtube.channel"]
                    .sudo()
                    .search([("youtube_number", "=", channel["id"])])
                )
                if not channel_temp:
                    image_base64 = None
                    if channel["snippet"]["thumbnails"]:
                        image_url = channel["snippet"]["thumbnails"]["default"]["url"]
                        response = requests.get(image_url, timeout=30)
                        if response:
                            image_base64 = base64.b64encode(response.content).decode(
                                "utf-8"
                            )
                    if channel:
                        self.env["youtube.channel"].sudo().create(
                            {
                                "name": channel["snippet"]["title"],
                                "youtube_account_id": self.id,
                                "is_active": True,
                                "youtube_number": channel["id"],
                                "youtube_etag": channel["etag"],
                                "customUrl": (
                                    channel["snippet"]["customUrl"]
                                    if channel["snippet"]["customUrl"]
                                    else None
                                ),
                                "channel_image": image_base64,
                            }
                        )
                else:
                    channel_temp.write({
                        "youtube_account_id": self.id,
                        "is_active": True,
                    })

    def action_open_channel(self):
        """
        Action to open associated YouTube channels.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Channels",
            "view_mode": "tree,form",
            "res_model": "youtube.channel",
            "domain": [("youtube_account_id", "=", self.id)],
            "context": "{'create': False}",
        }
