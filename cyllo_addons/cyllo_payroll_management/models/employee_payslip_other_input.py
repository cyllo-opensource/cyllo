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


class EmployeePayslipOtherInput(models.Model):
    """ Manage additional inputs for employee payslips under Payslip Other Input."""
    _name = 'employee.payslip.other.input'
    _description = 'Payslip Other Input'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, help='Description of the other input')
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    structure_ids = fields.Many2many('employee.salary.structure', string='Availability in Structure',
                                     help='This input will be only available in those structure.If empty, it will be'
                                          'available in all payslip.')
    company_id = fields.Many2one('res.company', copy=False, default=lambda self: self.env.company.id,
                                 help='The company associated with this record')
