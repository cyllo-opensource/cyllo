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
from odoo.http import Controller
from odoo.http import content_disposition, request
from odoo.tools import json
from odoo.tools import html_escape


class XLSXReportController(Controller):
    """
    Controller for generating and downloading XLSX reports in Odoo.

    This controller handles the creation of XLSX reports based on a specified
    model and data. The report is returned as an Excel file that the user can
    download.
    """

    @http.route('/flow_report', type='http', auth='user',
                methods=['POST'], csrf=False)
    def get_report_xlsx(self, model, data, output_format, report_name,
                        report_action):
        """
        Generate and return an XLSX report based on the provided data and model.

        This method generates an Excel report for a specified model and data,
        then returns it as an HTTP response with the appropriate headers for
        downloading the file.

        Returns:
            werkzeug.Response: The HTTP response containing the XLSX report.
        """
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        token = 'dummy-because-api-expects-one'
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition',
                         content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_xlsx_report(data, response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
