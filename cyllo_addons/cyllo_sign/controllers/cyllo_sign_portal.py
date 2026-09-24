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

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers import portal


class SignRequestPortal(portal.PaymentPortal):
    """Class to define all the details needed for the portal view."""

    @http.route(['/sign_request'], type='http', auth="user", website=True)
    def get_my_sign_requests(self):
        """Route handler for retrieving sign requests assigned to the current user."""
        sign_requester = request.env['sign.requester'].sudo().search([('partner_id', '=', request.env.user.partner_id.id)]).request_id.ids
        my_sign_requests = request.env['sign.request'].sudo().browse(sign_requester)

        draft_sign_requests = my_sign_requests.filtered(lambda r: r.state == 'draft')
        sent_sign_requests = my_sign_requests.filtered(lambda r: r.state == 'partial')
        signed_sign_requests = my_sign_requests.filtered(lambda r: r.state == 'signed')
        cancel_sign_requests = my_sign_requests.filtered(lambda r: r.state == 'cancel')

        values = {
            'sign_requests': my_sign_requests,
            'sign_request_count': len(my_sign_requests),
            'draft_sign_requests': draft_sign_requests,
            'draft_sign_requests_count': len(draft_sign_requests),
            'sent_sign_requests': sent_sign_requests,
            'sent_sign_requests_count': len(sent_sign_requests),
            'signed_sign_requests': signed_sign_requests,
            'signed_sign_requests_count': len(signed_sign_requests),
            'cancel_sign_requests': cancel_sign_requests,
            'cancel_sign_requests_count': len(cancel_sign_requests),
            'page_name': 'sign_request'
        }
        return request.render("cyllo_sign.sign_request_template", values)

    @http.route(['/sign_request/details/<int:request_id>'], type='http', auth="user", website=True)
    def get_sign_requests_details(self, request_id, report_type=None, access_token=None, download=True):
        """Route handler for retrieving details of a specific sign request."""
        try:
            current_record = self._document_check_access('sign.request', request_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        total_record = request.env['sign.requester'].sudo().search([('partner_id', '=', request.env.user.partner_id.id)]).request_id.ids
        if request_id in total_record:
            index = total_record.index(request_id)
        return request.render("cyllo_sign.sign_request_details", {
            'object': current_record,
            'signed': [rec.signed_on for rec in current_record.requester_ids],
            'sign_request': request.env['sign.request'].sudo().browse(
                request_id),
            'page_name': 'sign_request_details',
            'prev_record': total_record[index - 1] if index > 0 else False,
            'next_record': total_record[index + 1] if index < len(
                total_record) - 1 else False
        })

    @http.route(['/sign_request/sign/<int:request_id>'], type='http',
                auth="user", website=True)
    def action_sign_requests(self, request_id, report_type=None,
                             access_token=None, download=True):
        """ This route is called whenever the user clicks on 'Helpdesk Ticket'
        menu in website"""
        try:
            current_record = self._document_check_access('sign.request',
                                                         request_id,
                                                         access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        signer = current_record.requester_ids.partner_id.ids
        if current_record.env.user.partner_id.id not in signer:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "You are not allowed to sign, you are not added in the signers list"),
                    'type': 'warning',
                },
            }
        line = current_record.requester_ids.filtered(
            lambda r: r.partner_id == request.env.user.partner_id)
        return {
            "type": "ir.actions.client",
            "tag": "sign_configure",
            "name": current_record.template_id.name,
            "params": {
                "res_model": current_record.template_id._name,
                "res_id": current_record.template_id.id,
                "to_sign": True,
                "request_id": current_record.id,
                "requester_ids": current_record.requester_ids.id,
                "role": line.role_id.name,
            },
        }

    @http.route(['/sign_request/refuse/<int:request_id>'], type='http',
                auth="user", website=True)
    def action_refuse_requests(self, request_id):
        # Fetch the record
        sign_request = request.env['sign.request'].sudo().browse(request_id)
        if sign_request.exists():
            sign_request.state = 'cancel'
            request.env.cr.commit()  # Commit the transaction if needed (usually auto-handled)
            return request.redirect(f'/sign_request/details/{request_id}')
        return request.redirect('/sign_request')

    @http.route(['/web/portal/sign'], type='http', auth='user')
    def portal_sign(self):
        """
        Endpoint for handling signing requests in the web portal.
        :return: A rendered view containing information necessary for signing.
        """
        return request.render('cyllo_sign.root', {
            'res_id': request.params.get('res_id'),
            'request_id': request.params.get('request_id'),
            'to_sign': request.params.get('to_sign'),
            'requester_ids': request.params.get('requester_ids'),
            'role': request.params.get('role'),
            'res_model': request.params.get('res_model'),
        })

    @http.route(['/web/sign/download'], type='http', auth='user')
    def portal_sign_download(self):
        """
        Endpoint for downloading signed documents from the web portal.
        :return: A response containing the signed document.
        """
        sign_request = request.env['sign.request'].sudo().browse(
            int(request.params.get('res_id')))

        if sign_request and sign_request.data:
            data = base64.b64decode(sign_request.data)
            filename = f"{sign_request.name}"
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', http.content_disposition(filename))
            ]
            return request.make_response(data, headers=headers)
        else:
            return http.Response("Sign request not found or data missing.",
                                 status=404)
