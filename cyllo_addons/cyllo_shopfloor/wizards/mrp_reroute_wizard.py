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
from odoo import models, fields

class MrpRerouteWizard(models.TransientModel):
    _name = 'mrp.reroute.wizard'
    _description = 'Reroute Work Order Wizard'

    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Work Order',
        required=True,
        domain="[('production_id', '=', context.get('default_production_id')), ('state', 'not in', ('done', 'cancel'))]"
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='New Work Center',
        required=True
    )

    def action_reroute(self):
        """Reroute Work Order to other work center"""
        self.ensure_one()
        wo = self.workorder_id

        if wo and self.workcenter_id:
            original_state = wo.state

            if original_state == 'progress':
                wo.button_pending()

            wo.write({'workcenter_id': self.workcenter_id.id})
            if original_state == 'progress':
                wo.button_start()

            if hasattr(wo, '_update_shopfloor_view'):
                wo._update_shopfloor_view()

        return {'type': 'ir.actions.act_window_close'}
