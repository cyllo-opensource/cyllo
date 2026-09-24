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


class IncidentManagement(portal.PaymentPortal):
    """ Class to define all the details needed for incident management the 
    portal view """

    @http.route(['/incident_management'], type='http', auth="user",
                website=True)
    def get_user_incident_requests(self):
        """This route is called whenever the user clicks on the
        'Incident Management' menu on the website.
        :return: HTTP response containing the 'user incident requests' template
        with relevant data for the user's incident requests."""
        if not request.env.user.has_group('base.group_user'):
            return request.render("portal.portal_my_home")
        employee_id = request.env.user.employee_ids.id
        incident_model = request.env['hr.incident'].sudo()
        all_incidents = incident_model.search(
            [('incident_initiator_id', '=', employee_id)])
        grouped = incident_model.read_group(
            [('incident_initiator_id', '=', employee_id)],
            ['incident_stage'], ['incident_stage']
        )
        counts = {g['incident_stage']: g['incident_stage_count'] for g in
                  grouped}
        values = {
            'user_incidents': all_incidents,
            'incident_count': len(all_incidents),
            'new_incidents': all_incidents.filtered(
                lambda x: x.incident_stage == 'new'),
            'new_incidents_count': counts.get('new', 0),
            'submitted_incidents': all_incidents.filtered(
                lambda x: x.incident_stage == 'submitted'),
            'submitted_incidents_count': counts.get('submitted', 0),
            'ongoing_incidents': all_incidents.filtered(
                lambda x: x.incident_stage == 'ongoing'),
            'ongoing_incidents_count': counts.get('ongoing', 0),
            'completed_incidents': all_incidents.filtered(
                lambda x: x.incident_stage == 'completed'),
            'completed_incidents_count': counts.get('completed', 0),
            'page_name': 'incident_page',
        }
        return request.render(
            "cyllo_hr_incident_management.incident_request_template", values)

    @http.route(['/incident_management/details/request/<int:incident_id>'],
                type='http', auth="user", website=True)
    def get_incident_request_details(self, incident_id, report_type=None,
                                     access_token=None, download=True):
        """ This route is called whenever the user clicks on a 'Incident
        request' in website"""
        try:
            current_record = self._document_check_access(
                'hr.incident', incident_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        employee_id = request.env.user.employee_ids.id
        incidents = request.env['hr.incident'].sudo().search(
            [('incident_initiator_id', '=', employee_id)]
        )
        total_ids = incidents.ids
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=current_record,
                report_type=report_type,
                download=download,
                report_ref='cyllo_hr_incident_management.report_hr_incident_pdf'
            )
        if incident_id in total_ids:
            idx = total_ids.index(incident_id)
            return request.render(
                "cyllo_hr_incident_management.incident_requests_details", {
                    'object': current_record,
                    'incident_req': incidents.browse(incident_id),
                    'page_name': 'incident_details',
                    'prev_record': total_ids[idx - 1] if idx > 0 else False,
                    'next_record': total_ids[idx + 1] if idx < len(
                        total_ids) - 1 else False,
                })
        return request.redirect('/incident_management/create')

    @http.route(['/incident_management/create'], type='http', auth="user",
                website=True)
    def incident_request_form(self):
        """Render create incident form"""
        if not request.env.user.has_group('base.group_user'):
            return request.render("portal.portal_my_home")

        values = {
            'categories': request.env['hr.incident.category'].sudo().search([]),
            'employee_ids': request.env['hr.employee'].sudo().search([]),
            'page_name': 'create_incident',
            'is_manager': request.env.user.has_group('hr.group_hr_manager'),
        }
        return request.render(
            "cyllo_hr_incident_management.incident_request_form", values)

    @http.route(['/incident_request/submit/<int:req_id>'], type='http',
                auth="user", website=True)
    def hr_incident_submit(self, req_id):
        """ This route is called whenever the user hits the 'Submit request'
        button from each record's detailed view"""
        incident_request = request.env['hr.incident'].sudo().browse(req_id)
        incident_request.action_submit_incident_request()
        return request.render(
            'cyllo_hr_incident_management.incident_request_submitting_template')

    @http.route(['/request/incident/submit'], type='http', auth="user",
                website=True)
    def submit_incident_request(self, **kwargs):
        """ This route is called whenever the user hits the 'Submit' button
        in request form"""
        if kwargs.get('initiator'):
            incident_req = request.env['hr.incident'].sudo().create({
                'incident_initiator_id': kwargs.get('initiator'),
                'incident_category_id': kwargs.get('category_name'),
                'incident_receptor_phone': kwargs.get('phone'),
                'incident_receptor_email': kwargs.get('email'),
                'incident_receptor_id': kwargs.get('receptor'),
                'incident_description': kwargs.get('incident_desc')})
        else:
            incident_req = request.env['hr.incident'].sudo().create({
                'incident_initiator_id': request.env.user.employee_ids.id,
                'incident_category_id': kwargs.get('category_name'),
                'incident_receptor_phone': kwargs.get('phone'),
                'incident_receptor_email': kwargs.get('email'),
                'incident_receptor_id': kwargs.get('receptor'),
                'incident_description': kwargs.get('incident_desc')})
        for key, file_storage in request.httprequest.files.items(multi=True):
            if key == 'attachment_id' and isinstance(file_storage, FileStorage):
                filename = file_storage.filename
                content_type = file_storage.content_type
                request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(file_storage.read()),
                    'res_model': 'hr.incident',
                    'res_id': incident_req.id,
                    'mimetype': content_type
                })
        incident_req.action_submit_incident_request()
        return request.render("cyllo_portal.request_submit_template",
                              {'url': '/incident_management'})

    @http.route(['/employee/parent'], type='json', auth="user", website=True)
    def employee_handler(self, **kwargs):
        """
        To retrieve the parent or department manager of an employee.
        :param: Contains the 'employee_id' key with the ID of the employee.
        :return: JSON response with the name of the employee's parent or
        department manager.
        """
        employee_id = request.env['hr.employee'].sudo().browse(
            kwargs.get('employee_id'))
        receptor_id = employee_id.parent_id if employee_id.parent_id else employee_id.department_id.manager_id
        return {'receptor_id': receptor_id.name}
