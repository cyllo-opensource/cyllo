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
from datetime import datetime
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    def action_open_repair_floor(self):
        """Redirects the user to the Repair Floor dashboard for this record."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("cyllo_shopfloor_repair.action_repair_floor")
        # Setting context so it can be handled by JS components if needed
        action['context'] = {'default_repair_id': self.id}
        return action

    def action_show_repair_notes(self):
        """Returns an action to open the repair notes in a custom popup view."""
        self.ensure_one()
        notes_view_id = self.env.ref('cyllo_shopfloor_repair.view_repair_floor_notes_popup').id
        return {
            'name': f'Repair Notes: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(notes_view_id, 'form')],
            'target': 'new',
        }
