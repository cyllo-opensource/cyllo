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

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    """Add provider inside journals"""
    _inherit = "account.journal"

    online_bank_provider_id = fields.Many2one(
        string="Bank Provider",
        comodel_name="online.bank.provider",
        copy=False,
        help="Corresponding online bank provider"
    )
    saltedge_account_id = fields.Char('Saltedge Account ID',
                                      help='Account id from the salt edge provider')

    def action_new_transaction(self):
        """Open the transaction wizard from the journal dashboard."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "cyllo_accounting.account_bank_transaction_wizard_action"
        )
        action["context"] = {
            **self.env.context,
            "default_journal_id": self.id,
        }
        return action

    def _pull_bank_statements(self):
        """Scheduled action for fetching the bank statements"""
        journal_ids = self.env['account.journal'].search([('saltedge_account_id', '!=', False)])
        for journal in journal_ids:
            if journal.online_bank_provider_id.state == 'connect':
                journal._create_bank_statements()

    def _create_bank_statements(self):
        """Create bank statements and transactions based on the response of the provider"""
        saltedge_app_id = self.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_app_id')
        saltedge_secret_key = self.env['ir.config_parameter'].sudo().get_param('saltedge.saltedge_secret_key')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "App-id": saltedge_app_id,
            "Secret": saltedge_secret_key,
        }
        connection_id = self.online_bank_provider_id.saltedge_connection_id.connection_id
        if connection_id:
            # list the transactions of the bank accounts
            statement_url = "https://www.saltedge.com/api/v5/transactions?connection_id=" + connection_id + "account_id=" + self.saltedge_account_id
            response = requests.get(statement_url, headers=headers,
                                    params={'connection_id': connection_id, 'account_id': self.saltedge_account_id})
            if 'data' in response.json():
                for transaction in response.json().get('data'):
                    # Create statements for the created bank journals
                    bank_statement = self.env['account.bank.statement'].search([('journal_id', '=', self.id)],
                                                                               limit=1)
                    # Updates the currency also based on these accounts.
                    currency_id = self.env['res.currency'].search(
                        ['&', ('name', '=', transaction.get('currency_code')), '|', ('active', '=', True),
                         ('active', '=', False)])
                    if currency_id and not currency_id.active:
                        currency_id.action_unarchive()
                    if not bank_statement:
                        bank_statement = self.env['account.bank.statement'].create({
                            'name': self.name + "-" + transaction.get('made_on'),
                            'journal_id': self.id,
                            'date': transaction.get('made_on'),
                            'balance_start': 0,
                        })
                        # If not created the transactions already then will create new ones.
                    bank_statement_line = self.env['account.bank.statement.line'].search(
                        [('statement_id', '=', bank_statement.id), ('provider_transaction_id', '=', transaction.get('id'))])
                    if not bank_statement_line:
                        self.env['account.bank.statement.line'].create({
                            'date': transaction.get('made_on'),
                            'journal_id': self.id,
                            'payment_ref': transaction.get('description'),
                            'amount': transaction.get('amount'),
                            'amount_currency': transaction.get('amount') if currency_id else 0,
                            'statement_id': bank_statement.id,
                            'provider_transaction_id': transaction.get('id'),
                            'foreign_currency_id': currency_id.id if currency_id else False
                        })
