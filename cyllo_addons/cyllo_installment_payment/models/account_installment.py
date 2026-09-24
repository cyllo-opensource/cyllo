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


class AccountInstallment(models.Model):
    """For Installment Details: this will show inside the
    new tab installment details in invoice."""
    _name = 'account.installment'
    _description = 'Account Installment'
    _rec_name = 'name'

    name = fields.Char('Description', required=True)
    payment_date = fields.Date('Payment Date',
                               help='Date for paying installment')
    sequence = fields.Integer('Sequence', default=1)
    pay_amount = fields.Float(string='Payment Amount',
                              help='Amount for payment')
    state = fields.Selection(selection=[('draft', 'Draft'), ('paid', 'Paid'),
                                        ('cancel', 'Cancelled')],
                             string='Status',
                             readonly=True, copy=False, tracking=True,
                             default='draft')
    move_id = fields.Many2one('account.move', string='Invoice')
    ready_to_pay = fields.Boolean('Ready to Pay', default=False)
    is_advance = fields.Boolean('Advance', default=False)

    @api.constrains('payment_date')
    def _check_payment_date(self):
        """Validation for payment date"""
        for rec in self:
            if rec.payment_date and rec.payment_date < fields.Date.today():
                raise ValidationError(_("The Payment Date cannot be in the past."))

    def action_create_payment(self):
        """Open installment payment wizards"""
        action = {
            "name": _("Installment Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "installment.payment",
            "type": "ir.actions.act_window",
            "target": "new"
        }
        return action
