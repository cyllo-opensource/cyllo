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

from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

from odoo import Command, http, _
from odoo.addons.cyllo_portal.controllers.main import TableCompute as Table
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers import portal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.osv.expression import OR
from odoo.tools import lazy


class SupportServicePortalTicket(portal.CustomerPortal):
    """ Class to define all the details needed for the portal view """

    @http.route(
        ['/support-service-ticket/save_support_service_ticket_layout_mode'],
        type='json', auth='user', website=True)
    def save_support_service_ticket_layout_mode(self, layout_mode):
        assert layout_mode in ('grid', 'list'), "Invalid layout mode"
        request.session['support_service_ticket_layout_mode'] = layout_mode

    @http.route(
        ['/support-service-ticket', '/support-service-ticket/page/<int:page>'],
        type='http', auth="user",
        website=True)
    def get_my_support_service_tickets(self, page=1, state='all',
                                       search_in='all', search=None):
        """This route is called whenever the user clicks on the
        'Support Service Ticket' menu on the website.
        :return: HTTP response containing the 'my_support_service_ticket' template
        with relevant data for the user's support service ticket.
        """
        ServiceTicket = request.env['support.service.ticket'].sudo()
        searchbar_inputs = self._get_ticket_searchbar_inputs()
        domain = self._get_support_domain(state)
        if search and search_in:
            domain += self._get_search_domain(search_in, search)
        pager = portal_pager(
            url='/support-service-ticket',
            url_args={'state': state},
            total=ServiceTicket.search_count(domain),
            page=page,
            step=25
        )
        layout_mode = request.session.get('support_service_ticket_layout_mode')
        if not layout_mode:
            layout_mode = 'list'
            request.session['support_service_ticket_layout_mode'] = layout_mode
        records = ServiceTicket.search(
            domain,
            limit=25,
            offset=pager['offset']
        )
        values = {
            'tickets': records,
            'layout_mode': layout_mode,
            'bins': lazy(lambda: Table().process(records, ppg=25, ppr=4)),
            'page_name': 'support_service_tickets',
            'state': state,
            'create_url': '/support-service-ticket/create',
            'pager': pager,
            'search_in': search_in,
            'search': search,
            'default_url': '/support-service-ticket',
            'searchbar_inputs': searchbar_inputs
        }
        return request.render(
            "cyllo_support_service.support_service_ticket_template", values)

    def _get_ticket_searchbar_inputs(self):
        """ Get the search bar inputs for the support service ticket portal. """
        return {
            'all': {'input': 'all', 'label': _('Search in All'), 'order': 1},
            'name': {'input': 'name', 'label': _('Search in Name'), 'order': 1},
            'ticket': {'input': 'ticket', 'label': _('Search in Ref'),
                       'order': 1},
        }

    def _get_search_domain(self, search_in, search):
        """ Get the search domain for the support service ticket portal. """
        search_domain = []
        if search_in in ('ticket', 'all'):
            search_domain = OR([search_domain, [('ticket', 'ilike', search)]])
        if search_in in ('name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        return search_domain

    def _get_support_domain(self, state):
        """ Get the support domain for the support service ticket portal. """
        partner_id = request.env.user.partner_id.id
        domain = [] if request.env.user._is_admin() else [(
            'customer_id', '=', partner_id)]
        if state == 'draft':
            domain.append(('stage_id', '=', request.env.ref(
                'cyllo_support_service.support_service_stage_new').id))
        elif state == 'progress':
            domain.append(('stage_id', '=', request.env.ref(
                'cyllo_support_service.support_service_stage_in_progress').id))
        elif state == 'hold':
            domain.append(('stage_id', '=', request.env.ref(
                'cyllo_support_service.support_service_stage_on_hold').id))
        elif state == 'solved':
            domain.append(('stage_id', '=', request.env.ref(
                'cyllo_support_service.support_service_stage_solved').id))
        elif state == 'closed':
            domain.append(('stage_id', '=', request.env.ref(
                'cyllo_support_service.support_service_stage_closed').id))
        return domain

    @http.route(['/support-service-ticket/<int:ticket_id>'],
                type='http', auth="user", website=True)
    def get_support_service_ticket_details(self, ticket_id, report_type=None,
                                           access_token=None, download=True):
        """ This route is called whenever the user clicks on 'Support Service Ticket'
        menu in website"""
        try:
            current_record = self._document_check_access(
                'support.service.ticket', ticket_id,
                access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=current_record,
                report_type=report_type,
                report_ref='cyllo_support_service.support_service_report_document',
                download=download,
            )
        return request.render(
            "cyllo_support_service.support_service_ticket_details", {
                'object': current_record,
                'support_service_ticket': request.env[
                    'support.service.ticket'].sudo().browse(ticket_id),
                'page_name': 'support_service_ticket_details',
            })

    @http.route(['/support-service-ticket/create'], type='http', auth="user",
                website=True)
    def support_service_ticket_form(self):
        """ This route is called whenever the user clicks on 'Create Ticket'
        button in website"""
        priority_field_info = request.env[
            'support.service.ticket'].sudo().fields_get(['priority'])
        priority_values = priority_field_info['priority']['selection']
        return request.render(
            "cyllo_support_service.support_service_ticket_form", {
                'customers': request.env['res.partner'].sudo().search([]),
                'categories': request.env[
                    'support.service.category'].sudo().search([]),
                'sale_order_items': request.env['sale.order'].sudo().search(
                    [('partner_id', '=', request.env.user.partner_id.id)]),
                'priority_values': priority_values,
                'page_name': 'create_ticket'
            })

    @http.route(['/support-service-ticket/close/<int:req_id>'], type='http',
                auth="user", website=True)
    def support_service_ticket_close(self, req_id):
        """ This route is called whenever the user hits the 'Close' button """
        support_service_ticket = request.env[
            'support.service.ticket'].sudo().browse(req_id)
        support_service_ticket.stage_id = request.env.ref(
            'cyllo_support_service.support_service_stage_closed').id
        return request.render(
            'cyllo_support_service.support_service_ticket_closing_template')

    @http.route(['/ticket/submit'], type='http', auth="user", website=True)
    def submit_appointment(self, **kwargs):
        """ This route is called whenever the user hits the 'Submit' button """
        ticket = request.env['support.service.ticket'].sudo().create({
            'customer_id': request.env.user.partner_id.id,
            'name': kwargs.get('ticket_name'),
            'phone': kwargs.get('phone'),
            'email': kwargs.get('email'),
            'category_id': kwargs.get('category_name'),
            'sale_order_item_id': kwargs.get('sale_order'),
            'description': kwargs.get('description'),
            'priority': kwargs.get('priority'),
            'ticket_type': kwargs.get('ticket_type'),
            'type_of_issue': kwargs.get('type_of_issue'),
            'ticket_source': 'portal'
        })
        if 'attachments' in request.httprequest.files:
            attached_files = request.httprequest.files.getlist('attachments')
            attachments = []
            for attachment in attached_files:
                filename = secure_filename(attachment.filename)
                file_data = attachment.read()
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'res_model': 'support.service.ticket',
                    'res_id': ticket.id,
                    'type': 'binary',
                    'public': True,
                    'datas': base64.b64encode(file_data),
                })
                attachments.append(Command.link(attachment.id))
            ticket = ticket.sudo()
            partner_id = request.env.user.partner_id if request.env.user.partner_id else False
            if not partner_id:
                raise NotFound()
            post_values = dict(body="Submitted records", message_type="comment",
                               subtype_xmlid="mail.mt_comment",
                               author_id=partner_id.id)
            if partner_id.email:
                post_values['email_from'] = partner_id.email_formatted
            message = ticket.with_context(
                mail_create_nosubscribe=True).message_post(**post_values)
            message.sudo().write({'attachment_ids': attachments})
        return request.render("cyllo_portal.request_submit_template",
                              {'url': '/support-service-ticket'})
