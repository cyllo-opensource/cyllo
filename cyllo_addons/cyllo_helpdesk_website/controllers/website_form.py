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
import base64
from odoo import _, tools
from odoo.addons.website.controllers import form
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import plaintext2html


class WebsiteForm(form.WebsiteForm):

    def _get_website_ticket_team(self, values):
        """:param dict values: Dictionary containing ticket creation values.
    :return: helpdesk.team record used for ticket creation.
    :rtype: recordset(helpdesk.team)
    :raises ValidationError:
        - If the provided team is invalid or not allowed for website tickets.
        - If no Helpdesk Team is enabled for website ticket creation."""
        team_id = values.get("team_id")
        if team_id:
            team = request.env["helpdesk.team"].sudo().browse(int(team_id))
            if not team.exists() or not team.use_website_ticket_creation:
                raise ValidationError(_("Invalid Helpdesk Team"))
            return team
        team = request.env["helpdesk.team"].sudo().search(
            [("use_website_ticket_creation", "=", True)], limit=1
        )
        if not team:
            raise ValidationError(_("No Helpdesk Team enabled for website"))

        return team

    def _get_or_create_partner(self, values):
        """Retrieve or create a customer (res.partner) from website ticket data.

        This method attempts to find an existing partner:
        - If a user is logged in, it uses their partner record.
        - If not logged in, it searches for a partner by email.
        - If no partner is found, a new partner record is created.

        :param dict values: Dictionary containing website form data
            (email, phone, partner_name).
        :return: Partner record associated with the ticket.
        :rtype: recordset(res.partner)"""
        # Prioritize logged-in user
        if not request.env.user._is_public():
            return request.env.user.partner_id

        email = tools.email_normalize(values.get("email"))
        phone = values.get("phone")
        name = values.get("partner_name") or email or _("Website Visitor")

        partner = request.env["res.partner"].sudo()
        if email:
            partner = partner.search([("email", "=", email)], limit=1)

        if partner:
            partner.write({
                "name": name,
                "phone": phone,
            })
            return partner

        return request.env["res.partner"].sudo().create({
            "name": name,
            "email": email,
            "phone": phone,
        })

    def insert_record(self, request, model, values, custom, meta=None):
        """Customize website Helpdesk Ticket creation.

    Assigns team and customer, sets default values,
    creates the ticket, and attaches uploaded files."""
        if model.model == "helpdesk.ticket":
            # Team
            team = self._get_website_ticket_team(values)
            # Partner
            partner = self._get_or_create_partner(values)
            # Assign values
            values.update({
                "team_id": team.id,
                "customer_id": partner.id,
                "email": values.get("email"),
                "description": values.get("description") or _("No description"),
                "source": "website",
            })

            # Ensure subject exists
            if not values.get("name"):
                values["name"] = _("Website Ticket")
        record_id = super().insert_record(request, model, values, custom, meta=meta)
        if model.model == "helpdesk.ticket" and record_id:
            ticket = request.env['helpdesk.ticket'].sudo().browse(record_id)
            # Handle attachments from the website form
            if 'attachment_ids' in request.httprequest.files:
                for file in request.httprequest.files.getlist('attachment_ids'):
                    if file and file.filename:
                        attachment_record = request.env['ir.attachment'].sudo().create({
                            'name': file.filename,
                            'type': 'binary',
                            'datas': base64.b64encode(file.read()),
                            'res_model': 'helpdesk.ticket',
                            'res_id': record_id,
                        })
                        ticket.write({'attachment_ids': [(4, attachment_record.id)]})
        return record_id
