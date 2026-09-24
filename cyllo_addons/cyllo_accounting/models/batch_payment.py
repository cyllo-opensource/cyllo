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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BatchPayment(models.Model):
    """Model for batch payment"""
    _name = "batch.payment"
    _description = "Batch Payment"

    name = fields.Char(
        string='Batch Reference', required=True, readonly=True,
        default=lambda self: _('New'))
    batch_type = fields.Selection(
        selection=[
            ('outbound', 'Send'),
            ('inbound', 'Receive')],
        readonly=False, default='outbound',
        help="Used to set send or receive")
    journal_id = fields.Many2one(
        'account.journal', domain=[('type', '=', 'bank')], string="Bank")
    date = fields.Date(default=fields.Date.context_today, string="Date")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('reconciled', 'Reconciled')],
        default="draft", readonly=False, help="Used to set state")
    payment_method = fields.Char('Payment Method',
                                 related='payment_ids.payment_method_line_id.name')
    payment_ids = fields.Many2many(
        'account.payment',
        string="Payment Methods",
        required=True,
        domain="[('payment_type', '=', batch_type), ('state', '=', 'posted'), ('journal_id', '=', journal_id), ('batch_payment_id', '=', False)]"
    )
    total_amount = fields.Monetary(
        compute="_compute_total_amount", store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='payment_ids.currency_id',
        readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

    @api.depends('payment_ids')
    def _compute_total_amount(self):
        """Compute total amount from unreconciled payments only"""
        for record in self:
            valid_payments = record.payment_ids.filtered(lambda p: p.amount > 0)
            amount = sum(valid_payments.mapped('amount'))
            record.total_amount = -amount if record.batch_type == 'outbound' else amount

    @api.onchange('batch_type', 'journal_id')
    def _onchange_batch_type(self):
        """Filter payments dynamically based on batch type and journal"""
        self.payment_ids = False
        self.payment_method = False
        domain = [('state', '=', 'posted'),
                  ('is_reconciled', '=', False),
                  ('batch_payment_id', '=', False)]
        if self.batch_type:
            domain.append(('payment_type', '=', self.batch_type))
        if self.journal_id:
            domain.append(('journal_id', '=', self.journal_id.id))
        else:
            domain = [('id', '=',
                       False)]

        return {'domain': {'payment_ids': domain}}

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'batch.payment') or _('New')
        return super(BatchPayment, self).create(vals)

    def action_create_batch(self):
        """Create batch with selected payments and move to confirm state."""
        zero_amount_payments = self.payment_ids.filtered(
            lambda p: p.amount <= 0)
        if zero_amount_payments:
            raise ValidationError(_(
                'You cannot add payments with zero amount in a Batch Payment.'
            ))

        self.state = 'confirm'
        self.payment_ids.write({'batch_payment_id': self.id})

    def reset_to_draft(self):
        """Method to reset the batch payment to draft state."""
        self.payment_ids.write({
            'batch_payment_id': False
        })
        self.write({
            'state': 'draft'
        })
