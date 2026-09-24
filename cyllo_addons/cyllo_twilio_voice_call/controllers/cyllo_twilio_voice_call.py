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
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import Dial, VoiceResponse

from odoo import http
from odoo.http import request


class TwilioAccessToken(http.Controller):
    """Class for connecting odoo with twilio"""

    @http.route('/access/token', auth='public', type='json')
    def access_token(self, redirect=None, **kw):
        """Generate an access token for Twilio voice calls"""
        account_sid = request.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.account_sid")
        api_secret = request.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.api_secret")
        api_key = request.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.api_key")
        outgoing_application_sid = request.env[
            "ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.outgoing_application_sid")
        twilio_phone_number = request.env[
            "ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.from_number")
        # Check if Twilio configuration parameters are set
        if not all(
                [account_sid, api_key, api_secret, outgoing_application_sid,
                 twilio_phone_number]):
            return {"status": "not_configured",
                    "message": "Twilio is not configured. Check system parameters."}
        identity = request.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.twilio_user_identity")
        # Create the access token with necessary grants
        token = AccessToken(account_sid, api_key, api_secret,
                            identity=identity)
        voice_grant = VoiceGrant(
            outgoing_application_sid=outgoing_application_sid,
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        return {"status": "configured", "token": token.to_jwt()}

    @http.route('/voice', type='http', auth='public', methods=['POST'],
                csrf=False)
    def voice(self, **kw):
        """Handle Twilio voice call requests and generate XML responses."""
        response = VoiceResponse()
        caller = kw.get('Caller')
        caller_identity = caller.replace('client:', '') if caller else None
        user_identity = request.env[
            "ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.twilio_user_identity")
        twilio_phone_number = request.env[
            "ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.from_number")
        to_num = kw.get('To')
        is_recording_enable = request.env[
            "ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.enable_call_recording")
        web_base_url = request.env[
            'ir.config_parameter'].sudo().get_param(
            'web.base.url')
        status_callback_url = web_base_url + '/status' if web_base_url else None
        recording_status_callback = web_base_url + '/recording' if web_base_url else None
        if caller_identity == user_identity:
            if not to_num:
                return http.Response("Missing 'To' parameter", status=400)
            if is_recording_enable:
                dial = Dial(callerId=twilio_phone_number, record=True,
                            recordingStatusCallback=recording_status_callback)
            else:
                dial = Dial(callerId=twilio_phone_number)
            dial.number(to_num, status_callback=status_callback_url)
            response.append(dial)
        else:
            if is_recording_enable:
                dial = Dial(callerId=caller_identity, record=True,
                            recordingStatusCallback=recording_status_callback)
            else:
                dial = Dial(callerId=caller_identity)
            dial.client(user_identity)
            response.append(dial)

        return http.Response(str(response), mimetype='text/xml')

    @http.route('/status', type='http', auth='public', methods=['POST'],
                csrf=False)
    def status(self, **kw):
        """Update outgoing call status and duration from Twilio callback."""
        parent_call_sid = kw.get('ParentCallSid')
        if parent_call_sid:
            existing_record = request.env['out.going.call.list'].sudo().search(
                [('call_sid', '=', parent_call_sid)], limit=1)
            if existing_record:
                call_status = kw.get('CallStatus')
                call_duration = kw.get('CallDuration')
                existing_record.write({
                    'status': call_status,
                    'duration': call_duration
                })

    @http.route('/recording', type='http', auth='public', methods=['POST'],
                csrf=False)
    def recording_status(self, **kw):
        """Store Twilio call recording URL in the corresponding call record."""
        call_sid = kw.get('CallSid')
        recording_url = kw.get('RecordingUrl')
        if call_sid and recording_url:
            # Search for outgoing call record first, fallback to incoming call record
            record = request.env['out.going.call.list'].sudo().search(
                [('call_sid', '=', call_sid)], limit=1) or \
                     request.env['incoming.call.list'].sudo().search(
                         [('call_sid', '=', call_sid)], limit=1)
            if record:
                record.write({'record_sid': recording_url})
