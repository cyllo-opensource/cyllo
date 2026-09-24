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
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountReturn(models.Model):
    """
    Account Return Model
    This model represents a tax return for a specific period.
    It computes tax amounts from posted journal items
    (account.move.line with tax_line_id)
    and creates a settlement journal entry.
    """

    _name = 'account.return'
    _description = 'Tax Return'
    _order = 'date_from desc'

    name = fields.Char(string="Reference", required=True, copy=False, default="New",
                       help="Unique reference for this tax return.")
    periodicity = fields.Selection([('monthly', 'Monthly'), ('bi_monthly', 'Every 2 months'),
                                    ('quarterly', 'Quarterly'), ('four_months', 'Every 4 months'),
                                    ('semi_annually', 'Semi-annually'), ('annually', 'Annually'),
                                    ('fiscal_year', 'Fiscal Year'), ], required=True,
                                   help="Defines how often the tax return is filed.")
    date_from = fields.Date(required=True, help="Start date of the tax return period.")
    date_to = fields.Date(required=True, help="End date of the tax return period.")
    journal_id = fields.Many2one('account.journal', string="Settlement Journal",
                                 domain="[('type','=','general')]", required=True,
                                 help="Journal used to create the tax settlement entry.")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True,
                                 help="Company for which this tax return is generated.")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True,
                                  help="Currency used for tax computation.")
    is_tax_return = fields.Boolean(default=True, help="Technical flag to identify tax return records.")
    output_tax = fields.Monetary(string="Output Tax", currency_field='currency_id', readonly=True,
                                 help="Total sales tax collected during the selected period.")
    input_tax = fields.Monetary(string="Input Tax", currency_field='currency_id', readonly=True,
                                help="Total purchase tax paid during the selected period.")
    net_tax = fields.Monetary(string="Net Tax", currency_field='currency_id', readonly=True,
                              help="Difference between Output Tax and Input Tax. If positive, tax is payable. "
                                   "If negative, tax is refundable.")
    balance_amount = fields.Monetary(string="Balance", currency_field='currency_id',
                                     compute='_compute_balance_amount',
                                     help="Balance including net tax of the period and any outstanding balances on tax group accounts.")
    move_id = fields.Many2one('account.move', string="Settlement Entry", readonly=True,
                              help="Journal entry created to settle this tax return.")
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')],
                             default='draft',help="Status of the tax return.")
    check_ids = fields.One2many('account.return.validation', 'return_id',
                                string="Validation Checks")

    @api.depends('net_tax', 'date_to', 'company_id', 'move_id')
    def _compute_balance_amount(self):
        for rec in self:
            if not rec.date_to:
                rec.balance_amount = rec.net_tax
                continue

            taxes = self.env['account.tax'].search([('company_id', '=', rec.company_id.id)])
            tax_groups = taxes.mapped('tax_group_id')

            existing_balance = 0.0
            if tax_groups:
                accounts = []
                for tg in tax_groups:
                    if tg.advance_tax_payment_account_id:
                        accounts.append(tg.advance_tax_payment_account_id.id)
                    if tg.tax_receivable_account_id:
                        accounts.append(tg.tax_receivable_account_id.id)
                    if tg.tax_payable_account_id:
                        accounts.append(tg.tax_payable_account_id.id)

                if accounts:
                    self.env.cr.execute("""
                        SELECT COALESCE(SUM(aml.balance), 0) AS balance
                        FROM account_move_line aml
                        LEFT JOIN account_move move ON move.id = aml.move_id
                        WHERE aml.account_id IN %s
                          AND aml.date <= %s
                          AND move.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.move_id != %s
                    """, [tuple(set(accounts)), rec.date_to, rec.company_id.id, rec.move_id.id or 0])
                    res = self.env.cr.dictfetchone()
                    existing_balance = res.get('balance') or 0.0

            rec.balance_amount = rec.net_tax - existing_balance

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Ensure date range is valid."""
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise UserError(_("Start date must be before end date."))

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_overlap(self):
        """
        Prevent overlapping tax returns for the same company.
        """
        for rec in self:
            if not rec.date_from or not rec.date_to:
                continue
            domain = [('id', '!=', rec.id), ('company_id', '=', rec.company_id.id), ('state', '!=', 'cancel'),
                      ('date_from', '<=', rec.date_to), ('date_to', '>=', rec.date_from), ]
            overlapping = self.search(domain)
            if overlapping:
                raise UserError(_("Another tax return already exists for this period (%s - %s).") % (
                overlapping[0].date_from, overlapping[0].date_to))

    def action_compute(self):
        """
        Compute tax amounts from posted journal items.
        Only tax lines (tax_line_id) are considered.
        """

        self.ensure_one()

        lines = self.env['account.move.line'].search([('tax_line_id', '!=', False), ('move_id.state', '=', 'posted'),
                                                      ('date', '>=', self.date_from), ('date', '<=', self.date_to),
                                                      ('company_id', '=', self.company_id.id), ])

        output_tax = 0.0
        input_tax = 0.0

        for line in lines:

            tax_amount = line.credit - line.debit

            if line.tax_line_id.type_tax_use == 'sale':
                output_tax += tax_amount

            elif line.tax_line_id.type_tax_use == 'purchase':
                input_tax += tax_amount

        # Store positive values for display
        self.output_tax = abs(output_tax)
        self.input_tax = abs(input_tax)

        # Net = Output - Input (this matches Cyllo)
        self.net_tax = self.output_tax - self.input_tax

    def action_validate_checks(self):
        """
        Run all related validation checks.
        """
        self.ensure_one()
        for check in self.check_ids:
            check.action_run_validation()

        failed_mandatory = self.check_ids.filtered(lambda c: c.state == 'failed' and c.is_mandatory)
        failed_optional = self.check_ids.filtered(lambda c: c.state == 'failed' and not c.is_mandatory)

        if failed_mandatory or failed_optional:
            messages = []
            if failed_mandatory:
                messages.append(_("Mandatory failures:\n%s") % "\n".join(
                    [f"- {c.name}: {c.result_message}" for c in failed_mandatory]))
            if failed_optional:
                messages.append(_("Optional warnings:\n%s") % "\n".join(
                    [f"- {c.name}: {c.result_message}" for c in failed_optional]))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Validation Results'),
                    'message': "\n\n".join(messages),
                    'sticky': True,
                    'type': 'danger' if failed_mandatory else 'warning',
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Passed'),
                'message': _('All validation checks passed.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_post(self):
        """
        Create and post settlement journal entry.
        Generates balancing lines for each individual tax account and aggregates
        the net total per tax group into the payable or receivable account.
        """

        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_("Only draft returns can be posted."))

        if self.company_id.tax_lock_date and self.date_to <= self.company_id.tax_lock_date:
            raise UserError(_("You cannot post a tax return prior to and inclusive of the Tax Lock Date (%s).") % self.company_id.tax_lock_date)

        # Validate checks before posting
        self.action_validate_checks()
        if any(check.state == 'failed' and check.is_mandatory for check in self.check_ids):
            raise UserError(
                _("Cannot post tax return because some mandatory validation checks failed. Please review the 'Validation Checks' tab."))

        # Query all posted tax lines in this period to aggregate amounts
        self.env.cr.execute("""
            SELECT aml.tax_line_id as tax_id,
                   tax.tax_group_id as tax_group_id,
                   aml.account_id,
                   COALESCE(SUM(aml.balance), 0) as amount
            FROM account_move_line aml
            JOIN account_tax tax ON tax.id = aml.tax_line_id
            WHERE aml.company_id = %s
              AND aml.date >= %s
              AND aml.date <= %s
              AND aml.parent_state = 'posted'
            GROUP BY tax.tax_group_id, aml.tax_line_id, aml.account_id
        """, [self.company_id.id, self.date_from, self.date_to])
        results = self.env.cr.dictfetchall()

        move_lines = []
        tax_group_totals = {}

        # Step 1: Add balancing lines for each tax account
        for line in results:
            tax_group_id = line['tax_group_id']
            account_id = line['account_id']
            amount = line['amount']
            tax_id = line['tax_id']

            if not amount:
                continue

            # Accumulate net amount per tax group
            tax_group_totals[tax_group_id] = tax_group_totals.get(tax_group_id, 0.0) + amount

            tax = self.env['account.tax'].browse(tax_id)
            tax_name = tax.name

            move_lines.append((0, 0, {
                'name': _('Tax Closing - %s') % tax_name,
                'account_id': account_id,
                'debit': abs(amount) if amount < 0 else 0.0,
                'credit': amount if amount > 0 else 0.0,
            }))

        # Step 2: Add lines for each tax group's payable / receivable account, considering existing balances
        tax_group_subtotal = {}
        currency = self.company_id.currency_id or self.env.company.currency_id

        for tax_group_id, total in tax_group_totals.items():
            if currency.is_zero(total):
                continue
            tax_group = self.env['account.tax.group'].browse(tax_group_id)
            if not tax_group:
                continue
            if not tax_group.tax_payable_account_id or not tax_group.tax_receivable_account_id:
                raise UserError(_("Please configure Payable and Receivable accounts in Tax Group: %s") % tax_group.name)

            key = (
                tax_group.advance_tax_payment_account_id.id or False,
                tax_group.tax_receivable_account_id.id,
                tax_group.tax_payable_account_id.id
            )
            tax_group_subtotal[key] = tax_group_subtotal.get(key, 0.0) + total

        # Query existing balances on those accounts
        sql_account = '''
            SELECT SUM(aml.balance) AS balance
            FROM account_move_line aml
            LEFT JOIN account_move move ON move.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.date <= %s
              AND move.state = 'posted'
              AND aml.company_id = %s
        '''

        def _add_line(account, name):
            self.env.cr.execute(sql_account, (
                account,
                self.date_to,
                self.company_id.id,
            ))
            result = self.env.cr.dictfetchone()
            advance_balance = result.get('balance') or 0
            if not currency.is_zero(advance_balance):
                move_lines.append((0, 0, {
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0.0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0.0,
                    'account_id': account
                }))
            return advance_balance

        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'))
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'))
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'))
                account_already_balanced.append(key[2])

            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                move_lines.append((0, 0, {
                    'name': _('Payable tax amount') if total < 0 else _('Receivable tax amount'),
                    'debit': total if total > 0 else 0.0,
                    'credit': abs(total) if total < 0 else 0.0,
                    'account_id': key[2] if total < 0 else key[1]
                }))

        # Fallback: if no tax lines found in this period, but we have net_tax config, use default fallback
        if not move_lines:
            tax_group = self.env['account.tax.group'].search([], limit=1)
            if not tax_group:
                raise UserError(_("No Tax Group configured."))
            if not tax_group.tax_payable_account_id or not tax_group.tax_receivable_account_id:
                raise UserError(_("Please configure Payable and Receivable accounts in Tax Group."))

            sale_tax = self.env['account.tax'].search([
                ('company_id', '=', self.company_id.id),
                ('type_tax_use', '=', 'sale')
            ], limit=1)
            purchase_tax = self.env['account.tax'].search([
                ('company_id', '=', self.company_id.id),
                ('type_tax_use', '=', 'purchase')
            ], limit=1)

            tax_received_account = sale_tax.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').account_id or tax_group.tax_payable_account_id
            tax_paid_account = purchase_tax.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').account_id or tax_group.tax_receivable_account_id

            if self.net_tax == 0:
                amount = self.output_tax or self.input_tax or 0.0
                move_lines = [
                    (0, 0, {
                        'name': _('Tax Received - Zero Settlement'),
                        'account_id': tax_received_account.id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Tax Paid - Zero Settlement'),
                        'account_id': tax_paid_account.id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            elif self.net_tax > 0:
                amount = abs(self.net_tax)
                move_lines = [
                    (0, 0, {
                        'name': _('Tax Received - Settlement'),
                        'account_id': tax_received_account.id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Tax Payable - %s') % tax_group.name,
                        'account_id': tax_group.tax_payable_account_id.id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            else:
                amount = abs(self.net_tax)
                move_lines = [
                    (0, 0, {
                        'name': _('Tax Receivable - %s') % tax_group.name,
                        'account_id': tax_group.tax_receivable_account_id.id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Tax Paid - Settlement'),
                        'account_id': tax_paid_account.id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]

        move = self.env['account.move'].create({
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'company_id': self.company_id.id,
            'line_ids': move_lines,
        })

        move.action_post()

        self.move_id = move.id
        self.state = 'posted'

        if not self.company_id.tax_lock_date or self.date_to > self.company_id.tax_lock_date:
            self.company_id.sudo().tax_lock_date = self.date_to

    def _revert_tax_lock_date(self):
        last_posted = self.env['account.return'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
            ('id', '!=', self.id)
        ], order='date_to desc', limit=1)
        if last_posted:
            self.company_id.sudo().tax_lock_date = last_posted.date_to
        else:
            self.company_id.sudo().tax_lock_date = False

    def action_cancel(self):
        """
        Cancel the tax return and reverse settlement entry.
        """
        self.ensure_one()

        if self.move_id:
            self.move_id.button_draft()
            self.move_id.button_cancel()

        self.state = 'cancel'
        self._revert_tax_lock_date()

    def action_draft(self):
        """
        Reset the tax return to draft.
        """
        self.ensure_one()
        if self.move_id:
            self.move_id.button_draft()
            self.move_id.button_cancel()
            move = self.move_id
            self.move_id = False
            try:
                move.unlink()
            except Exception:
                pass

        if self.check_ids:
            self.check_ids.write({
                'state': 'draft',
                'record_count': 0,
                'result_message': '',
            })

        self.state = 'draft'
        self._revert_tax_lock_date()

    def action_open_tax_return_wizard(self):
        """
        Open the Tax Return Wizard from a button.
        """
        return {
            'name': _('Tax Return Generation Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'tax.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def unlink(self):
        """
        Prevent deletion of posted returns.
        """
        for rec in self:
            if rec.state == 'posted':
                raise UserError(_("You cannot delete a posted tax return."))
        return super().unlink()
