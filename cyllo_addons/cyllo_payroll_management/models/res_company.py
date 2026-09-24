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


class ResCompany(models.Model):
    """Extends the `res.config.settings` model to add the fields"""
    _inherit = 'res.company'

    batch_move_line = fields.Boolean(string='Batch Move', help='To get the value from the settings')
    advance_salary_account_id = fields.Many2one('account.account', string='Advance Salary Account',
                                               help='Account to be used for Advance Salary bill creation (Debit Account)')
    advance_salary_payment_account_id = fields.Many2one('account.account', string='Advance Salary Payment Account',
                                                       help='Account to be used for Advance Salary payment (Credit Account)')
