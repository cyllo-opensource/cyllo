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
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class AppointmentCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        Appointment = request.env['appointment.appointment']
        if 'appointment_count' in counters:
            appointment_count = Appointment.search_count([
                ('partner_id', '=', partner.id),
                ('state', 'not in', ['draft', 'cancelled', 'rejected'])
            ])
            values['appointment_count'] = appointment_count
        return values

    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Appointment = request.env['appointment.appointment']
        domain = [
            ('partner_id', '=', partner.id),
            ('state', 'not in', ['draft', 'cancelled', 'rejected'])
        ]
        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'start_datetime desc'},
            'name': {'label': 'Reference', 'order': 'name'},
            'state': {'label': 'Status', 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': 'All', 'domain': []},
            'upcoming': {'label': 'Upcoming', 'domain': [('state', 'in', ['confirmed', 'pending_payment'])]},
            'past': {'label': 'Past', 'domain': [('state', 'in', ['done', 'no_show'])]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        appointment_count = Appointment.search_count(domain)
        pager = portal_pager(
            url="/my/appointments",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=appointment_count,
            page=page,
            step=self._items_per_page
        )
        appointments = Appointment.search(domain, order=order, limit=self._items_per_page, offset=pager['offset']).sudo()
        values.update({
            'appointments': appointments,
            'page_name': 'appointment',
            'pager': pager,
            'default_url': '/my/appointments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        return request.render("cyllo_appointment.portal_my_appointments", values)
