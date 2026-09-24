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
from odoo import _, api, models


class AccountPaymentRegister(models.TransientModel):
    """Inherit the register payment wizard """
    _inherit = 'account.payment.register'

    @api.model
    def _prepare_account_move_vals(self, payment):
        """Account move values"""
        self.ensure_one()
        move_vals = {
            "move_type": "entry",
            "journal_id": payment.journal_id.id,
            "date": payment.date,
            "ref": _("Payment %s") % payment.name,
            "company_id": payment.company_id.id,
        }
        return move_vals

    @api.model
    def _prepare_move_line_vals(self, line):
        """Account move line values"""
        assert line.credit > 0, "Credit must have a value"
        return {
            "name": line.ref and _("Payment Ref. %s") % line.ref or False,
            "debit": line.credit,
            "credit": 0.0,
            "account_id": line.account_id.id,
            "partner_id": line.partner_id.id,
            "currency_id": line.currency_id.id or False,
            "amount_currency": line.amount_currency * -1,
        }

    def _prepare_counterpart_move_lines_vals(self, total_credit,
                                             total_amount_currency):
        """Counterpart move line values"""
        self.ensure_one()
        account_id = False
        if not account_id:
            account_id = self.company_id.account_journal_payment_credit_account_id.id
        return {
            "debit": 0.0,
            "credit": total_credit,
            "account_id": account_id,
            "partner_id": False,
            "currency_id": self.currency_id.id or False,
            "amount_currency": total_amount_currency,
        }

    def _create_payments(self):
        """Adding more features to the wizard"""
        res = super(AccountPaymentRegister, self)._create_payments()
        for rec in self:
            account_move_obj = self.env["account.move"]
            account_move_line_obj = self.env["account.move.line"]
            for payment in res:
                if rec.payment_method_line_id.code == 'credit_payment':
                    credit_payment_ids = self.env['account.move.line'].search(
                        [('reconciled', '=', False), ('credit', '>', 0),
                         ('parent_state', '=', 'posted'),
                         ('payment_id', '=', payment.id)])
                    move = account_move_obj.create(
                        rec._prepare_account_move_vals(payment))
                    total_credit = 0.0
                    total_amount_currency = 0.0
                    to_reconcile_lines = []
                    for line in credit_payment_ids:
                        total_credit += line.credit
                        total_amount_currency += line.amount_currency
                        line_vals = self._prepare_move_line_vals(line)
                        line_vals["move_id"] = move.id
                        move_line = account_move_line_obj.with_context(
                            check_move_validity=False).create(line_vals)
                        to_reconcile_lines.append(line + move_line)
                    counter_vals = rec._prepare_counterpart_move_lines_vals(
                        total_credit, total_amount_currency)
                    counter_vals["move_id"] = move.id
                    account_move_line_obj.create(counter_vals)
                    move.action_post()
                    for reconcile_lines in to_reconcile_lines:
                        reconcile_lines.reconcile()
        return res
