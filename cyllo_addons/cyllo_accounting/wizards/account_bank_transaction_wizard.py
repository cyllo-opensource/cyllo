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
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountBankTransactionWizard(models.TransientModel):
    """Create a bank/cash transaction from the journal dashboard."""
    _name = "account.bank.transaction.wizard"
    _description = "Create Bank Transaction"

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get("default_journal_id"),
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    payment_ref = fields.Char(
        string="Payment Reference",
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )
    foreign_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Foreign Currency",
    )
    amount_currency = fields.Monetary(
        string="Amount In Currency",
        currency_field="foreign_currency_id",
    )

    @api.depends("journal_id", "journal_id.currency_id", "journal_id.company_id.currency_id")
    def _compute_currency_id(self):
        for wizard in self:
            journal = wizard.journal_id
            wizard.currency_id = journal.currency_id or journal.company_id.currency_id

    @api.onchange("amount", "currency_id", "foreign_currency_id")
    def _onchange_foreign_currency_id(self):
        for wizard in self:
            if not wizard.foreign_currency_id:
                wizard.amount_currency = 0
                continue
            if not wizard.currency_id:
                wizard.amount_currency = wizard.amount
                continue
            base_amount = wizard.amount * wizard.currency_id.inverse_rate
            wizard.amount_currency = base_amount * wizard.foreign_currency_id.rate

    def action_create_transaction(self):
        self.ensure_one()
        if not self.amount:
            raise UserError(_("Amount must be different from zero."))

        self.env["account.bank.statement.line"].create({
            "journal_id": self.journal_id.id,
            "date": self.date,
            "payment_ref": self.payment_ref,
            "partner_id": self.partner_id.id or False,
            "amount": self.amount,
            "foreign_currency_id": self.foreign_currency_id.id or False,
            "amount_currency": self.amount_currency if self.foreign_currency_id else 0,
        })

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
