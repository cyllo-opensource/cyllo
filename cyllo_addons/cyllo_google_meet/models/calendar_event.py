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
import logging
import uuid

import requests
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_google_meet = fields.Boolean(
        string='Google Meeting',
        help='Enable to create a Google Meet for this event.'
    )
    google_meet_url = fields.Char(
        string='Google Meet URL',
        readonly=True,
        help='URL to join the Google Meet.'
    )
    google_meet_event_id = fields.Char(
        string='Google Calendar Event ID',
        readonly=True,
        help='Internal Google Calendar event ID.'
    )
    description = fields.Html(
        'Description',
        compute='_compute_description',
        store=True,
        readonly=False
    )

    @api.depends('google_meet_url', 'is_google_meet', 'start', 'stop')
    def _compute_description(self):
        """Generate a formatted meeting description."""
        for rec in self:
            if not rec.is_google_meet:
                rec.description = ""
                continue

            if rec.google_meet_url:
                start_str = fields.Datetime.to_string(rec.start)
                stop_str = fields.Datetime.to_string(rec.stop)
                rec.description = Markup(_(f"""
                    <div style="font-family: Arial, sans-serif; color: #333; margin-top: 12px; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                        <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                            <i class="fa fa-video-camera" style="color:#00897B;"></i> Google Meet
                        </h2>
                        <p style="font-size: 14px; margin: 6px 0;">
                            <b>Start:</b> {start_str}<br>
                            <b>End:</b> {stop_str}
                        </p>
                        <div style="font-size: 14px; margin: 12px 0; word-break: break-all;">
                            <b>Google Meet Link:</b>
                            <a href="{rec.google_meet_url}" target="_blank">
                                {rec.google_meet_url}
                            </a>
                        </div>
                        <div style="text-align: center; margin-top: 18px;">
                            <a href="{rec.google_meet_url}"
                               target="_blank"
                               style="
                                   background-color: #00897B;
                                   color: white;
                                   padding: 10px 18px;
                                   text-decoration: none;
                                   border-radius: 5px;
                                   font-size: 14px;
                                   display: inline-block;">
                                ▶ Join Google Meet
                            </a>
                        </div>
                    </div>
                """))

    @api.onchange('is_google_meet')
    def _onchange_is_google_meet(self):
        """Removes the linked Google Calendar event and clears stored meeting information when Google Meet is disabled."""
        if not self.is_google_meet and self.google_meet_event_id:
            try:
                access_token = self._refresh_google_access_token()
                requests.delete(
                    f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{self.google_meet_event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
            except Exception:
                _logger.warning(
                    f"Could not delete Google Calendar event "
                    f"{self.google_meet_event_id}"
                )

            self.google_meet_url = ''
            self.google_meet_event_id = ''
            self.videocall_location = ''
            _logger.info(f"Google Meet cleared for event '{self.name}'.")

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically creates a Google Meet meeting and sends invitations if Google Meet is enabled."""
        events = super().create(vals_list)
        for event in events:
            if event.is_google_meet:
                self._create_google_meet(event)
                event._send_google_meet_invitation_to_attendees()
        return events

    def write(self, vals):
        """Creates Google Meet meetings if missing and sends invitations to newly added attendees."""
        old_partners = {rec.id: rec.partner_ids for rec in self}
        res = super().write(vals)

        for event in self:
            if event.is_google_meet and not event.google_meet_event_id:
                self._create_google_meet(event)
                event._send_google_meet_invitation_to_attendees()
            else:
                old = old_partners.get(event.id, self.env['res.partner'])
                new_partners = event.partner_ids - old
                if new_partners:
                    event._send_google_meet_invitation_to_attendees(
                        new_partners)
        return res

    def unlink(self):
        """Removes linked Google Calendar meetings before deleting local event records."""
        for event in self:
            if event.is_google_meet and event.google_meet_event_id:
                try:
                    access_token = event._refresh_google_access_token()
                    requests.delete(
                        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event.google_meet_event_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10,
                    )
                except Exception:
                    _logger.warning(
                        f"Could not delete Google Calendar event "
                        f"{event.google_meet_event_id} on unlink."
                    )
        return super().unlink()

    def action_google_meet_url(self):
        """Returns an action that redirects the user to the meeting URL in a new browser tab."""
        meet_url = self.google_meet_url or 'https://meet.google.com'
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': meet_url,
        }

    def _refresh_google_access_token(self):
        """Retrieves OAuth configuration values and requests a new access token using the stored refresh token."""
        params = self.env['ir.config_parameter'].sudo()
        refresh_token = params.get_param('cyllo_google.refresh_token')
        client_id = params.get_param('cyllo_google.client_id')
        client_secret = params.get_param('cyllo_google.client_secret')
        if not all([refresh_token, client_id, client_secret]):
            raise ValidationError(
                "Google OAuth configuration is incomplete. "
                "Please fill in Client ID, Client Secret and Refresh Token "
                "under Settings → Google Forms Configuration."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise ValidationError(f"Token refresh failed: {response.text}")

        access_token = response.json().get("access_token")
        if not access_token:
            raise ValidationError("Access token missing in response.")
        return access_token

    def _create_google_meet(self, cal_event):
        """Sends a request to Google Calendar API, creates a meeting link, and stores the meeting URL and event ID."""
        access_token = cal_event._refresh_google_access_token()

        event_body = {
            "summary": cal_event.name or "Meeting",
            "start": {
                "dateTime": cal_event.start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": cal_event.stop.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "UTC",
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    },
                }
            },
            "guestsCanModify": False,
            "guestsCanInviteOthers": True,
            "guestsCanSeeOtherGuests": True,
            "attendees": [
                {"email": partner.email}
                for partner in cal_event.attendee_ids.mapped('partner_id')
                if partner.email
            ],
        }

        resp = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            params={"conferenceDataVersion": 1},
            json=event_body,
            timeout=10,
        )

        if resp.status_code not in (200, 201):
            raise ValidationError(
                f"Failed to create Google Meet:\n{resp.text}"
            )

        result = resp.json()
        entry_points = result.get("conferenceData", {}).get("entryPoints", [])
        meeting_url = next(
            (ep.get("uri") for ep in entry_points
             if ep.get("entryPointType") == "video"),
            ""
        )
        google_event_id = result.get("id", "")

        if not meeting_url:
            raise ValidationError(
                "Google Meet URL not returned. "
                "Ensure your OAuth token has the 'calendar.events' scope."
            )

        cal_event.sudo().write({
            'google_meet_url': meeting_url,
            'google_meet_event_id': google_event_id,
            'videocall_location': meeting_url,
        })
        # A meeting launched from "Schedule Activity" already has a linked
        # mail.activity.  Keep its planned-activity note in sync with the
        # generated meeting details, including its start and end time.
        if cal_event.activity_ids:
            cal_event.activity_ids.write({
                'note': cal_event.description,
            })
        _logger.info(
            f"calendar.event [{cal_event.id}] — Google Meet created: {meeting_url}"
        )

    def _send_google_meet_invitation_to_attendees(self, partners=None):
        """Sends email invitations to all attendees or specified partner records using the calendar meeting template."""
        template = self.env.ref(
            "calendar.calendar_template_meeting_update",
            raise_if_not_found=False
        )
        if not template:
            return

        target_partners = partners or self.attendee_ids.mapped('partner_id')
        target_partner_ids = [p.id for p in target_partners]

        template.with_context(
            default_partner_ids=target_partner_ids
        ).send_mail(self.id, force_send=True)

    def _google_meet_alarm_notification(self):
        """Posts reminder messages to chatter and sends bus notifications to attendees before the meeting starts."""
        for rec in self:
            if not rec.is_google_meet:
                continue

            start_str = fields.Datetime.to_string(rec.start)
            stop_str = fields.Datetime.to_string(rec.stop)

            message = Markup(f"""
                <div style="font-family: Arial, sans-serif; color: #333; padding: 16px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 420px;">
                    <h2 style="margin-top: 0; color: #2c3e50; font-size: 20px; text-align: center;">
                        <i class="fa fa-video-camera" style="color:#00897B;"></i> Google Meet Reminder
                    </h2>
                    <p style="font-size: 14px; margin: 6px 0;">
                        <b>Start:</b> {start_str}<br>
                        <b>End:</b> {stop_str}
                    </p>
                    <div style="text-align: center; margin-top: 18px;">
                        <a href="{rec.google_meet_url}"
                           target="_blank"
                           style="
                               background-color: #00897B;
                               color: white;
                               padding: 10px 18px;
                               text-decoration: none;
                               border-radius: 5px;
                               font-size: 14px;
                               display: inline-block;">
                            ▶ Join Google Meet
                        </a>
                    </div>
                </div>
            """)

            rec.message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=rec.attendee_ids.mapped('partner_id').ids
            )

            for partner in rec.attendee_ids.mapped('partner_id'):
                self.env['bus.bus']._sendone(
                    (self.env.cr.dbname, 'res.partner', partner.id),
                    {
                        'type': 'simple_notification',
                        'title': "Google Meet Reminder",
                        'message': f"Your meeting '{rec.name}' is starting soon!",
                        'meet_url': rec.google_meet_url,
                    }
                )
