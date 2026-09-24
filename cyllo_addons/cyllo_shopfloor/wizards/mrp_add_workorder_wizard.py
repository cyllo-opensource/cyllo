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


class MrpAddWorkorderWizard(models.TransientModel):
    _name = 'mrp.add.workorder.wizard'
    _description = 'Add Custom Work Order Wizard'

    production_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Manufacturing Order',
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='production_id.company_id'
    )
    name = fields.Char(
        string='Operation Name',
        required=True,
        help="e.g. Extra Polishing"
    )
    workcenter_id = fields.Many2one(
        comodel_name='mrp.workcenter',
        string='Work Center',
        required=True
    )
    duration_expected = fields.Float(
        string='Expected Duration',
        default=60.0,
        help="Expected duration in minutes"
    )
    date_start = fields.Datetime(
        string='Scheduled Start Date'
    )

    def action_add_workorder(self):
        """Creates a new work order for the specified manufacturing order."""
        self.ensure_one()

        workorder_values = {
            'name': self.name,
            'production_id': self.production_id.id,
            'workcenter_id': self.workcenter_id.id,
            'duration_expected': self.duration_expected,
            'company_id': self.company_id.id,
            'consumption': 'warning',
            'product_id': self.production_id.product_id.id,
            'product_uom_id': self.production_id.product_uom_id.id,
        }

        if self.date_start:
            workorder_values['date_start'] = self.date_start

        new_workorder = self.env['mrp.workorder'].create(workorder_values)

        if self.production_id.state in ('confirmed', 'progress'):
            new_workorder.state = 'ready'

        new_workorder._update_shopfloor_view()
        return {'type': 'ir.actions.act_window_close'}

    def action_remove_workorder(self):
        """Removes the custom work order from the manufacturing order."""
        self.ensure_one()

        existing_workorder = self.env['mrp.workorder'].search([
            ('production_id', '=', self.production_id.id),
            ('workcenter_id', '=', self.workcenter_id.id),
            ('name', '=', self.name),
            ('state', 'not in', ('done', 'cancel'))
        ], limit=1)

        if existing_workorder:
            existing_workorder.unlink()

        return {'type': 'ir.actions.act_window_close'}
