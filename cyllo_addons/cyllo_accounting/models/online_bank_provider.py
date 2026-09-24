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
import json
import logging
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
saltedge_domain = "https://www.saltedge.com/api/v5/"


class OnlineBankProvider(models.Model):
    """For connecting online bank provider"""
    _name = "online.bank.provider"
    _inherit = ["mail.thread"]
    _description = "Online Bank Provider"

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    name = fields.Char('Identifier', required=True, help='Used to create customer on the Salt Edge provider')
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'),
                              ('connect', 'Connected'), ('cancel', 'Cancelled')],
                             'Status', readonly=True, default='draft')
    saltedge_customer_id = fields.Char('Customer Id', help='To save the customer id from the provider')
    saltedge_connection_id = fields.Many2one('saltedge.connection', string='Bank Provider',
                                             help='To save the connection details from the provider')
    bank_journal_ids = fields.One2many('account.journal', 'online_bank_provider_id',
                                       domain=[('type', '=', 'bank')], string='Bank Journals',
                                       help="All bank journals for the bank connection")

    def unlink(self):
        """It will delete the connection first then delete the record."""
        for rec in self:
            if rec.saltedge_connection_id:
                if rec.bank_journal_ids:
                    rec.bank_journal_ids.unlink()
                url = saltedge_domain + "connections/" + rec.saltedge_connection_id.connection_id
                header = rec._get_header()
                json_data = {"data": {"fetch_scopes": ["accounts", "transactions"]}}
                response = requests.delete(
                    url,
                    json=json_data,
                    headers=header,
                )
                rec.saltedge_connection_id.unlink()
            res = super(OnlineBankProvider, rec).unlink()
            return res

    def action_confirm(self):
        """Button: Confirm - Create a saltedge customer by using identifier"""
        # To create a new customer
        url = saltedge_domain + "customers/"
        json_data = {"data": {"identifier": self.name}}
        response = self._post_request(url, json_data)
        if 'data' in json.loads(response.text):
            self.saltedge_customer_id = json.loads(response.text).get('data')['id']
        else:
            raise UserError(_("Make sure your Salt Edge connection"))
        self.state = 'open'

    def pull_bank_transactions(self):
        """Server action for fetching the bank statements"""
        if self.state == 'connect':
            for journal in self.bank_journal_ids:
                journal._create_bank_statements()

    def action_connect_to_bank(self):
        """Button: Connect to Bank - To create bank connections using the customer id."""
        if self.saltedge_customer_id:
            include_fake_providers = self.env['ir.config_parameter'].sudo().get_param('saltedge.include_fake_providers')
            # To create new connect session
            url = saltedge_domain + "connect_sessions/create"
            json_data = {"data":
                {
                    "customer_id": self.saltedge_customer_id,
                    "return_connection_id": True,
                    "show_connect_overview": True,
                    "include_fake_providers": True if include_fake_providers else False,
                    "consent": {
                        "from_date": "2020-05-08",
                        "period_days": 90,
                        "scopes": ["account_details", "transactions_details"]
                    },
                    "attempt": {
                        "from_date": "2020-07-07",
                        "fetch_scopes": ["accounts", "transactions"]
                    }
                }
            }
            response = self._post_request(url, json_data)
            if 'data' in json.loads(response.text):

                return {
                    'type': 'ir.actions.act_url',
                    'url': json.loads(response.text).get('data')['connect_url'],
                    'target': 'new',
                }
            else:
                raise UserError(_("Make sure your Salt Edge connection"))
        else:
            raise UserError(_("Make sure your Salt Edge connection"))

    def action_reset_to_connect(self):
        """Button: Reset to Draft"""
        bank_journals = self.env['account.journal'].search(
            [('active', '=', False), ('online_bank_provider_id', '=', self.id)])
        for journal in bank_journals:
            journal.active = True
        self.state = 'connect'

    def action_cancel(self):
        """Button: Cancel"""
        for journal in self.bank_journal_ids:
            journal.active = False
        self.state = 'cancel'

    def _get_header(self):
        """To get the header for the request"""
        saltedge_app_id = self.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_app_id')
        saltedge_secret_key = self.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_secret_key')
        if saltedge_app_id and saltedge_secret_key:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "App-id": saltedge_app_id,
                "Secret": saltedge_secret_key,
            }
            return headers
        else:
            raise UserError(_("Make sure your Salt Edge connection: Add App Id and Secret Key from the configuration"))

    def _post_request(self, url, json_data):
        """Post request and return the json response."""
        headers = self._get_header()
        response = requests.post(
            url,
            json=json_data,
            headers=headers,
        )
        return response
