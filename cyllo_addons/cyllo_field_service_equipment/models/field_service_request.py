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
from datetime import datetime
from odoo import fields, models


class FieldServiceRequest(models.Model):
    """In this class we are defining the additional fields required for the model field.service.request."""
    _inherit = 'field.service.request'

    field_service_equipments_ids = fields.Many2many(
        'maintenance.equipment', string="Equipments", help="Choose Equipments for this field service",
        domain="[('maintenance_open_count', '=', 0), ('field_service_id', '=', False)]", copy=False)



    def action_assign_workers(self):
        """
                   Overrides the 'action_assign_workers' method to perform the following:
                   1. Calls the parent method to assign workers to the field service.
                   2. Assigns the current field service request ID to each equipment in 'field_service_equipments_ids'.
                   3. Sets the 'assigned_date' to today's date for each equipment.
                   Returns:
                       res: The result from the parent class method.
                """
        res = super().action_assign_workers()
        if not res:
            for rec in self.field_service_equipments_ids:
                rec.assigned_date = datetime.today().date()
            if self.field_service_equipments_ids:
                self.field_service_equipments_ids.write({'field_service_id': self.id})
        return res

    def action_mark_as_done(self):
        """
            Overrides the 'action_mark_as_done' method to perform the following:

            1. Calls the parent method to mark the task as done.
            2. If all required checklist items are completed, unassign the equipment by clearing their 'field_service_id'.
            3. Sets the 'returned_date' to today's date for each equipment.

            Returns:
                res: The result from the parent class method.
            """
        res = super().action_mark_as_done()
        for rec in self.field_service_equipments_ids:
            rec.returned_date = datetime.today().date()
        if not self.service_checklist_ids.filtered(lambda x: x.required and x.status == 'pending'):
            if self.field_service_equipments_ids:
                self.field_service_equipments_ids.write({'field_service_id': None})
        return res
