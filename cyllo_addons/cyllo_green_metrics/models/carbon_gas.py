
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


class CarbonGas(models.Model):
    _name = 'carbon.gas'
    _description = 'Carbon Gas'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Unique short code used to identify the gas (e.g., CO2, CH4, N2O).")
    formula = fields.Char(help="Chemical formula of the gas (e.g., CO₂, CH₄, N₂O).")
    gwp = fields.Float(string='GWP', help="Global Warming Potential (GWP) indicates how much more heat this gas traps "
                                          "in the atmosphere compared to CO₂ (GWP = 1) over a specified time period.")
    unit_name = fields.Many2one('carbon.unit', string='Unit',
                                help="Select the unit used to measure the gas or its emission factor.")
    active = fields.Boolean(default=True)
    note = fields.Text()

    _sql_constraints = [
        ('carbon_gas_code_uniq', 'unique(code)', 'Gas code must be unique.'),
    ]
