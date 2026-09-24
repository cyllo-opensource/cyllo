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
import logging
import requests

from odoo import http
from odoo.http import request

saltedge_domain = "https://www.saltedge.com/api/v5/"
_logger = logging.getLogger(__name__)


class BankConnection(http.Controller):
    """For getting Saltedge connection id from the redirect url"""

    @http.route(
        [
            "/connection",
        ],
        methods=["GET"],
        type="http",
        auth="public",
        website=True
    )
    def get_connection_details(self, connection_id=None, **kwargs):
        """Get connection details such as provider name,
         customer id, status etc from the response."""
        saltedge_app_id = request.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_app_id')
        saltedge_secret_key = request.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_secret_key')
        if connection_id and saltedge_app_id and saltedge_secret_key:
            # To get the connection
            url = saltedge_domain + "connections/" + connection_id
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "App-id": saltedge_app_id,
                "Secret": saltedge_secret_key,
            }
            response = requests.get(url, headers=headers, params={})
            if 'data' in response.json():
                connection_data = response.json().get('data')
                if 'customer_id' in connection_data:
                    online_bank_provider_id = request.env['online.bank.provider'].sudo().search(
                        [('saltedge_customer_id', '=', connection_data.get('customer_id'))], limit=1)
                    if online_bank_provider_id:
                        online_bank_provider_id.saltedge_connection_id = request.env['saltedge.connection'].create({
                            'name': connection_data.get('provider_name'),
                            'bank_provider_id': online_bank_provider_id.id,
                            'connection_id': connection_id,
                            'country_code': connection_data.get('country_code'),
                            'status': connection_data.get('status'),
                        })
                        online_bank_provider_id.state = 'connect'
                        # To get the accounts from the connection
                        account_url = saltedge_domain + "accounts?connection_id=" + connection_id
                        account_response = requests.get(account_url, headers=headers,
                                                        params={'connection_id': connection_id})
                        if 'data' in account_response.json():
                            for account in account_response.json().get('data'):
                                # Creates new journal based on the accounts from the provider
                                request.env['account.journal'].sudo().create({
                                        'type': 'bank',
                                        'name': account.get('name'),
                                        'online_bank_provider_id': online_bank_provider_id.id,
                                        'saltedge_account_id': account.get('id'),
                                        'company_id': online_bank_provider_id.company_id.id
                                })

        return request.redirect('/')
