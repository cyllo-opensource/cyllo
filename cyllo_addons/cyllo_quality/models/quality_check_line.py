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
from odoo import api,_, fields, models
from odoo.exceptions import UserError


class QualityCheckLine(models.Model):
    _name = 'quality.check.line'
    _description = 'Quality Check Lines'

    quality_check_id = fields.Many2one('quality.check')
    quality_control_id = fields.Many2one('quality.control.point', string='Quality Control Point')
    inspection_action_id = fields.Many2one('inspection.action', string='Actions', required=True)
    inspection_type_id = fields.Many2one('inspection.type', string='Type', required=True)
    quality_inspection_id = fields.Many2one('quality.inspection', string='Type')
    blocked_by_id = fields.Many2one('quality.inspection', string='Blocked By')
    value = fields.Char()
    value_image = fields.Binary(string='Photo', compute='_compute_value_image')
    unit_value = fields.Json()
    measure_start = fields.Float(string='Start')
    measure_end = fields.Float(string='End')
    unit_id = fields.Many2one('uom.uom', string='Unit')
    note = fields.Text(string='Note')
    instruction = fields.Text(string='Quality Check Instructions')
    is_checked = fields.Boolean(copy=False)
    is_pass = fields.Boolean(copy=False)
    is_alert = fields.Boolean(copy=False)
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    is_picture_type = fields.Boolean(
        compute='_compute_is_picture_type')

    @api.depends('inspection_type_id')
    def _compute_is_picture_type(self):
        for line in self:
            line.is_picture_type = (
                line.inspection_type_id.name == 'Take a picture')

    @api.depends('value', 'inspection_type_id')
    def _compute_value_image(self):
        for line in self:
            if line.value and line.inspection_type_id.name == 'Take a picture':
                image_data = line.value
                if ',' in image_data:
                    image_data = image_data.split(',', 1)[1]
                line.value_image = image_data
            else:
                line.value_image = False

    def action_check_qc(self):
        quality_check = self.quality_check_id.read(['quality_check_line_ids', 'quality_control_id', 'product_id', 'user_id', 'quality_team_id'])
        return {
            'type': 'ir.actions.client',
            'tag': 'validate_quality_action',
            'name': 'Quality Check',
            'target': 'new',
            'context': {
                'quality_check': quality_check,
                'quality_check_action': self.read(),
            }
        }

    def validate_quality_actions(self, value, note):
        self.ensure_one()
        if self.blocked_by_id:
            blocking_line = self.env['quality.check.line'].search([
                ('quality_check_id', '=', self.quality_check_id.id),
                ('quality_inspection_id', '=', self.blocked_by_id.id)
            ], limit=1)
            if blocking_line and not blocking_line.is_checked:
                raise UserError(_("This action is blocked by %s. Please complete it first.") % blocking_line.inspection_action_id.name)
        if self.inspection_type_id.name == 'Measure':
            if not value or not str(value).strip():
                raise UserError(_("Measurement value is required for '%s'.") % self.inspection_action_id.name)
            try:
                val = float(value)
                if self.measure_start <= val <= self.measure_end:
                    self.write({'status': 'pass'})
                else:
                    self.write({'status': 'fail'})
            except (ValueError, TypeError):
                self.write({'status': 'fail'})
            self.write({
                'value': value,
                'unit_value': {
                    'unit': {
                        'id': self.unit_id.id,
                        'name': self.unit_id.name or '',
                    },
                    'value': value
                }
            })
        elif self.inspection_type_id.name == 'Instructions':
            if value == 'pass':
                self.write({
                    'status': 'pass'})
            else:
                self.write({
                    'status' : 'fail'})
        elif self.inspection_type_id.name == 'Take a picture':
            if value and '|' in value:
                status, actual_value = value.split('|', 1)
                self.write({
                    'status': status,
                    'value': actual_value
                })
            else:
                self.write({
                    'status': value,
                    'value': value
                })
        elif self.inspection_type_id.name == 'Pass/Fail':
            if value == 'pass':
                self.write({
                    'status': 'pass'})
            else:
                self.write({
                    'status' : 'fail'})
        self.write({
            'is_checked': True,
            'note': note
        })
        return self.status

    def action_create_alert(self):
        return {
            'name': "Create Alert",
            'view_mode': 'form',
            'res_model': 'alert.warning',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_quality_check_id': self.quality_check_id.id,
                'default_quality_check_line_id': self.id,
            }
        }


