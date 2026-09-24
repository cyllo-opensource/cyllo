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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extends the `res.config.settings` model to add the fields"""
    _inherit = 'res.config.settings'

    batch_move_line = fields.Boolean(string="Batch Account Move Lines",
                                     help="To combine all of the accounting entries for a given time into a single "
                                          "account move line, enable this option. In addition to disabling single "
                                          "payment generations, this will anonymize the accounting entries.",
                                     config_parameter='cyllo_payroll_management.batch_move_line')
    advance_salary_account_id = fields.Many2one('account.account', related='company_id.advance_salary_account_id',
                                               readonly=False, string='Advance Salary Account',
                                               help='Account to be used for Advance Salary bill creation (Debit Account)')
    advance_salary_payment_account_id = fields.Many2one('account.account', related='company_id.advance_salary_payment_account_id',
                                                       readonly=False, string='Advance Salary Payment Account',
                                                       help='Account to be used for Advance Salary payment (Credit Account)')

    @api.onchange('batch_move_line')
    def _onchange_batch_move_line(self):
        """To set true the batch move line"""
        if self.batch_move_line:
            self.env.user.company_id.batch_move_line = True
        else:
            self.env.user.company_id.batch_move_line = False
