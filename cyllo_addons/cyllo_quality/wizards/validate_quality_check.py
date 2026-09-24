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


class ValidateQualityCheck(models.TransientModel):
    _name = 'validate.quality.check'
    _description = 'Validate Quality Check'


    quality_control_point_id = fields.Many2many('quality.control.point')
    quality_check_wizard_line_ids = fields.Many2many('quality.check.line', compute='_compute_quality_check')

    @api.depends('quality_control_point_id')
    def _compute_quality_check(self):
        for action in self:
            action.quality_check_wizard_line_ids = [fields.Command.clear()]
            action.quality_check_wizard_line_ids = [fields.Command.create({
                'quality_control_id': action.quality_control_point_id.id,
                'inspection_action_id': qc.inspection_action_id.id,
                'quality_inspection_id': qc.inspection_type_id.id,
                'value': qc.value,
            }) for qc in action.quality_control_point_id.quality_inspection_ids]

