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
import re

from odoo import _, api, fields, models
from twilio.base.exceptions import TwilioRestException

try:
    from twilio.rest import Client
except ImportError:
    pass


class ResConfigSettings(models.TransientModel):
    """Extends the `res.config.settings` model to add the credential's
    for the twilio configuration."""
    _inherit = 'res.config.settings'

    account_sid = fields.Char(
        help="To add the account sidfor the twilio account",
        config_parameter='cyllo_twilio_voice_call.account_sid')
    api_key = fields.Char(help="To add the api key for the twilio account",
                          config_parameter='cyllo_twilio_voice_call.api_key')
    api_secret = fields.Char(
        help="To add the api secret for the twilio account",
        config_parameter='cyllo_twilio_voice_call.api_secret')
    outgoing_application_sid = fields.Char(
        help="To add the outgoing application sid for the twilio account",
        config_parameter='cyllo_twilio_voice_call.outgoing_application_sid')
    auth_token = fields.Char(
        help="To add the auth token for the twilio account",
        config_parameter='cyllo_twilio_voice_call.auth_token')
    from_number = fields.Char(string="Phone Number",
                              help="To add the twilio phone number to call",
                              config_parameter='cyllo_twilio_voice_call.from_number')
    twilio_user_identity = fields.Char(
        string="Twilio User Identity",
        default=lambda self: self._default_twilio_user_identity(),
        config_parameter='cyllo_twilio_voice_call.twilio_user_identity'
    )
    enable_call_recording = fields.Boolean(string="Enable Call Recording",
                                           config_parameter='cyllo_twilio_voice_call.enable_call_recording',
                                           help="Enable or disable call recording")

    @api.model
    def _default_twilio_user_identity(self):
        """Generate a default value for the Twilio User Identity field."""
        user = self.env.user
        sanitized_name = re.sub(r'\W+', '', user.login)
        return f"user_{user.id}_{sanitized_name}"

    def test_twilio_connection(self):
        success = []
        errors = []

        # First connection attempt using API key and secret
        try:
            client = Client(self.api_key, self.api_secret, self.account_sid)
            application = client.applications(
                self.outgoing_application_sid).fetch()
            if application:
                success.append(
                    _("Connected Successfully using API key and secret"))
        except TwilioRestException as e:
            errors.append(
                _("Twilio API error using API key and secret: %s") % str(e))
        except Exception as e:
            errors.append(
                _("Unexpected error using API key and secret: %s") % str(e))

        # Second connection attempt using account SID and auth token
        try:
            client = Client(self.account_sid, self.auth_token)
            service = client.verify.v2.services.create(
                friendly_name="My First Verify Service")
            if service:
                success.append(
                    _("Connected Successfully using account SID and auth token"))
                # Clean up the created service
                client.verify.v2.services(service.sid).delete()
        except TwilioRestException as e:
            errors.append(
                _("Twilio API error using account SID and auth token: %s") % str(
                    e))
        except Exception as e:
            errors.append(
                _("Unexpected error using account SID and auth token: %s") % str(
                    e))

        # Validate the Outgoing Application SID
        try:
            client_auth = Client(self.account_sid, self.auth_token)
            application = client_auth.applications(
                self.outgoing_application_sid).fetch()
            if application:
                success.append(
                    _("Outgoing Application SID is valid: %s") % application.sid)
        except TwilioRestException as e:
            errors.append(
                _("Failed to validate Outgoing Application SID: %s") % str(e))
        except Exception as e:
            errors.append(
                _("Unexpected error validating Outgoing Application SID: %s") % str(
                    e))

        # Validate the Phone Number
        try:
            client_auth = Client(self.account_sid, self.auth_token)
            phone = client_auth.lookups.v1.phone_numbers(
                self.from_number).fetch()
            if phone:
                success.append(
                    _("Phone Number is valid: %s") % phone.phone_number)
        except TwilioRestException as e:
            errors.append(_("Failed to validate Phone Number: %s") % str(e))
        except Exception as e:
            errors.append(
                _("Unexpected error validating Phone Number: %s") % str(e))

        # Combine all results and display notifications
        if errors:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': " | ".join(errors),
                }
            }
        elif success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("All checks passed: ") + " | ".join(success),
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _(
                        "No errors occurred, but no successful connections were made either."),
                }
            }
