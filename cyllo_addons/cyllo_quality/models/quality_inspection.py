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


class QualityInspection(models.Model):
    _name = 'quality.inspection'
    _description = 'Quality Inspections'
    _order = 'priority'

    priority = fields.Integer(default=1)

    quality_control_id = fields.Many2one('quality.control.point',
                                         string='Quality Control Point')
    inspection_action_id = fields.Many2one('inspection.action',
                                           string='Actions', required=True)
    name = fields.Char(compute='_compute_name', string='Actions', help="Displays the inspection action name.")
    inspection_type_id = fields.Many2one('inspection.type', string='Type', required=True)
    blocked_by_id = fields.Many2one('quality.inspection', string='Blocked By',
                                    domain="[('quality_control_id', '=', quality_control_id), ('quality_control_id', '!=', False), ('id', '!=', id)]",
                                    help="Select another inspection that must be completed before this inspection can begin."
                                    )
    value = fields.Json(default=lambda self: {
        "unit": {
            "id": False,
            "name": ''
        },
        "value": ''
    })
    is_measure = fields.Boolean(compute='_compute_is_measure')
    instruction = fields.Text(string='Quality Check Instructions',help="Provide detailed instructions for performing this quality inspection.")
    measure_start = fields.Float(string='Start', help="Enter the minimum acceptable measurement value.")
    measure_end = fields.Float(string='End', help="Enter the maximum acceptable measurement value.")
    unit_id = fields.Many2one('uom.uom', string='Unit', help="Select the unit of measure for the inspection.")

    @api.depends('inspection_action_id', 'priority')
    def _compute_name(self):
        """Compute the display name using priority and inspection action."""
        for record in self:
            action_name = record.inspection_action_id.name or ''
            record.name = f"{record.priority if record.priority else ''},{action_name} "

    @api.depends('inspection_type_id')
    def _compute_is_measure(self):
        """Determine whether the inspection type is 'Measure'."""
        measure_inspection_type_id = self.env.ref(
            'cyllo_quality.inspection_type_measure').id
        for record in self:
            record.is_measure = False
            if record.inspection_type_id.id == measure_inspection_type_id:
                record.is_measure = True

    @api.onchange('inspection_type_id')
    def _onchange_inspection_type_id(self):
        """Clear measurement fields when the inspection type is not Measure."""
        if self.inspection_type_id.name != 'Measure':
            self.measure_start = False
            self.measure_end = False
            self.unit_id = False

    @api.model_create_multi
    def create(self, vals_list):
        """Reset measurement values when the inspection type is not Measure."""
        measure_type = self.env.ref('cyllo_quality.inspection_type_measure', raise_if_not_found=False)
        for vals in vals_list:
            if 'inspection_type_id' in vals and measure_type:
                if vals['inspection_type_id'] != measure_type.id:
                    vals['measure_start'] = 0.0
                    vals['measure_end'] = 0.0
                    vals['unit_id'] = False
        return super().create(vals_list)

    def write(self, vals):
        """Reset measurement values when the inspection type is not Measure."""
        measure_type = self.env.ref('cyllo_quality.inspection_type_measure', raise_if_not_found=False)
        if measure_type and any(f in vals for f in ('inspection_type_id', 'measure_start', 'measure_end', 'unit_id')):
            for record in self:
                inspection_type_id = vals.get('inspection_type_id', record.inspection_type_id.id)
                if inspection_type_id != measure_type.id:
                    vals.update({
                        'measure_start': 0.0,
                        'measure_end': 0.0,
                        'unit_id': False,
                    })
        return super().write(vals)

    def action_add_instruction(self):
        """Open the instruction editor wizard for the inspection."""
        return {
            'type': 'ir.actions.client',
            'tag': 'quality_instruction_action',
            'target': 'new',
            'params': {
                'res_id': self.id,
            }
        }
