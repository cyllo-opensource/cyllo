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


class AccountMoveLine(models.Model):
    """Keep the PDC cheque status in sync with the bank reconciliation"""
    _inherit = 'account.move.line'

    def _get_pdc_payments_to_sync(self):
        """PDC payments whose PDC-account line is one of these lines or is
        reconciled with one of them (e.g. the bank statement line)."""
        lines = self | self.matched_debit_ids.debit_move_id \
            | self.matched_credit_ids.credit_move_id
        return lines.move_id.pdc_payment_id

    def reconcile(self):
        """Cheque becomes Accepted once its PDC line is fully reconciled"""
        res = super().reconcile()
        self._get_pdc_payments_to_sync()._sync_payment_status_with_reconciliation()
        return res

    def remove_move_reconcile(self):
        """Cheque goes back to Registered if the reconciliation is undone"""
        pdc_payments = self._get_pdc_payments_to_sync()
        res = super().remove_move_reconcile()
        pdc_payments._sync_payment_status_with_reconciliation()
        return res
