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
from odoo.addons.portal.controllers.portal import CustomerPortal


class DocumentRequestPortal(CustomerPortal):
    """Controller handling document request counts and downloads."""

    def _prepare_home_portal_values(self, counters):
        """Prepare home portal values including document request count.
            Args:counters (dict): Dictionary of counters.
            Returns:Dictionary of values for the home portal."""
        vals = super()._prepare_home_portal_values(counters)
        if 'doc_req_count' in counters:
            vals['doc_req_count'] = request.env['document.template.request'].sudo().search_count(
                [('employee_id', '=', request.env.user.employee_id.id)])
        return vals

    @http.route(['/document_request/download/<int:order_id>'], type='http', auth="public", website=True)
    def portal_document_download(self, order_id):
        """Route to handle downloading of requested documents.
         Args:order_id (int): ID of the requested document.
         Returns:HTTP response for the requested document download."""
        document_request = request.env['document.template.request'].browse(order_id)
        return self._show_report(model=document_request, report_type='pdf',
                                 report_ref='cyllo_documents.report_document_download_pdf', download=True)
