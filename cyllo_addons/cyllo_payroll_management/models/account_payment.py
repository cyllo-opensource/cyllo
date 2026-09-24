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
from odoo import api, models


class AccountPayment(models.Model):
    """Inheriting for overwriting existing function that returns valid payment
     account types to supports payslip payment registration"""
    _inherit = 'account.payment'

    @api.model
    def _get_valid_payment_account_types(self):
        """This method add a new account type to existing account types which
        allows payment registration of payslip"""
        res = super()._get_valid_payment_account_types()
        if self.env.context.get('payroll_register_payment', False):
            res.append('liability_current')
        return res