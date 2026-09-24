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

from werkzeug.datastructures import FileStorage

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.payment.controllers import portal



class ServiceManagement(portal.PaymentPortal):
    """
    Portal controller for managing HR Service Requests.
    Provides endpoints for employees to:
      - View their service requests
      - Access details of individual requests
      - Create new requests
      - Submit existing requests
      - Upload related attachments
    """
    @http.route(['/service_management'], type='http', auth="user", website=True)
    def get_user_service_requests(self):
        """This route is called whenever the user clicks on the
        'Service Management' menu on the website.
        :return: HTTP response containing the 'user service requests' template
        with relevant data for the user's service requests."""
        employee_id = request.env.user.employee_ids.id
        service_model = request.env['hr.service'].sudo()
        user_services = service_model.search(
            [('employee_id', '=', employee_id)])
        service_count = len(user_services)
        values = {
            'support_service_tickets': user_services,
            'service_count': service_count,
            'draft_services': user_services.filtered(
                lambda s: s.state == 'draft'),
            'submitted_services': user_services.filtered(
                lambda s: s.state == 'submit'),
            'approved_services': user_services.filtered(
                lambda s: s.state == 'approved'),
            'returned_services': user_services.filtered(
                lambda s: s.state == 'returned'),
            'ongoing_services': user_services.filtered(
                lambda s: s.state == 'ongoing'),
            'done_services': user_services.filtered(
                lambda s: s.state == 'done'),
            'cancel_services': user_services.filtered(
                lambda s: s.state == 'cancel'),
            'page_name': 'services_page',
        }
        return request.render(
            "cyllo_hr_service_management.service_request_template", values)

    @http.route(['/service_management/details/request/<int:service_id>'],
                type='http', auth="user", website=True)
    def get_service_request_details(self, service_id, report_type=None,
                                    access_token=None, download=True):
        """ This route is called whenever the user clicks on a 'Service
        request' in website"""
        try:
            current_record = self._document_check_access(
                'hr.service', service_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')
        employee_id = request.env.user.employee_ids.id
        service_model = request.env['hr.service'].sudo()
        total_ids = service_model.search(
            [('employee_id', '=', employee_id)]).ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=current_record,
                report_type=report_type,
                download=download,
                report_ref='cyllo_hr_service_management.report_hr_service_request_form'
            )
        if service_id in total_ids:
            idx = total_ids.index(service_id)
            return request.render(
                "cyllo_hr_service_management.service_requests_details", {
                    'object': current_record,
                    'service_req': service_model.browse(service_id),
                    'page_name': 'service_details',
                    'prev_record': total_ids[idx - 1] if idx > 0 else False,
                    'next_record': total_ids[idx + 1] if idx < len(
                        total_ids) - 1 else False,
                })

        return request.redirect('/service_management/create')

    @http.route(['/service_management/create'], type='http', auth="user",
                website=True)
    def service_request_form(self):
        """Render form to create a new service request"""
        employee = request.env.user.employee_ids
        service_handlers = request.env['hr.employee'].sudo().search([])
        if len(employee) == 1:
            service_handlers = (
                    employee.parent_id or employee.department_id.manager_id or service_handlers
            )
        values = {
            'categories': request.env['hr.service.category'].sudo().search([]),
            'equipment': request.env['maintenance.equipment'].sudo().search(
                [('employee_id', '=', False)]),
            'service_equipment': request.env[
                'maintenance.equipment'].sudo().search(
                [('employee_id', '=', employee.id)]),
            'service_handlers': service_handlers,
            'page_name': 'create_service',
        }
        return request.render(
            "cyllo_hr_service_management.service_request_form", values)

    @http.route(['/service_request/submit/<int:req_id>'], type='http',
                auth="user", website=True)
    def hr_service_submit(self, req_id):
        """Submit an existing service request"""
        request.env['hr.service'].sudo().browse(req_id).action_submit()
        return request.render(
            'cyllo_hr_service_management.service_request_submitting_template')

    @http.route(['/request/submit'], type='http', auth="user", website=True)
    def submit_request(self, **kwargs):
        """Handle submission of new service request"""
        employee = request.env.user.employee_ids
        request_type = kwargs.get('request_type')
        equipment = None
        if request_type == 'custody':
            equipment = kwargs.get('equipment')
        elif request_type == 'service' and kwargs.get('service_equipment'):
            equipment = kwargs.get('service_equipment')
        service = request.env['hr.service'].sudo().create({
            'state': 'submit',
            'service_request_type': request_type,
            'employee_id': employee.id,
            'employee_department_id': kwargs.get('requester_dept'),
            'service_category_id': kwargs.get('category') or False,
            'equipment_id': equipment,
            'maintenance_type': kwargs.get(
                'maintenance_type') if request_type == 'service' and equipment else False,
            'expected_return_date': kwargs.get('expected_return_date') or False,
            'service_handler_id': int(kwargs.get('handler')),
            'service_handler_department_id': kwargs.get('handlers_dept'),
        })
        for key, file in request.httprequest.files.items(multi=True):
            if key == 'attachment_id' and isinstance(file,
                                                     FileStorage) and file.filename:
                request.env['ir.attachment'].sudo().create({
                    'name': file.filename,
                    'datas': base64.b64encode(file.read()),
                    'res_model': 'hr.service',
                    'res_id': service.id,
                    'mimetype': file.content_type,
                })
        service.action_submit()
        return request.render("cyllo_portal.request_submit_template",
                              {'url': '/service_management'})
