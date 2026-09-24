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


class CarbonComputeWizard(models.TransientModel):
    _name = 'carbon.compute.wizard'
    _description = 'Compute Emissions Wizard'

    calculation_id = fields.Many2one('carbon.calc', required=True, ondelete='cascade', help="Carbon calculation to be processed.")
    apply_rules = fields.Boolean(default=True, help="Apply assignment rules before computing emissions.")
    mark_done = fields.Boolean(default=False, help="Mark the calculation as done after processing.")

    def action_run(self):
        """Execute the selected processing steps for the associated carbon calculation."""
        self.ensure_one()
        activities = self.calculation_id.carbon_activity_ids
        if self.apply_rules:
            activities.action_apply_rules()
        activities.action_compute()
        if self.mark_done:
            self.calculation_id.action_done()
        return {'type': 'ir.actions.act_window_close'}
