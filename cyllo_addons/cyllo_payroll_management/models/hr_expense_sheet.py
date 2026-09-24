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
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    """Inherit hr.expense.sheet to add payroll integration"""
    _inherit = 'hr.expense.sheet'
    report_to_payslip = fields.Boolean(
        string='Report to Payslip',
        copy=False,
        help='If checked, this expense will be included in the next payslip calculation'
    )
    payslip_id = fields.Many2one(
        'employee.payslip',
        string='Payslip',
        copy=False,
        readonly=True,
        help='The payslip where this expense was included'
    )
    def action_report_to_payslip(self):
        """Mark expense sheet to be reported in next payslip"""
        for sheet in self:
            if sheet.state != 'approve':
                raise UserError(_('Only approved expense sheets can be reported to payslip.'))
            if sheet.report_to_payslip:
                raise UserError(_('This expense sheet is already reported to payslip.'))
            sheet.sudo().write({'report_to_payslip': True})
        return True