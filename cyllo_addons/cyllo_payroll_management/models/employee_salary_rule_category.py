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


class EmployeeSalaryRuleCategory(models.Model):
    """To create the salary rule category"""
    _name = 'employee.salary.rule.category'
    _description = 'Employee Salary Rule Category'

    name = fields.Char(help='To Add the name', required=True)
    code = fields.Char(help='To Add the code', required=True)
    parent_id = fields.Many2one(string='Parent Category', comodel_name='employee.salary.rule.category',
                                help='To choose the parent category')
    description = fields.Html(help='To add the description of the category')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
