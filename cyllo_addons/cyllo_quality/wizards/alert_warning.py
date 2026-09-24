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


class AlertWarning(models.TransientModel):
    _name = 'alert.warning'
    _description = 'Alert Warning'

    quality_check_id = fields.Many2one('quality.check')
    quality_check_line_id = fields.Many2one('quality.check.line')
    failure_location_id = fields.Many2one('stock.location', string='Failure Location', related='quality_check_id.quality_control_id.failure_location_id', readonly=False)

    def action_create_alert(self):
        stage_id = self.env.ref('cyllo_quality.quality_alert_stage_quarantine').id
        product = self.quality_check_id.product_id
        self.env['quality.alert'].create({
            'quality_check_id': self.quality_check_id.id,
            'product_id': product.id if product else False,
            'product_template_id': product.product_tmpl_id.id if product else False,
            'picking_id': self.quality_check_id.picking_id.id if self.quality_check_id.picking_id else False,
            'quality_team_id': self.quality_check_id.quality_team_id.id if self.quality_check_id.quality_team_id else False,
            'stage_id': stage_id
        })
        self.quality_check_line_id.is_alert = True
