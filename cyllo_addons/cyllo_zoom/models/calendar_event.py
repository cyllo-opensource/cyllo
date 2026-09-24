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
import json
import logging

import requests
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# ir.config_parameter keys (must match res_config_settings.py)
PARAM_ACCESS_TOKEN = 'cyllo_zoom.zoom_token'


def _get_global_zoom_token(env):
    """Helper: return the global Zoom access token from ir.config_parameter."""
    return env['ir.config_parameter'].sudo().get_param(PARAM_ACCESS_TOKEN, '')


class CalendarEvent(models.Model):
    """Inheriting Calendar events to create zoom meetings"""
    _inherit = 'calendar.event'

    is_zoom_meet = fields.Boolean(
        string='Zoom Meeting',
        help='Enable to create a Zoom meeting for this event.'
    )
    zoom_meet_url = fields.Char(
        string='Zoom Meeting URL',
        help='URL to join the Zoom meeting.'
    )
    zoom_meet_code = fields.Char(
        string='Zoom Meeting ID',
        help='Zoom meeting ID (used as meeting code).'
    )
    zoom_meet_password = fields.Char(
        string='Zoom Meeting Password',
        help='Passcode required to join by Meeting ID.'
    )
    zoom_event = fields.Char(
        string='Zoom Event ID',
        help='Internal Zoom meeting event ID.'
    )
    video_call_location = fields.Char(
        'Meeting URL',
        related='zoom_meet_url',
        store=True
    )
    description = fields.Html(
        'Description',
        compute="_compute_description",
        store=True,
        readonly=False
    )
    meeting_processed = fields.Boolean(
        string='Meeting Processed',
        help='Enable when meeting is ended'
    )

    @api.depends(
        'zoom_meet_code', 'zoom_meet_url', 'zoom_meet_password',
        'is_zoom_meet', 'start', 'stop',
    )
    def _compute_description(self):
        """Generate readable description with Zoom details OR clear it."""
        for rec in self:
            # If Zoom is disabled → clear description
            if not rec.is_zoom_meet:
                rec.description = ""
                continue

            # Zoom is enabled → build HTML block
            if rec.zoom_meet_code and rec.zoom_meet_url:
                start_str = fields.Datetime.to_string(rec.start)
                stop_str = fields.Datetime.to_string(rec.stop)
                rec.description = Markup(_(f"""
                    <div style="font-family: Arial, sans-serif; color: #333; margin-top: 12px; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                        <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                            <i class="fa fa-calendar" style="color:#0078ff;"></i> Zoom Meeting
                        </h2>

                        <p style="font-size: 14px; margin: 6px 0;">
                            <b>Start:</b> {start_str}<br>
                            <b>End:</b> {stop_str}<br>
                            <b>Meeting ID:</b> {rec.zoom_meet_code}<br>
                            <b>Password:</b> {rec.zoom_meet_password or 'None'}
                        </p>
                        <div style="font-size: 14px; margin: 12px 0; word-break: break-all;">
                            <b>Zoom Meet Link:</b>
                            <a href="{rec.zoom_meet_url}" target="_blank">
                                {rec.zoom_meet_url}
                            </a>
                        </div>

                        <div style="text-align: center; margin-top: 18px;">
                            <a href="{rec.zoom_meet_url}" 
                               target="_blank"
                               style="
                                   background-color: #0078ff;
                                   color: white;
                                   padding: 10px 18px;
                                   text-decoration: none;
                                   border-radius: 5px;
                                   font-size: 14px;
                                   display: inline-block;">
                                ▶ Join Zoom Meeting
                            </a>
                        </div>
                    </div>
                """))

    def action_zoom_meet_url(self):
        """Join zoom from Odoo"""
        meet_url = self.zoom_meet_url or 'https://api.zoom.us/v2/'
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': meet_url,
        }

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)

        for event in events:
            if event.is_zoom_meet:
                # Create Zoom only after Calendar has created and linked the
                # mail.activity.  This lets the generated description be
                # displayed directly in the Planned Activities chatter card.
                event._create_zoom_meet(event)
                event._sync_zoom_meet_activity()
                event._send_zoom_invitation_to_attendees()
        return events

    def write(self, vals):
        old_partners = {rec.id: rec.partner_ids for rec in self}
        res = super().write(vals)

        for event in self:
            if event.is_zoom_meet and not event.zoom_event:
                # If Zoom was toggled on or created via write, fetch and update
                zoom_data = self._fetch_zoom_data(
                    name=event.name,
                    start=event.start,
                    duration_hours=event.duration
                )
                event.write(zoom_data)
                event._sync_zoom_meet_activity()
                event._send_zoom_invitation_to_attendees()
            else:
                # Keep the visible note in the Planned Activities card current
                # when a Zoom meeting's time or other details are edited.
                if event.is_zoom_meet:
                    event._sync_zoom_meet_activity()
                old = old_partners.get(event.id, self.env['res.partner'])
                new_partners = event.partner_ids - old
                if new_partners:
                    event._send_zoom_invitation_to_attendees(new_partners)
        return res

    def _sync_zoom_meet_activity(self):
        """Copy generated Zoom details into the linked planned activity."""
        for event in self:
            if event.activity_ids and event.description:
                event.activity_ids.write({'note': event.description})

    def _fetch_zoom_data(self, name, start, duration_hours, retry=True):
        """Helper to call Zoom API and return data dict without writing to record."""
        url = "https://api.zoom.us/v2/users/me/meetings"
        zoom_token = _get_global_zoom_token(self.env)

        if not zoom_token:
            raise UserError(_(
                "Zoom Access Token is not configured. "
                "Please go to Settings → General Settings → Zoom Integration "
                "and connect your Zoom account."
            ))

        duration_minutes = int(duration_hours * 60)

        payload = {
            "topic": name,
            "type": 2,
            "start_time": start.isoformat() if start else fields.Datetime.now().isoformat(),
            "timezone": 'UTC',
            "duration": duration_minutes,
            "settings": {
                "email_notification": False,
                "waiting_room": True,
                "join_before_host": True,
                "mute_participants_upon_entry": True,
                "auto_recording": "local",
                "auto_start_meeting_summary": True,
            },
        }

        headers = {
            'Authorization': f'Bearer {zoom_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        res_json = response.json()

        # Handle Token Expiry (code 124) with an automatic retry
        if res_json.get('code') == 124 and retry:
            _logger.info("Zoom Token Expired (124). Attempting auto-refresh and retry...")
            try:
                # Trigger the global refresh method
                self.env['res.config.settings'].sudo().action_zoom_meet_refresh_token()
                # Retry once without the retry flag
                return self._fetch_zoom_data(name, start, duration_hours, retry=False)
            except Exception as e:
                _logger.error("Auto-refresh failed during meeting creation: %s", e)
                # Fall through to the normal error handling if refresh fails

        if res_json.get('id'):
            return {
                'zoom_event': str(res_json.get('id')),
                'zoom_meet_url': res_json.get('join_url'),
                'zoom_meet_code': str(res_json.get('id')),
                'zoom_meet_password': res_json.get('password') or '',
            }
        else:
            # If we still have an error after a potential retry
            error_msg = res_json.get('message', 'Unknown error')
            if res_json.get('code') == 124:
                raise UserError(_(
                    "Zoom Token Expired and auto-refresh failed. Please go to "
                    "Settings → General Settings → Zoom Integration and "
                    "manually click 'Refresh Token'."))

            raise ValidationError(
                _("Failed to create Zoom meeting: %s") % error_msg)

    def _create_zoom_meet(self, cal_event):
        """Standard wrapper around fetch to maintain compatibility if needed."""
        zoom_data = self._fetch_zoom_data(
            name=cal_event.name,
            start=cal_event.start,
            duration_hours=cal_event.duration
        )
        cal_event.write(zoom_data)

    @api.onchange("is_zoom_meet")
    def _onchange_is_zoom_meet(self):
        if not self.is_zoom_meet and self.zoom_event:
            zoom_token = _get_global_zoom_token(self.env)
            url = f'https://api.zoom.us/v2/meetings/{self.zoom_event}'
            headers = {
                'Authorization': f'Bearer {zoom_token}',
                'Content-Type': 'application/json',
            }

            response = requests.delete(url, headers=headers)
            if response.status_code == 401:
                raise UserError(_(
                    "Zoom Token Expired. Please go to Settings → General Settings "
                    "→ Zoom Integration and click 'Refresh Token'."
                ))

            # Clear all fields
            self.zoom_meet_url = ''
            self.zoom_meet_code = ''
            self.zoom_meet_password = ''
            self.zoom_event = ''
            # Description clears automatically from compute()

            _logger.info("Zoom meeting deleted for event '%s'.", self.name)

    def _send_zoom_invitation_to_attendees(self, partners=None):
        template_id = self.env.ref("calendar.calendar_template_meeting_update").id
        if not template_id:
            return

        mail_template = self.env['mail.template'].browse(template_id)
        if not mail_template.exists():
            return

        target_partners = partners or self.attendee_ids.mapped('partner_id')
        target_partners = [partner.id for partner in target_partners]

        mail_template.with_context(
            default_partner_ids=target_partners
        ).send_mail(self.id, force_send=False)

    def unlink(self):
        for event in self:
            if event.is_zoom_meet and event.zoom_event:
                zoom_token = _get_global_zoom_token(self.env)
                url = f'https://api.zoom.us/v2/meetings/{event.zoom_event}'
                headers = {
                    'Authorization': f'Bearer {zoom_token}',
                    'Content-Type': 'application/json',
                }
                requests.delete(url, headers=headers)

        return super().unlink()

    def _zoom_alarm_notification(self):
        for rec in self:
            if not rec.is_zoom_meet:
                continue

            start_str = fields.Datetime.to_string(rec.start)
            stop_str = fields.Datetime.to_string(rec.stop)

            message = Markup(f"""
                <div style="font-family: Arial, sans-serif; color: #333; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                    <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                        <i class="fa fa-calendar" style="color:#0078ff;"></i> Zoom Meeting Reminder
                    </h2>

                    <p style="font-size: 14px; margin: 6px 0;">
                        <b>Start:</b> {start_str}<br>
                        <b>End:</b> {stop_str}<br>
                        <b>Meeting ID:</b> {rec.zoom_meet_code}<br>
                        <b>Password:</b> {rec.zoom_meet_password or 'None'}
                    </p>

                    <div style="text-align: center; margin-top: 18px;">
                        <a href="{rec.zoom_meet_url}"
                           target="_blank"
                           style="
                               background-color: #0078ff;
                               color: white;
                               padding: 10px 18px;
                               text-decoration: none;
                               border-radius: 5px;
                               font-size: 14px;
                               display: inline-block;">
                            ▶ Join Zoom Meeting
                        </a>
                    </div>
                </div>
            """)

            # Post chatter message + inbox notification
            rec.message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=rec.attendee_ids.mapped('partner_id').ids
            )

            # Real-time browser popup
            for partner in rec.attendee_ids.mapped('partner_id'):
                self.env['bus.bus']._sendone(
                    (self.env.cr.dbname, 'res.partner', partner.id),
                    {
                        'type': 'simple_notification',
                        'title': "Zoom Meeting Reminder",
                        'message': f"Your meeting '{rec.name}' is starting soon!",
                        'zoom_url': rec.zoom_meet_url,
                    }
                )
