# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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


class CarbonScope(models.Model):
    _name = 'carbon.scope'
    _description = 'Emission Scope'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'sequence, name'

    name = fields.Char(required=True, help="Enter the name of the emission scope (e.g., Scope 1, Scope 2, Scope 3).")
    code = fields.Char(required=True, help="Enter a unique code to identify the emission scope.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, default=lambda self: self.env.company,
                                    help="Select the company to which this emission scope belongs.")
    description = fields.Text( help="Provide additional details or notes about this emission scope.")

    _sql_constraints = [
        ('carbon_scope_code_uniq', 'unique(code, company_id)', 'Scope code must be unique per company.'),
    ]
