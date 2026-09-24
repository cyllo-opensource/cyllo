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
from datetime import date
from werkzeug.datastructures import FileStorage

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers import portal


class FieldServiceRequestPortal(portal.PaymentPortal):
    """ Class to specify the route and template for field service request document"""

    @http.route(['/my/field_service_request'], type='http', auth='user',
                website=True)
    def get_field_service_request(self):
        """ Function to get field requests data  to portal """

        if request.env.user.has_group('base.group_portal'):
            domain = [('partner_id', '=', request.env.user.partner_id.id),
                      ('company_id', '=', request.env.company.id)]
        elif request.env.user.has_group(
                'cyllo_field_service.group_cyllo_field_service_manager'):
            domain = [('company_id', '=', request.env.company.id)]
        else:
            domain = [('company_id', '=', request.env.company.id), '|',
                      ('field_service_worker_ids.employee_id.user_id.id', '=',
                       request.env.user.id),
                      ('user_id', '=', request.env.user.id)]
        fs_request_all = request.env['field.service.request'].sudo().search(
            domain)
        fs_request_draft = fs_request_all.filtered_domain(
            [('state', '=', 'draft')])
        fs_request_submit = fs_request_all.filtered_domain(
            [('state', '=', 'submit')])
        fs_request_assigned = fs_request_all.filtered_domain(
            [('state', '=', 'assigned')])
        fs_request_in_progress = fs_request_all.filtered_domain(
            [('state', '=', 'in_progress')])
        fs_request_completed = fs_request_all.filtered_domain(
            [('state', '=', 'completed')])
        return request.render('cyllo_field_service.service_request_template',
                              {'fs_request_all': fs_request_all,
                               'fs_request_draft': fs_request_draft,
                               'fs_request_submit': fs_request_submit,
                               'fs_request_assigned': fs_request_assigned,
                               'fs_request_in_progress': fs_request_in_progress,
                               'fs_request_completed': fs_request_completed,
                               'page_name': "fs_requests"
                               })

    @http.route(['/field_service_request/<int:record>'], type='http',
                auth="user", website=True)
    def field_service_request_details(self, record, report_type=None,
                                      access_token=None, download=True):
        """ Function to get selected field request data to portal """
        try:
            fs_request_rec = self._document_check_access(
                'field.service.request', record, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        fs_request_all = request.env['field.service.request'].sudo().search(
            []).ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=fs_request_rec,
                report_type=report_type,
                report_ref='cyllo_field_service.report_field_service_request_form',
                download=download,
            )
        if record in fs_request_all:
            return http.request.render(
                'cyllo_field_service.fs_service_request_details',
                {'object': fs_request_rec,
                 'page_name': "fs_requests_details",
                 })
        else:
            return request.redirect('/field_service_request/new')

    @http.route(['/field_service_request/new'], type='http', auth="user",
                website=True)
    def field_service_request_new(self):
        """ Function to render template and pass value to website """
        if request.env.user.has_group('base.group_portal'):
            partners = request.env.user.partner_id
            sale_orders = request.env['sale.order'].search(
                [('partner_id', '=', partners.id), ('state', '=', 'sale')])
        else:
            partners = request.env['res.partner'].sudo().search([])
            sale_orders = request.env['sale.order'].search(
                [('state', '=', 'sale'),
                 ('company_id', '=', request.env.company.id)])
        domain = [('company_id', '=', request.env.company.id)]
        categories = request.env['field.service.skill.category'].sudo().search(
            domain)
        return http.request.render(
            'cyllo_field_service.fs_service_request_form', {
                'partners': partners,
                'sale_orders': sale_orders,
                'categories': categories,
                'today': date.today(),
            })

    @http.route(['/fs_request/form/action_complete'], type='json')
    def action_complete_form(self, request_id):
        """ Function to action done for request while clicking the start
        button in the portal """
        fs_request = request.env['field.service.request'].sudo().browse(
            int(request_id))
        if fs_request.service_checklist_ids.filtered(
                lambda x: x.required and x.status == 'pending'):
            return True
        else:
            fs_request.action_mark_as_done()
            return False

    @http.route(['/fs_request/form/action_start'], type='json')
    def action_start_service(self, request_id):
        """ Function to start service while clicking the start button in the portal"""
        request.env['field.service.request'].sudo().browse(
            int(request_id)).action_service_start()
        return True

    @http.route(['/fs_request/form/action_done'], type='json')
    def action_done_form_check_line(self, checkline_id):
        """ Function to action done for checklist while clicking the start button in the portal"""
        request.env['field.service.checklist'].sudo().browse(
            int(checkline_id)).action_mark_as_done()
        return True

    @http.route(['/fs_service_request/create'], type='http', auth="user",
                website=True)
    def create_field_service_request(self, **post):
        """ Function to create a new request on the basis of user response"""
        fs_request = request.env['field.service.request'].sudo().create({
            'partner_id': post.get('partner_id'),
            'description': post.get('description'),
            'priority': post.get('priority'),
            'sale_order_id': post.get('sale_order'),
            'state': 'draft',
            'skill_category_id': post.get('skill_category_id'),
            'date_deadline': post.get('date_deadline') or None,
            'company_id': request.env.company.id
        })
        for key, file_storage in request.httprequest.files.items(multi=True):
            if key == 'attachment_id' and isinstance(file_storage, FileStorage):
                filename = file_storage.filename
                content_type = file_storage.content_type
                request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(file_storage.read()),
                    'res_model': 'field.service.request',
                    'res_id': fs_request.id,
                    'mimetype': content_type
                })
        fs_request.action_submit()
        return request.render("cyllo_portal.request_submit_template",
                              {'url': '/my/field_service_request'})
