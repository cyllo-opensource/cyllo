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
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import plaintext2html
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class HelpdeskPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super(HelpdeskPortal, self)._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            ticket_count = request.env['helpdesk.ticket'].sudo().search_count([
                ('customer_id', '=', request.env.user.partner_id.id)
            ])
            values['ticket_count'] = ticket_count
        return values

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        HelpdeskTicket = request.env['helpdesk.ticket'].sudo()
        domain = [('customer_id', '=', request.env.user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        ticket_count = HelpdeskTicket.search_count(domain)
        pager = portal_pager(
            url="/my/tickets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=ticket_count,
            page=page,
            step=self._items_per_page
        )
        tickets = HelpdeskTicket.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'tickets': tickets,
            'page_name': 'ticket',
            'pager': pager,
            'default_url': '/my/tickets',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("cyllo_helpdesk.portal_my_tickets", values)

    @http.route(['/my/ticket/<int:ticket_id>'], type='http', auth="public", website=True)
    def portal_my_ticket_detail(self, ticket_id, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'ticket': ticket_sudo,
            'page_name': 'ticket',
        }
        return request.render("cyllo_helpdesk.portal_ticket_page", values)

    @http.route(['/my/ticket/<int:ticket_id>/close'], type='http', auth="user", website=True)
    def portal_my_ticket_close(self, ticket_id, solved=None, reason=None, **kw):
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if ticket.customer_id == request.env.user.partner_id:
            vals = {}
            if solved == '1':
                stage = request.env.ref('cyllo_helpdesk.solved_ticket')
            else:
                stage = request.env.ref('cyllo_helpdesk.canceled_ticket')
            vals['stage_id'] = stage.id
            
            if reason:
                # Append the reason to existing internal notes (HTML field)
                note = ticket.internal_notes or ""
                new_note = f"Reason for closing: {reason}"
                vals['internal_notes'] = f"{note}<br/>{new_note}" if note else new_note
            
            ticket.write(vals)
        return request.redirect('/my/ticket/%s' % ticket_id)

    @http.route(['/helpdesk/create'], type='http', auth="public", website=True)
    def website_create_ticket(self, **kw):
        values = self._prepare_ticket_form_values()
        return request.render("cyllo_helpdesk.website_create_ticket", values)

    @http.route(['/helpdesk/create/submit'], type='http', auth="public", website=True, methods=['POST'])
    def website_create_ticket_submit(self, **post):
        errors = {}
        required_fields = ["name", "email", "subject", "message", "team_id"]
        for field_name in required_fields:
            if not post.get(field_name):
                errors[field_name] = _("This field is required.")
        team = request.env["helpdesk.team"].sudo().browse(int(post.get("team_id"))) if post.get("team_id") else request.env["helpdesk.team"]
        if post.get("team_id") and (not team.exists() or not team.use_website_ticket_creation):
            errors["team_id"] = _("Please select a valid website-enabled helpdesk team.")
        if errors:
            values = self._prepare_ticket_form_values(values=post, errors=errors)
            return request.render("cyllo_helpdesk.website_create_ticket", values)

        partner_values = {
            "name": post.get("name"),
            "email": post.get("email"),
            "phone": post.get("phone"),
            "company_name": post.get("company"),
        }
        partner = request.env["res.partner"].sudo().search(
            [("email", "=", post.get("email"))],
            limit=1,
        )
        if partner:
            partner.sudo().write({key: value for key, value in partner_values.items() if value})
        else:
            partner = request.env["res.partner"].sudo().create(partner_values)

        ticket = request.env["helpdesk.ticket"].sudo().create(
            {
                "name": post.get("subject"),
                "team_id": team.id,
                "customer_id": partner.id,
                "email": post.get("email"),
                "phone": post.get("phone"),
                "description": plaintext2html(post.get("message")),
                "user_id": False,
            }
        )
        return request.redirect("/helpdesk/create?success=%s" % ticket.ticket)
