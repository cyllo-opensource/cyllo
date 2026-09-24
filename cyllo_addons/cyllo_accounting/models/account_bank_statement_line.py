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
import re
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_amount

_logger = logging.getLogger(__name__)

TOLERANCE = 0.01


class AccountBankStatementLine(models.Model):
    """Save transaction id from the provider to a field"""
    _name = 'account.bank.statement.line'
    _inherit = ['account.bank.statement.line', 'mail.thread', 'mail.activity.mixin']

    provider_transaction_id = fields.Char("Provider Transaction Id", readonly=True,
                                          help="Transaction ID from the payment provider",
                                          index=True)

    tax_ids = fields.Many2many(comodel_name='account.tax', string='Taxes',
                               tracking=True,
                               help="Taxes associated with this statement line")
    reconcile_data_json = fields.Json(string='Reconciliation Data',
                                      help="JSON data storing reconciliation information")
    account_id = fields.Many2one("account.account", compute="_compute_account_id",
                                 string="Account", tracking=True,
                                 help="Account derived from the associated move line")
    reconcile_session_data = fields.Json(string='Reconciliation Session Data',
                                         help="Temporary data for reconciliation session")
    payment_ref = fields.Char(string='Label',
                              tracking=True)
    amount_currency = fields.Monetary(
        compute='_compute_amount_currency', store=True, readonly=False,
        string="Amount in Currency",
        currency_field='foreign_currency_id',
        tracking=True,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner', ondelete='restrict',
        tracking=True,
        domain="['|', ('parent_id','=', False), ('is_company','=',True)]",
        check_company=True)
    foreign_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Foreign Currency",
        tracking=True,
        help="The optional other currency if it is a multi-currency entry.",
    )
    amount_in_base = fields.Monetary(compute="_compute_amount_in_base",
                                     tracking=True,
                                     help="Amount stored in company currency",
                                     store=True)
    currency_rate = fields.Float(compute="_compute_currency_rate",
                                 help="Exchange rate when created",
                                 store=True)
    foreign_currency_rate = fields.Float(compute="_compute_foreign_currency_rate",
                                         help="Exchange rate when created",
                                         store=True)

    @api.depends('foreign_currency_id')
    def _compute_foreign_currency_rate(self):
        """Compute currency rate when saved"""
        for rec in self:
            rec.foreign_currency_rate = rec.foreign_currency_id.with_company(rec.company_id).rate if rec.foreign_currency_id else 0

    @api.depends('currency_id')
    def _compute_currency_rate(self):
        """Compute currency rate when saved"""
        for rec in self:
            rec.currency_rate = rec.currency_id.with_company(rec.company_id).rate

    @api.depends('amount')
    def _compute_amount_in_base(self):
        """Compute the amount in company currency"""
        for rec in self:
            rec.amount_in_base = rec.amount * rec.currency_id.with_company(rec.company_id).inverse_rate if rec.currency_id != rec.company_currency_id else rec.amount

    def _compute_account_id(self):
        """Compute account field for statement from move."""
        for rec in self:
            line_ids = rec.move_id.line_ids
            if line_ids:
                rec.account_id = line_ids[0].account_id
            else:
                rec.account_id = False

    @api.model_create_multi
    def create(self, vals_list):
        """Create statement lines and attempt automatic validation.

            Args:
                vals_list (list): List of dictionaries with field values

            Returns:
                AccountBankStatementLine: Created records
            """
        res = super().create(vals_list)
        res.action_validate_bank_bank_statement_line()
        return res

    def action_undo_reconciliation(self):
        """Update field values while undo reconciliation of statement."""
        res = super().action_undo_reconciliation()
        self.write({
            'reconcile_data_json': False,
            'reconcile_session_data': False
        })
        return res

    def check_reconcile_statement_condition(self, model):
        """Check matching moves for statement from with given model conditions and return the mathced moves."""
        amount, partner, reference, notes = self.amount, self.partner_id, self.payment_ref, self.narration

        def check_match_amount():
            return (not model.match_amount
                    or (model.match_amount == 'lower' and abs(amount) <= model.match_amount_max)
                    or (model.match_amount == 'greater' and abs(amount) >= model.match_amount_min)
                    or (model.match_amount == 'between' and
                        model.match_amount_min < abs(amount) < model.match_amount_max))

        def check_match_label():
            return (not model.match_label
                    or (model.match_label == 'contains' and model.match_label_param in reference)
                    or (model.match_label == 'not_contains' and model.match_label_param not in reference)
                    or (model.match_label == 'match_regex' and re.match(model.match_label_param, reference)))

        def check_note():
            if not notes: return True
            cleaned_notes = BeautifulSoup(notes, "html.parser").get_text()
            return (not model.match_note
                    or (model.match_note == 'contains' and model.match_note_param in cleaned_notes)
                    or (model.match_note == 'not_contains' and model.match_note_param not in cleaned_notes)
                    or (model.match_note == 'match_regex' and re.search(
                        model.match_note_param, cleaned_notes)))
        basic_conditions = check_match_amount() and check_match_label() and check_note()
        if not basic_conditions:
            return False
        if model.match_partner:
            has_partner_ids = bool(model.match_partner_ids)
            has_category_ids = bool(model.match_partner_category_ids)
            if has_partner_ids and not has_category_ids:
                return partner and partner in model.match_partner_ids
            elif not has_partner_ids and has_category_ids:
                return partner and partner.category_id and any(
                    categ_id in model.match_partner_category_ids.ids for categ_id in
                    partner.category_id.ids
                )
            elif has_partner_ids and has_category_ids:
                partner_match = partner in model.match_partner_ids
                category_match = partner.category_id and any(
                    categ_id in model.match_partner_category_ids.ids for categ_id in
                    partner.category_id.ids
                )
                return partner_match or category_match
            else:
                return True
        return True

    def check_journal_entries_condition(self, model, move_lines):
        """Check move lines conditions with given model."""
        partner = self.partner_id if self.partner_id else False

        def check_monthly_limit(line):
            limit_date = fields.Date.today() - relativedelta(months=model.past_months_limit)
            return not model.past_months_limit or (line.invoice_date or line.date) >= limit_date

        def check_label_checkbox(line):
            return (not (
                    model.rule_type == 'invoice_matching' and model.match_text_location_label)
                    or line.name == self.payment_ref or line.amount_residual == self.amount
                    or check_monthly_limit(line))

        def check_payment_tolerance(line):
            """
            Filter lines based on payment tolerance and return only the line with the highest amount_residual.
            """
            filtered_lines = []

            if model.rule_type == 'invoice_matching' and model.allow_payment_tolerance:
                if model.payment_tolerance_type == 'percentage':
                    tolerance = line.amount_residual * (model.payment_tolerance_param / 100)
                elif model.payment_tolerance_type == 'fixed_amount':
                    tolerance = model.payment_tolerance_param
                else:
                    tolerance = 0  # Default case

                difference = abs(line.amount_residual - self.amount)
                if difference <= tolerance:
                    filtered_lines.append(line)

                # Return the line with the highest amount_residual if filtered_lines is not empty
                if filtered_lines:
                    return max(filtered_lines, key=lambda l: l.amount_residual)
                return False
            else:
                return line

        def find_matching_lines(lines, target_amount):
            amount, matched_lines = 0, []
            for line in lines:
                amount += line.amount_residual
                matched_lines.append(line.id)
                if abs(amount) >= abs(target_amount): break
            return matched_lines, target_amount - amount

        matching_order = model.matching_order != 'old_first'
        move_lines = move_lines.filtered(lambda line: check_monthly_limit(line))
        move_lines = move_lines.filtered(lambda line: check_label_checkbox(line))
        move_lines = move_lines.filtered(lambda line: check_payment_tolerance(line))
        move_lines = move_lines.sorted(key=lambda l: (l.date_maturity, l.invoice_date or l.date, l.id),
                                       reverse=matching_order)
        matching_lines, ref_lines, remaining_amount = [], False, 0

        if self.payment_ref:
            ref_lines = move_lines.filtered(lambda line: self.payment_ref in line.name)
            matching_lines = ref_lines.filtered(
                lambda line: abs(line.amount_residual) == abs(self.amount))
            matching_lines, remaining_amount = find_matching_lines(
                ref_lines if not matching_lines else matching_lines,
                self.amount)

        if not matching_lines:
            ref_lines = move_lines - ref_lines if self.payment_ref else move_lines
            matching_lines = ref_lines.filtered(
                lambda line: abs(line.amount_residual) == abs(self.amount))
            matching_lines, remaining_amount = find_matching_lines(
                ref_lines if not matching_lines else matching_lines,
                self.amount)

        order_direction = 'desc' if matching_order else 'asc'
        order = f"date_maturity {order_direction}, invoice_date {order_direction}, id {order_direction}"
        matching_lines = self.env['account.move.line'].search_read(
            [('id', 'in', matching_lines)], self._get_move_line_read_fields,
            order=order
        )

        if remaining_amount and model.allow_payment_tolerance and model.payment_tolerance_param != 0 and matching_lines:
            for line in model.line_ids:
                counterpart_entries = self._get_counterpart_line_vals(line, model, partner,
                                                                      remaining_amount,
                                                                      self.payment_ref,
                                                                      self.move_id)
                if counterpart_entries:
                    matching_lines.extend(counterpart_entries)

        return matching_lines, remaining_amount

    def suggest_counterpart_entries(self, model):
        """Method to return counterpart entries for the transaction."""
        partner = self.partner_id
        counterpart_entries = []
        for line in model.line_ids:
            counterpart_entries.extend(
                self._get_counterpart_line_vals(line, model, partner, self.amount,
                                                self.payment_ref, self.move_id))
        return counterpart_entries

    def button_counterpart_entries(self, model, total_matched=0.0, suspense_amounts=None):
        """Method to generate counterpart entries based on the clicked button model."""
        suspense_amounts = suspense_amounts[0] if suspense_amounts else 0.0
        button_model = self.env['account.reconcile.model'].browse(model)
        button_entries = []
        for line in button_model.line_ids:
            button_entries.extend(
                self._get_counterpart_line_vals(line, button_model, self.partner_id, self.amount,
                                                self.payment_ref, self.move_id,
                                                is_counterpart=True, total_matched=total_matched,
                                                suspense_amounts=suspense_amounts))
        return button_entries

    def get_match_invoice(self):
        """Method to return matching after checking the conditions."""
        partner = self.partner_id
        if self.amount > 0:
            move_type = ('out_invoice', 'in_refund', 'entry')
            match_nature = ('match_nature', '!=', 'amount_paid')
            amount_sign = ('amount_residual', '>', 0)
        else:
            move_type = ('in_invoice', 'out_refund', 'entry')
            match_nature = ('match_nature', '!=', 'amount_received')
            amount_sign = ('amount_residual', '<', 0)
        moves_domain = [('move_type', 'in', move_type), ('parent_state', '=', 'posted'),
                        amount_sign, ('is_account_reconcile', '=', True),
                        ('partner_id', '=', partner.id),('date_maturity', '!=', False ),
                        ('company_id', '=', self.company_id.id),]
        move_lines = self.env['account.move.line'].search(moves_domain)
        reconcile_domain = [
            '|', ('match_journal_ids', '=', False),
            ('match_journal_ids', 'in', self.journal_id.id),
            ('rule_type', 'in', ('writeoff_suggestion', 'invoice_matching')), match_nature
        ]
        reconcile_model_ids = self.env['account.reconcile.model'].search(reconcile_domain,
                                                                         order="rule_type ASC, sequence ASC")
        for model in reconcile_model_ids:
            if self.check_reconcile_statement_condition(model):
                if model.rule_type == 'writeoff_suggestion':
                    return self.suggest_counterpart_entries(model), model
                else:
                    matching_invoices, remaining_amount = self.check_journal_entries_condition(
                        model, move_lines)
                    if matching_invoices:
                        return matching_invoices, model
        return False, False

    @property
    def _get_move_line_read_fields(self):
        """Return fields list of the move line."""
        return ["account_id", "partner_id", "date", "amount_residual", "move_id", "move_type",
                "amount_currency", "currency_id", "is_same_currency", "company_currency_id",
                "amount_residual_currency", "currency_rate"]

    @api.model
    def toggle_to_check(self, record_id):
        """Method to toggle to check for bank statement line."""
        record = self.browse(record_id)
        if record.to_check:
            record.write({'to_check': False})
        else:
            record.write({'to_check': True})
        return True

    def validate_transaction(self, line_ids, counter_part_lines):
        """Validate transaction by creating journal entries and reconciling.

        Args:
            line_ids: List of move line data dictionaries
            counter_part_lines: List of counterpart line data

        Returns:
            int: ID of the validated statement line

        Raises:
            ValidationError: If transaction validation fails
        """
        try:
            liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()
            bank_line = self.line_ids[0]
            bank_line_vals = {
                "move_id": bank_line.move_id.id,
                "journal_id": bank_line.journal_id.id,
                "account_id": bank_line.account_id.id,
                "partner_id": bank_line.partner_id.id if bank_line.partner_id else False,
                "statement_line_id": self.id,
                "move_name": bank_line.move_name,
                "name": bank_line.name,
                "debit": bank_line.debit,
                "credit": bank_line.credit,
                "currency_id": bank_line.currency_id.id,
                "amount_currency": bank_line.amount_currency,
            }
            unwanted_lines = [fields.Command.delete(line.id) for line in
                              liquidity_lines + suspense_lines + other_lines]
            move_id = self.move_id
            container = {"records": move_id, "self": move_id}
            with move_id._check_balanced(container):
                move_id.with_context(
                    skip_account_move_synchronization=True,
                    force_delete=True,
                    skip_invoice_sync=True, ).write({
                    "line_ids": unwanted_lines
                })
                line_vals = []
                line_vals.append((0, 0, bank_line_vals))
                AccountMoveLine = self.env['account.move.line']
                Invoices = self.env['account.move.line']
                Bills = self.env['account.move.line']
                Payments = self.env['account.move.line']
                partner_lines = []

                batch_payment_list = []

                for line in line_ids:
                    if line.get('move_id'):
                        if line.get('move_type') in ('out_invoice', 'out_refund'):
                            invoice = AccountMoveLine.browse(line.get('id'))
                            receivable_line = {
                                'account_id': invoice.account_id.id,
                                'partner_id': invoice.partner_id.id,
                                'name': invoice.name,
                                'debit': -line.get('amount_residual') if line.get(
                                    'amount_residual') < 0 else 0,
                                'credit': line.get('amount_residual') if line.get(
                                    'amount_residual') > 0 else 0,
                                'currency_id': line.get('currency_id'),
                                'amount_currency': -line.get('amount_currency'),
                            }
                            line_vals.append((0, 0, receivable_line))
                            Invoices += invoice
                        elif line.get('move_type') in ('in_invoice', 'in_refund'):
                            bill = AccountMoveLine.browse(line.get('id'))
                            payable_line = {
                                'account_id': bill.account_id.id,
                                'partner_id': bill.partner_id.id,
                                'name': bill.name,
                                'debit': -line.get('amount_residual') if line.get(
                                    'amount_residual') < 0 else 0,
                                'credit': line.get('amount_residual') if line.get(
                                    'amount_residual') > 0 else 0,
                                'currency_id': line.get('currency_id'),
                                'amount_currency': -line.get('amount_currency'),
                            }
                            line_vals.append((0, 0, payable_line))
                            Bills += bill
                        elif line.get('move_type') == 'entry':
                            payment = AccountMoveLine.browse(line.get('id'))
                            payment_line = {
                                'account_id': payment.account_id.id,
                                'partner_id': payment.partner_id.id,
                                'name': payment.name,
                                'debit': -line.get('amount_residual') if line.get(
                                    'amount_residual') < 0 else 0,
                                'credit': line.get('amount_residual') if line.get(
                                    'amount_residual') > 0 else 0,
                                'currency_id': line.get('currency_id'),
                                'amount_currency': -line.get('amount_currency'),
                            }
                            line_vals.append((0, 0, payment_line))
                            Payments += payment
                            batch_payment_list.append(payment.payment_id.id)

                    else:
                        amount_residual = line.get('amount_residual', 0)
                        amount_formatted = line.get('amount_formatted', "$0")
                        partner_line_vals = {
                            'account_id': line.get('account_id', False),
                            'partner_id': line.get('partner_id', False),
                            'name': f'Open balance of {amount_formatted}',
                            'debit': abs(amount_residual) if amount_residual < 0 else 0,
                            'credit': abs(amount_residual) if amount_residual > 0 else 0,
                            'currency_id': line.get('currency_id'),
                            'amount_currency': -line.get('amount_currency'),
                        }
                        partner_lines.append((0, 0, partner_line_vals))

                counter_part_line_ids = []
                for line in counter_part_lines:
                    amount_residual = line.get('amount_residual', 0)
                    amount_currency = -line.get('amount_currency', 0)
                    partner = line.get('partner_id', [])
                    currency = line.get('currency_id', [])
                    account = line.get('account_id', [])
                    counter_part_line_vals = {
                        'account_id': account[0] if account else False,
                        'partner_id': partner[0] if partner else False,
                        'name': line.get('payment_ref', '') or line.get('journal_label') or '',
                        'debit': -amount_residual if amount_residual < 0 else 0,
                        'credit': amount_residual if amount_residual > 0 else 0,
                        'currency_id': currency[0] if currency else self.env.company.currency_id.id,
                        'amount_currency': amount_currency if amount_currency != 0 else -amount_residual,
                        'reconcile_model_id': line.get('reconcile_model_id', False),
                    }
                    counter_part_line_ids.append((0, 0, counter_part_line_vals))

                self.move_id.write({
                    'line_ids': line_vals + partner_lines + counter_part_line_ids
                })

                if Invoices:
                    move_lines = self.move_id.line_ids.filtered(
                        lambda
                            l: l.account_id == Invoices.account_id and l.name != f'{self.move_id.id}-Partner account line'
                    )
                    (move_lines + Invoices).reconcile()
                if Bills:
                    move_lines = self.move_id.line_ids.filtered(
                        lambda
                            l: l.account_id == Bills.account_id and l.name != f'{self.move_id.id}-Partner account line'
                    )
                    (move_lines + Bills).reconcile()
                if Payments:
                    move_lines = self.move_id.line_ids.filtered(
                        lambda
                            l: l.account_id == Payments.account_id and l.name != f'{self.move_id.id}-Partner account line'
                    )
                    (move_lines + Payments).reconcile()

                    batch_payments = self.env['batch.payment'].search([
                        ('payment_ids', 'in', batch_payment_list),
                        ('state', '=', 'confirm')
                    ])
                    if batch_payments:
                        batch_payments.write({'state': 'reconciled'})

                # ==== Update Statement Line Status ====
                if self.move_id.state == 'posted':
                    self.is_reconciled = True

                return self.id
        except Exception as e:
            _logger.error("Failed to validate transaction: %s", e)
            raise ValidationError(_("Transaction validation failed: %s") % e) from e

    def _get_counterpart_line_vals(self, line, model, partner, amount, payment_ref, move_id,
                                   is_counterpart=True, total_matched=0.0,
                                   suspense_amounts=0.0):
        """
        Generate counterpart line values based on the provided parameters.

        :param line: The line from the reconcile model.
        :param model: The reconcile model.
        :param partner: The partner associated with the transaction.
        :param amount: The amount of the transaction.
        :param payment_ref: The payment reference.
        :param move_id: The move ID associated with the transaction.
        :param is_counterpart: Boolean indicating if this is a counterpart entry.
        :return: A list of dictionaries containing the counterpart line values.
        """
        tax_amount = 0.0
        counterpart_amount = 0.0
        reference = self.payment_ref
        tax_rate = sum(line.tax_ids.mapped('amount')) / 100

        if line.amount_type == 'fixed':
            counterpart_amount = float(line.amount_string)
        elif line.amount_type == 'percentage_st_line':
            counterpart_amount = (amount * float(line.amount_string) / 100)
        elif line.amount_type == 'percentage':
            balance = amount - (total_matched - suspense_amounts)
            for prev_line in model.line_ids:
                if prev_line.sequence < line.sequence or (prev_line.sequence == line.sequence and prev_line.id < line.id):
                    prev_entries = self._get_counterpart_line_vals(
                        prev_line, model, partner, amount, payment_ref, move_id, is_counterpart=is_counterpart, total_matched=total_matched
                    )
                    balance -= sum(entry.get('amount_residual', 0.0) for entry in prev_entries)
            counterpart_amount = (balance * float(line.amount_string) / 100)
        elif line.amount_type == 'regex':
            match = re.search(line.amount_string, payment_ref)
            if match:
                sign = 1 if amount > 0.0 else -1
                decimal_separator = re.escape(model.decimal_separator)  # Escape special characters
                try:
                    # Extract the matched group if available, else use the full match
                    extracted_text = match.group(1) if match.lastindex else match.group(0)

                    # Find a numeric pattern with optional decimal separators
                    number_match = re.search(rf"\d+{decimal_separator}?\d*", extracted_text)

                    if number_match:
                        extracted_balance = float(
                            number_match.group().replace(model.decimal_separator, '.'))
                        counterpart_amount = extracted_balance * sign
                    else:
                        counterpart_amount = 0.0
                except ValueError:
                    counterpart_amount = 0.0
            else:
                counterpart_amount = 0.0

        if counterpart_amount != 0:
            amount_before_tax = counterpart_amount
            counterpart_amount /= (1 + tax_rate)
            analytic_names = []
            if line.analytic_distribution:
                for analytic_id, percentage in line.analytic_distribution.items():
                    analytic_account = self.env['account.analytic.account'].browse(int(analytic_id))
                    analytic_names.append(f"{analytic_account.name}")
            analytic_display = ", ".join(analytic_names) if analytic_names else ""
            counterpart_entries = [{
                'counterpart_id': line.id,
                'account_id': [line.account_id.id,
                               f"{line.account_id.code} {line.account_id.name}"],
                'journal_label': line.label,
                'payment_ref': reference,
                'amount_residual': round(counterpart_amount, 2),
                'amount_before_tax': amount_before_tax,
                'tax_amount': tax_amount,
                'partner_id': [partner.id if partner else False,
                               partner.name if partner else False],
                'analytic': analytic_display,
                'is_counterpart': is_counterpart,
                'move_id': move_id.id,
                'tax_ids': self.env['account.tax'].search_read([('id', 'in', line.tax_ids.ids)],
                                                               ["name"]),
                'reconcile_model_id': model.id,
            }]

            for tax in line.tax_ids:
                tax_amount = counterpart_amount * (tax.amount / 100)
                tax_account = tax.invoice_repartition_line_ids.filtered(
                    lambda r: r.repartition_type == 'tax' and r.account_id
                ).mapped('account_id')
                counterpart_entries.append({
                    'counterpart_id': line.id,
                    'tax_id': tax.id,
                    'account_id': [tax_account.id,
                                   f"{tax_account.code} {tax_account.name}"] if tax_account else [
                        line.account_id.id, f"{line.account_id.code} {line.account_id.name}"],
                    'payment_ref': reference,
                    'amount_residual': round(tax_amount, 2),
                    'partner_id': [partner.id if partner else False,
                                   partner.name if partner else False],
                    'tax_rate': tax_rate * 100,
                    'tax_amount': tax.amount,
                    'is_counterpart': is_counterpart,
                    'move_id': move_id.id,
                    'reconcile_model_id': model.id,
                })
            return counterpart_entries
        return []

    def update_statement_line_fields(self, fields_data):
        """Method to update bank statement line record field through manual operation."""
        partner_data = fields_data.get('partner_id', [])
        if partner_data:
            partner_id = partner_data[0]
            if partner_id:
                self.write({
                    'partner_id': partner_id
                })
        else:
            self.write(fields_data)

    def action_validate_bank_bank_statement_line(self):
        """Method to get matching lines for statement and validate."""
        try:
            for line in self:
                matching_moves, model = line.get_match_invoice()
                if not matching_moves or not model:
                    continue
                if not model.auto_reconcile:
                    continue
                moves_to_store = []
                move_lines = []
                counterpart_lines = []
                statement_amount = line.amount
                total_amount = 0
                for move in matching_moves:
                    date = move.get('date', False)
                    if date:
                        move.update({
                            'date': date.isoformat()
                        })

                    if move.get('id', False):
                        remaining_amount = statement_amount - total_amount
                        line_amount = move.get('amount_residual', 0)
                        currency_id = self.env['res.currency'].browse(move.get('currency_id')[0])
                        currency_rate = move.get('currency_rate', 1)

                        if abs(remaining_amount) >= abs(line_amount):
                            used_amount = line_amount
                        else:
                            if statement_amount > 0:
                                used_amount = remaining_amount if line_amount > 0 else -remaining_amount
                            else:
                                used_amount = remaining_amount if line_amount < 0 else -remaining_amount

                        move_lines.append({
                            'id': move.get('id', False),
                            'account_id': move.get('account_id', ())[0] if move.get('account_id',
                                                                                    False) else False,
                            'amount_residual': used_amount,
                            'move_id': move.get('move_id', ())[0] if move.get('move_id',
                                                                              False) else False,
                            'partner_id': move.get('partner_id', ())[0] if move.get('partner_id',
                                                                                    False) else False,
                            'name': move.get('move_id', ())[1] if move.get('move_id',
                                                                           False) else False,
                            'move_type': move.get('move_type', ''),
                            'amount_formatted': format_amount(
                                self.env,
                                used_amount,
                                currency_id
                            ),
                            'foreign_currency_id': move.get(
                                'foreign_currency_id', ()
                            )[0] if move.get('foreign_currency_id', False) else False,
                            'currency_id': currency_id.id,
                            'amount_currency': used_amount * currency_rate,
                        })
                        move.update({
                            'amount_residual': used_amount
                        })
                        if used_amount != 0:
                            moves_to_store.append(move)
                        total_amount += used_amount

                        if abs(total_amount - statement_amount) < TOLERANCE:
                            break

                    else:
                        remaining_amount = statement_amount - total_amount
                        line_amount = move.get('amount_residual', 0)

                        if abs(remaining_amount) >= abs(line_amount):
                            used_amount = line_amount
                        else:
                            used_amount = remaining_amount

                        counterpart_lines.append({
                            'counterpart_id': move.get('counterpart_id', False),
                            'account_id': move.get('account_id', []),
                            'journal_label': move.get('journal_label', ''),
                            'payment_ref': move.get('payment_ref', ''),
                            'amount_residual': used_amount,
                            'amount_before_tax': move.get('amount_before_tax', 0),
                            'tax_amount': move.get('tax_amount', 0),
                            'partner_id': move.get('partner_id', []),
                            'analytic': move.get('analytic', ''),
                            'is_counterpart': move.get('is_counterpart', False),
                            'move_id': move.get('move_id', False),
                            'tax_ids': move.get('tax_ids', [])
                        })
                        move.update({
                            'amount_residual': used_amount
                        })
                        if used_amount != 0:
                            moves_to_store.append(move)
                        total_amount += used_amount

                        if abs(total_amount - statement_amount) < TOLERANCE:
                            break

                if abs(total_amount - statement_amount) > TOLERANCE:
                    _logger.warning(f"Amount mismatch for statement line {line.id}: "
                                    f"total={total_amount}, statement={statement_amount}")
                    continue

                line.validate_transaction(move_lines, counterpart_lines)
                line.write({
                    'reconcile_data_json': {
                        'data': moves_to_store
                    }
                })
        except Exception as e:
            _logger.error(f"Failed to validate statement :{e}")

    def cron_reconcile_bank_bank_statement_line(self):
        """Cron method to validate all reconciliable statements."""
        records = self.search([('is_reconciled', '=', False)])
        records.action_validate_bank_bank_statement_line()
