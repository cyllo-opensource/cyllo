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


class CommissionReport(models.Model):
    """Inherit commission.report to add payroll integration"""
    _inherit = 'commission.report'

    payslip_id = fields.Many2one(
        'employee.payslip',
        string='Payslip',
        copy=False,
        readonly=True,
        help='The payslip where this commission was included'
    )
    payslip_input_ids = fields.One2many(
        'employee.payslip.input',
        'commission_report_id',
        string='Payslip Inputs'
    )
    paysliped_amount = fields.Monetary(
        string='Paysliped Amount',
        compute='_compute_paysliped_amount',
        store=True,
        help='Total amount already paid via payslips'
    )
    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        compute='_compute_remaining_amount',
        store=True,
        help='Remaining commission to be paysliped'
    )
    report_to_payslip = fields.Boolean(
        string='Report to Payslip',
        copy=False,
        help='If checked, this commission will be included in the next payslip'
    )

    @api.depends('commission_amount', 'paysliped_amount')
    def _compute_remaining_amount(self):
        """Compute the balance commission amount"""
        for report in self:
            report.remaining_amount = report.commission_amount - report.paysliped_amount

    @api.depends('payslip_input_ids.payslip_id.state', 'payslip_input_ids.amount')
    def _compute_paysliped_amount(self):
        """Compute total amount paid in previous finalized payslips"""
        for report in self:
            total = 0.0
            for line in report.payslip_input_ids:
                if line.payslip_id.state in ['done', 'paid']:
                    total += line.amount
            report.paysliped_amount = total
