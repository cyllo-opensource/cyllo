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
import hashlib
import hmac
import logging
# import mimetypes
import os
from datetime import datetime, timedelta

import pytz
import requests
import tzlocal
# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI todo: Summarising using AI is pending (change langchain)
from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

processed_meeting = set()

# ir.config_parameter keys (must match res_config_settings.py)
PARAM_CLIENT_ID = 'cyllo_zoom.zoom_client'
PARAM_CLIENT_SECRET = 'cyllo_zoom.zoom_client_secret'
PARAM_REDIRECT_URI = 'cyllo_zoom.zoom_redirect_uri'
PARAM_REFRESH_TOKEN = 'cyllo_zoom.zoom_refresh_token'
PARAM_ACCESS_TOKEN = 'cyllo_zoom.zoom_token'
PARAM_TOKEN_EXPIRY = 'cyllo_zoom.zoom_token_expiry'
PARAM_STATUS = 'cyllo_zoom.zoom_status'


class ZoomController(http.Controller):

    @http.route('/zoom/callback', type='http', auth='public', csrf=False)
    def zoom_callback(self, **kwargs):
        """Handle Zoom OAuth callback and store tokens in global config parameters."""
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')

        if error:
            return f"<h3>Zoom Authorization Failed: {error}</h3>"
        if not code or not state:
            return "<h3>Missing code or state from Zoom response.</h3>"

        if state != 'global':
            return "<h3>Invalid state parameter. Please try connecting again.</h3>"

        ICPSudo = request.env['ir.config_parameter'].sudo()

        client_id = ICPSudo.get_param(PARAM_CLIENT_ID)
        client_secret = ICPSudo.get_param(PARAM_CLIENT_SECRET)
        redirect_uri = ICPSudo.get_param(PARAM_REDIRECT_URI)

        if not all([client_id, client_secret, redirect_uri]):
            return (
                "<h3>Missing Zoom credentials in General Settings → Zoom Integration. "
                "Please configure Client ID, Client Secret and Redirect URI first.</h3>"
            )

        auth_header = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()

        token_url = "https://zoom.us/oauth/token"

        try:
            response = requests.post(
                token_url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=15,
            )
            response.raise_for_status()
            tokens = response.json()

        except requests.exceptions.HTTPError:
            return f"<h3>Failed to exchange Zoom token: {response.text}</h3>"

        expiry = fields.Datetime.to_string(
            fields.Datetime.now() + timedelta(
                seconds=tokens.get('expires_in', 3599)
            )
        )

        ICPSudo.set_param(PARAM_ACCESS_TOKEN, tokens.get('access_token', ''))
        ICPSudo.set_param(PARAM_REFRESH_TOKEN, tokens.get('refresh_token', ''))
        ICPSudo.set_param(PARAM_TOKEN_EXPIRY, expiry)
        ICPSudo.set_param(PARAM_STATUS, 'connected')

        _logger.info("Zoom OAuth callback: global credentials saved. Expiry: %s", expiry)
        return request.redirect('/odoo/settings?searchTerms=Zoom')


    @http.route('/zoom/webhook', type='json', auth='public', methods=['POST'],
                csrf=False)
    def zoom_webhook(self, **kwargs):
        """Response from the Zoom after meeting ends, includes URL validation."""
        data = request.get_json_data() or {}
        event_type = data.get('event')

        # 1. Handle Zoom Webhook URL Validation
        if event_type == 'endpoint.url_validation':
            plain_token = data.get('payload', {}).get('plainToken')
            ICPSudo = request.env['ir.config_parameter'].sudo()
            client_secret = ICPSudo.get_param('cyllo_zoom.zoom_client_secret')

            if plain_token and client_secret:
                hash_for_validate = hmac.new(
                    client_secret.encode('utf-8'),
                    plain_token.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()

                return {
                    "plainToken": plain_token,
                    "encryptedToken": hash_for_validate
                }
            return {"status": "error", "message": "Missing token or secret"}

        # 2. Handle Meeting Ended Event
        if event_type == 'meeting.ended':
            meeting_id = str(data.get('payload', {}).get('object', {}).get('id', ''))
            if not meeting_id:
                return {"status": "error", "message": "No meeting ID found"}

            calendar_event = request.env['calendar.event'].sudo().search(
                [('zoom_meet_code', '=', meeting_id)],
                limit=1
            )

            if not calendar_event:
                _logger.warning("No calendar.event found for zoom_meet_code=%s", meeting_id)
                return {"status": "error", "message": "No matching calendar event found"}

            if calendar_event.meeting_processed:
                _logger.info("Meeting %s already processed, skipping.", meeting_id)
                return {"status": "ignored", "message": "Already processed"}

            calendar_event.write({'meeting_processed': True})

            # ----------------------------------------------------------------
            # FIX: Read res_model / res_id the same way the old code did —
            # via .read() so relational fields are resolved correctly.
            # ----------------------------------------------------------------
            events = calendar_event.read(['res_id', 'res_model'])
            res_model = events[0].get('res_model') or 'calendar.event'
            res_id = events[0].get('res_id') or calendar_event.id

            # ----------------------------------------------------------------
            # FIX: Use per-user zoom_recordings path (like old code) and fall
            # back to global ir.config_parameter only if not set on the user.
            # ----------------------------------------------------------------
            path_to_watch = ''
            if calendar_event.user_id and hasattr(calendar_event.user_id, 'zoom_recordings'):
                path_to_watch = calendar_event.user_id.zoom_recordings or ''

            if not path_to_watch:
                # Fallback to global config parameter
                path_to_watch = request.env['ir.config_parameter'].sudo().get_param(
                    'cyllo_zoom.zoom_recordings', '')

            if not path_to_watch:
                _logger.error("zoom_recordings path is not configured for user or globally.")
                return {"status": "error", "message": "Recording path not configured"}

            payload_obj = data.get('payload', {}).get('object', {})
            start_time_utc_str = payload_obj.get('start_time')
            end_time_utc_str = payload_obj.get('end_time')

            if not start_time_utc_str or not end_time_utc_str:
                _logger.error("Missing start/end time in webhook payload")
                return {"status": "error", "message": "Missing timestamps"}

            # Parse as UTC-aware datetimes
            start_time_utc = datetime.strptime(
                start_time_utc_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=pytz.UTC)
            end_time_utc = datetime.strptime(
                end_time_utc_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=pytz.UTC)

            # Convert to system local timezone
            local_tz = tzlocal.get_localzone()
            start_time_local = start_time_utc.astimezone(local_tz)
            end_time_local = end_time_utc.astimezone(local_tz)

            # Naive for display
            start_naive = start_time_local.replace(tzinfo=None)
            end_naive = end_time_local.replace(tzinfo=None)

            if not os.path.isdir(path_to_watch):
                _logger.error("No directory found at: %s", path_to_watch)
                return {"status": "error", "message": f"Path not found: {path_to_watch}"}

            folders = [
                os.path.join(path_to_watch, f)
                for f in os.listdir(path_to_watch)
            ]
            folders = [f for f in folders if os.path.isdir(f)]
            if not folders:
                return {"status": "error", "message": "No recording folders found."}

            latest_folder = max(folders, key=os.path.getmtime)

            # ----------------------------------------------------------------
            # FIX: Include .mp4 in supported extensions (like new code) AND
            # keep the old audio extensions — best of both versions.
            # ----------------------------------------------------------------
            # media_extensions = {'.mp3', '.m4a', '.wav', '.aac', '.ogg', '.mp4'}
            #
            # for root, _, files in os.walk(latest_folder):
            #     for file in files:
            #         if os.path.splitext(file)[1].lower() in media_extensions:
            #             file_path = os.path.join(root, file)
            #             _logger.info("Found media file for AI processing: %s", file_path)
            #
            #             mime_type, _ = mimetypes.guess_type(file_path)
            #             if not mime_type:
            #                 mime_type = 'video/mp4' if file.endswith('.mp4') else 'audio/mpeg'
            #
            #             with open(file_path, "rb") as media_file:
            #                 encoded_data = base64.b64encode(
            #                     media_file.read()
            #                 ).decode("utf-8")
            #
            #             # Fetch AI configuration
            #             ICPSudo = request.env['ir.config_parameter'].sudo()
            #             GEMINI_API_KEY = (
            #                 ICPSudo.get_param('cyllo_agent.api_key') or
            #                 ICPSudo.get_param('cyllo_zoom.gemini_api_key')
            #             )
            #
            #             # ----------------------------------------------------------------
            #             # FIX: Default model changed to gemini-2.5-flash to match
            #             # the old working code, with dynamic model lookup preserved.
            #             # ----------------------------------------------------------------
            #             model_id_str = ICPSudo.get_param('agent.llm_model_id')
            #             model_name = 'gemini-2.5-flash'  # Same default as old code
            #             if model_id_str:
            #                 try:
            #                     llm_record = request.env['cyllo.llm'].sudo().browse(int(model_id_str))
            #                     if llm_record.exists():
            #                         model_name = llm_record.name
            #                 except Exception:
            #                     _logger.warning("Failed to browse cyllo.llm with ID %s", model_id_str)
            #
            #             if not GEMINI_API_KEY:
            #                 _logger.error("No API Key found in system parameters.")
            #                 return {"status": "error", "message": "Missing AI API Key"}
            #
            #             # Fetch customer local time context (for CRM leads)
            #             customer_time_context = ""
            #             if res_model == 'crm.lead':
            #                 lead = request.env['crm.lead'].sudo().browse(res_id)
            #                 if lead.exists() and lead.partner_local_time:
            #                     c_time = lead.partner_local_time
            #                     customer_time_context = (
            #                         f"The customer's local time during this meeting was approximately "
            #                         f"{c_time.strftime('%H:%M')} (on {c_time.strftime('%Y-%m-%d')}). "
            #                     )
            #
            #             # Build prompt
            #             prompt = (
            #                 f"Transcribe the recording from the Zoom meeting. "
            #                 f"Meeting Name: {calendar_event.name}. "
            #                 f"The meeting started at {start_naive} and ended at {end_naive} (System Local Time). "
            #                 f"{customer_time_context}"
            #                 "Generate a professional meeting summary. Include the duration, and clearly state "
            #                 "the start/end times in the output. "
            #                 "Provide only the summary content. Do not mention that this is based on an "
            #                 "audio/video file; present it solely as the meeting summary."
            #             )
            #
            #             message = HumanMessage(
            #                 content=[
            #                     {"type": "text", "text": prompt},
            #                     {"type": "media", "data": encoded_data, "mime_type": mime_type},
            #                 ]
            #             )
            #
            #             llm = ChatGoogleGenerativeAI(
            #                 model=model_name,
            #                 google_api_key=GEMINI_API_KEY,
            #             )
            #
            #             try:
            #                 ai_response = llm.invoke([message])
            #                 if ai_response and ai_response.content:
            #                     record = request.env[res_model].sudo().browse(res_id)
            #                     record.message_post(
            #                         body=ai_response.content,
            #                         subject=f"Meeting Summary: {calendar_event.name}",
            #                     )
            #                     _logger.info(
            #                         "Summary posted to %s(%s) using model %s",
            #                         res_model, res_id, model_name
            #                     )
            #                     return {"status": "success"}
            #             except Exception as e:
            #                 _logger.exception("Cyllo AI (Gemini) call failed: %s", e)
            #                 return {"status": "error", "message": str(e)} todo: Summarising using AI is pending (change langchain)

        return {"status": "ignored"}
