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
from odoo import fields, models, _


class MaintenanceEquipment(models.Model):
    """In this class we are defining the additional fields required for the model maintenance.equipment."""
    _inherit = 'maintenance.equipment'

    field_service_id = fields.Many2one('field.service.request',
                                       help="Assigned field request to this equipment")
    assigned_date = fields.Date("Assigned Date", help="Equipment assigned date")
    returned_date = fields.Date("Returned Date", help="Equipment returned date")
    equipment_history_count = fields.Integer("History", compute='_compute_equipment_history_count')

    def action_view_equipment_history(self):
        """
            Opens a window action to display the history of field service requests related to the equipment.

            This method returns an action that displays a list (tree view) of `field.service.request` records associated
            with the current equipment. It filters the field service requests using the `field_service_equipments_ids`
            field to show only the requests related to the equipment represented by the current record.

            Workflow:
            1. The method creates a window action with a tree view of the `field.service.request` model.
            2. The `domain` ensures that only records where the current equipment (`self.ids`) is part of
               the `field_service_equipments_ids` field in the `field.service.request` model are shown.

            Returns:
            - dict: A dictionary representing an Odoo window action with a tree view of the filtered
              `field.service.request` records.

            Example:
            - When a user clicks to view the equipment history, a list of all field service requests related to
              the equipment will be displayed in the tree view.

        """
        return {
            'name': _('History'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.request',
            'domain': [('field_service_equipments_ids','in',self.ids)],
            'view_mode': 'tree,form',
            'context': {
                'create': False,
            },
        }

    def _compute_equipment_history_count(self):
        """
            Computes the number of field service requests related to the current equipment.

            This method calculates the `equipment_history_count` field for each record by counting how many
            `field.service.request` records are associated with the equipment (`self`). It uses the
            `field_service_equipments_ids` field in the `field.service.request` model to find related service requests.

            Returns:
            - Updates the `equipment_history_count` field with the number of related field service requests.

            Example:
            - If the current equipment has 3 associated service requests, the `equipment_history_count` will be set to 3.

        """
        self.equipment_history_count = 0
        for rec in self:
            rec.equipment_history_count = self.env['field.service.request'].search_count([('field_service_equipments_ids','in',self.ids)])
