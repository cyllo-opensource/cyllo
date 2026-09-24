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
from odoo import api, fields, models


class CarbonEmissionSource(models.Model):
    _name = 'carbon.source'
    _description = 'Emission Source'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'name'

    name = fields.Char(required=True, help="Enter the name of the emission source (e.g., Electricity, Company Vehicle, Diesel Generator).")
    category = fields.Selection([
        ('energy', 'Energy'),
        ('transport', 'Transport'),
        ('materials', 'Materials'),
        ('waste', 'Waste'),
        ('services', 'Services'),
        ('other', 'Other'),
    ], default='other', required=True, help="Select the category that best describes the source of the emission.")
    activity_unit = fields.Many2one('carbon.unit', string='Activity Unit', help="Select the unit used to measure the activity for this source.")
    scope_id = fields.Many2one('carbon.scope', ondelete='restrict', help="Select the emission scope to which this source belongs")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    description = fields.Text(help="Provide additional details or notes about this emission source.")
    air_factor_ids = fields.One2many('carbon.factor', 'source_id',domain=[('type', '=', 'air')], context={'default_type': 'air'}, string="Air Factors")
    sound_factor_ids = fields.One2many('carbon.factor', 'source_id', domain=[('type', '=', 'sound')], context={'default_type': 'sound'}, string="Sound Factors")
    water_factor_ids = fields.One2many('carbon.factor', 'source_id', domain=[('type', '=', 'water')], context={'default_type': 'water'}, string="Water Factors")
    factor_count = fields.Integer(compute='_compute_factor_count', string='Factor Count')

    @api.depends('air_factor_ids', 'sound_factor_ids','water_factor_ids')
    def _compute_factor_count(self):
        """Compute factor count for the record."""
        for rec in self:
            air_factor_count=len(rec.air_factor_ids)
            sound_factor_count=len(rec.sound_factor_ids)
            water_factor_count=len(rec.water_factor_ids)
            rec.factor_count = air_factor_count+sound_factor_count+water_factor_count


