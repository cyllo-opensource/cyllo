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
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    """Inherit the register payment wizards """
    _inherit = 'account.payment.register'

    def _create_payments(self):
        """When create payment updates installments"""
        res = super(AccountPaymentRegister, self)._create_payments()
        for payment in res:
            for move in payment.reconciled_invoice_ids:
                if move.installment_payment:
                    installment_ids = self.env['account.installment'].search(
                        [('move_id', '=', move.id), ('state', '=', 'draft')],
                        order='sequence asc')
                    if installment_ids:
                        if move.payment_state == 'paid':
                            installment_ids.write({'state': 'paid'})
                        else:
                            paid_amount = payment.amount
                            for installment in installment_ids:
                                if paid_amount == 0:
                                    break
                                elif paid_amount >= installment.pay_amount:
                                    paid_amount -= installment.pay_amount
                                    installment.write({'state': 'paid'})
                                else:
                                    installment_pay_amount = installment.pay_amount - paid_amount
                                    installment.write(
                                        {'pay_amount': installment_pay_amount})
                                    paid_amount = 0
        return res
