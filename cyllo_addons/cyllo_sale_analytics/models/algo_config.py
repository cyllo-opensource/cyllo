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
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AlgoConfig(models.Model):
    _name = 'algo.config'
    _description = 'Algorithm Configuration'

    name = fields.Char(default='Churn Prediction Configuration')
    line_ids = fields.One2many('algo.config.line', 'config_id', string='Feature Configuration')

    @api.constrains('line_ids')
    def _check_total_weightage(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('weightage'))
            if total != 100:
                raise ValidationError("Total weightage must be exactly 100%.")

class AlgoConfigLine(models.Model):
    _name = 'algo.config.line'
    _description = 'Algorithm Configuration Line'

    config_id = fields.Many2one('algo.config', ondelete='cascade')
    field_type = fields.Selection([
        ('count', 'Sale Order Count'),
        ('total', 'Total Sale Amount'),
        ('recency', 'Recency (Days since last order)'),
        ('custom', 'Custom Field')
    ], required=True, default='custom', string="Field Type")
    
    custom_field_id = fields.Many2one(
        'ir.model.fields',
        # store=True matters: the churn query sums this column in raw SQL, and
        # computed non-stored fields (amount_paid, invoice_count, ...) have no
        # column, so offering them here produced an UndefinedColumn error.
        domain="[('model', '=', 'sale.order'), ('ttype', 'in', ('integer', 'float', 'monetary')), ('store', '=', True)]",
        string="Sale Order Field"
    )
    weightage = fields.Float(string="Weightage (%)", required=True)
