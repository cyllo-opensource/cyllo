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


class InstallmentPayment(models.TransientModel):
    """Wizard for Installment Payment"""
    _name = 'installment.payment'
    _description = 'Installment Payment'

    communication = fields.Char(string="Memo", help="Reference")
    pay_amount = fields.Float(string="Installment Pay Amount",
                              help="Installment amount to pay")
    currency_id = fields.Many2one(comodel_name="res.currency")
    partner_id = fields.Many2one(comodel_name="res.partner")
    date = fields.Date(string="Payment Date")
    company_id = fields.Many2one("res.company")

    journal_id = fields.Many2one("account.journal",
                                 compute="_compute_journal_id", store=True,
                                 readonly=False,
                                 precompute=True, check_company=True,
                                 help="Journal for the payment")
    payment_method_line_id = fields.Many2one('account.payment.method.line',
                                             string='Payment Method',
                                             store=True,
                                             compute='_compute_payment_method_line_id',
                                             help="Payment method line for the payment")

    @api.constrains('date')
    def _check_date(self):
        """Validation for payment date"""
        for rec in self:
            if rec.date and rec.date < fields.Date.today():
                raise ValidationError(
                    _("The Payment Date cannot be in the past."))

    def default_get(self, fields_list):
        """Default values to the wizards"""
        res = super(InstallmentPayment, self).default_get(fields_list)
        res["currency_id"] = self.env.user.company_id.currency_id.id
        res["company_id"] = self.env.user.company_id.id
        installment_id = self.env["account.installment"].browse(
            self._context.get("active_id"))
        if installment_id:
            res["communication"] = installment_id.move_id.name
            res["pay_amount"] = installment_id.pay_amount
            res["partner_id"] = installment_id.move_id.partner_id.id
            res[
                "currency_id"] = installment_id.move_id.currency_id.id if installment_id.move_id.currency_id \
                else self.env.user.company_id.currency_id.id
            res["company_id"] = installment_id.move_id.company_id.id if installment_id.move_id.company_id \
                else self.env.user.company_id.id
            res["date"] = installment_id.payment_date if installment_id.payment_date and installment_id.payment_date >= fields.Date.today() else fields.Date.today()
        return res

    @api.depends('company_id')
    def _compute_journal_id(self):
        """Compute the default journal for the current company"""
        for wizard in self:
            if not wizard.company_id:
                wizard.journal_id = False
                continue
            domain = [
                *self.env['account.journal']._check_company_domain(
                    wizard.company_id),
                ('type', 'in', ('bank', 'cash'))
            ]
            wizard.journal_id = self.env['account.journal'].search(domain,
                                                                   limit=1)

    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        """Compute the payment method line based on the journal"""
        for wizard in self:
            if wizard.journal_id:
                if self._context.get("type") == 'sale':
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines(
                        'inbound')
                else:
                    available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines(
                        'outbound')
            else:
                available_payment_method_lines = False

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[
                    0]._origin
            else:
                wizard.payment_method_line_id = False

    def action_validate_payment(self):
        """Button: Create Payment , Creates new payment with wizards values"""
        installment_id = self.env["account.installment"].browse(
            self._context.get("active_id"))
        if self.date < fields.Date.today():
            raise ValidationError(_("The Payment Date cannot be in the past."))
        payment = self.env['account.payment'].create({
            'partner_id': installment_id.move_id.partner_id.commercial_partner_id.id,
            'company_id': self.company_id.id if self.company_id else self.env.user.company_id.id,
            'date': self.date,
            'amount': self.pay_amount,
            'currency_id': self.currency_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'ref': _("%s - Installment Payment",
                     installment_id.move_id.name) if not installment_id.is_advance else _(
                "%s - Advance Payment", installment_id.move_id.name),
        })
        payment.action_post()
        move_lines = payment.line_ids
        for line in move_lines:
            installment_id.move_id.js_assign_outstanding_line(line.id)
        installment_id.write({'state': 'paid'})
