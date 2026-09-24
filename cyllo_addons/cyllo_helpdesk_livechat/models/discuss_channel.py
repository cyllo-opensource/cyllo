# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import _, models
from odoo.tools import html2plaintext, html_escape
from markupsafe import Markup


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _get_command_feedback_target(self):
        guest = self.env["mail.guest"]._get_guest_from_context()
        return guest or self.env.user.partner_id

    def _get_ticket_customer_partner(self):
        self.ensure_one()
        partner_to_exclude = self.livechat_operator_id or self.env.user.partner_id
        partner_members = self.channel_member_ids.filtered(
            lambda member: member.partner_id
            and member.partner_id != partner_to_exclude
            and member.partner_id != self.env.ref("base.partner_root")
        ).mapped("partner_id")
        if partner_members:
            return partner_members[0]

        if self.channel_type != "livechat":
            return self.env["res.partner"]

        guest = self.channel_member_ids.filtered("guest_id").guest_id[:1]
        if not guest:
            return self.env["res.partner"]

        return self.env["res.partner"].sudo().create(
            {
                "name": guest.name or self.anonymous_name or _("Visitor"),
                "country_id": guest.country_id.id or self.country_id.id,
            }
        )

    def _get_ticket_description(self):
        self.ensure_one()
        description = ""
        if self.description:
            description = "<b>%s</b><br/>%s<br/><br/>" % ( _("Description"),html_escape(html2plaintext(self.description)),)
        if hasattr(self, "_get_channel_history") and self.channel_type == "livechat":
            return description + self._get_channel_history()
        history = "<br/>".join(
            "<b>%s</b>: %s <br/>" % ( html_escape(message.author_id.name or message.author_guest_id.name or _("Unknown")),
                html_escape(html2plaintext(message.body or "")),
            )
            for message in self.message_ids.sorted("id")
        )
        return description + history

    def _get_livechat_ticket_team(self):
        self.ensure_one()
        return self.env["helpdesk.team"].sudo().search(
            [("use_livechat_ticket_creation", "=", True)],
            limit=1,
        )

    def _execute_command_help_message_extra(self):
        msg = super()._execute_command_help_message_extra()
        msg += _(
            "%(new_line)sType %(bold_start)s/ticket ticket name%(bold_end)s to create a helpdesk ticket.",
            new_line=Markup("<br>"),
            bold_start=Markup("<b>"),
            bold_end=Markup("</b>"),
        )
        return msg

    def execute_command_ticket(self, body="", **kwargs):
        self.ensure_one()

        ticket_name = (body or "").split(None, 1)
        ticket_name = ticket_name[1].strip() if len(ticket_name) > 1 else ""
        if not ticket_name:
            self._send_transient_message(
                self._get_command_feedback_target(),
                _("Usage: /ticket <name>"),
            )
            return False

        visitor_partner = self._get_ticket_customer_partner()
        visitor_guest = self.channel_member_ids.filtered("guest_id").guest_id[:1]
        customer_name = visitor_partner.name or visitor_guest.name or self.anonymous_name
        transcript = self._get_ticket_description()
        ticket_team = self._get_livechat_ticket_team() if self.channel_type == "livechat" else self.env["helpdesk.team"]

        if not ticket_team:
            ticket_team = self.env["helpdesk.team"].sudo().search([], limit=1)

        if not ticket_team:
            self._send_transient_message(
                self._get_command_feedback_target(),
                _("No helpdesk team is available to create a ticket."),
            )
            return False

        ticket_vals = {
            "name": ticket_name,
            "description": transcript,
            "source": "livechat",
            "team_id": ticket_team.id,
        }
        if visitor_partner:
            ticket_vals.update(
                {
                    "customer_id": visitor_partner.id,
                    "email": visitor_partner.email,
                    "phone": visitor_partner.phone or visitor_partner.mobile,
                }
            )
        elif customer_name:
            ticket_vals["description"] = _(
                "Livechat visitor: %s",
                customer_name,
            )
            if transcript:
                ticket_vals["description"] += "<br/><br/>%s" % transcript

        ticket = self.env["helpdesk.ticket"].sudo().create(ticket_vals)
        self._send_transient_message(
            self._get_command_feedback_target(),
            _("Ticket %(ticket)s created.", ticket=html2plaintext(ticket.display_name or ticket.name)),
        )
        return ticket.id