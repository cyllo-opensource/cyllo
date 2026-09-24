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
from odoo import fields, models


class AccountPdcBounceReason(models.TransientModel):
    """Wizard for PDC bounce reason"""
    _name = 'account.pdc.bounce.reason'
    _description = 'PDC Bounce Reason'

    reason = fields.Char(string="Reason Displayed on Journal Entry? ",
                         required=True, help="reason for bounce")
    bank_name = fields.Char(string="Bank", required=True,
                            help="Name of the bank")
    cheque_reference = fields.Char(required=True,
                                   help="Reference of the cheque")
    pdc_payment_id = fields.Many2one(comodel_name='account.pdc.payment')

    def default_get(self, fields_list):
        """Default values to the wizard"""
        res = super(AccountPdcBounceReason, self).default_get(fields_list)
        pdc_payment_id = self.env["account.pdc.payment"].browse(
            self._context.get("active_id"))
        if pdc_payment_id:
            res.update({
                "pdc_payment_id": pdc_payment_id.id,
                "bank_name": pdc_payment_id.bank_name,
                "cheque_reference": pdc_payment_id.cheque_reference
            })
        return res

    def action_bounce(self):
        """ Button: Confirm"""
        if self.pdc_payment_id:
            if self.pdc_payment_id.reconciled_invoice_ids:
                exist_move_id = self.pdc_payment_id.reconciled_invoice_ids
            elif self.pdc_payment_id.reconciled_bill_ids:
                exist_move_id = self.pdc_payment_id.reconciled_bill_ids
            else:
                exist_move_id = False
            self.pdc_payment_id.pdc_move_d = exist_move_id.id if exist_move_id and len(
                exist_move_id) == 1 else False
            self.pdc_payment_id.move_id.button_draft()
            self.pdc_payment_id.move_id.button_cancel()
            self.pdc_payment_id.move_id.pdc_reference = 'Check ' + self.pdc_payment_id.cheque_reference + ' Bounced -  ' + self.reason
            self.pdc_payment_id.write({'payment_status': 'bounced'})
