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
from odoo.exceptions import ValidationError


class OdometerReading(models.Model):
    _name = "odometer.reading"

    fleet_id = fields.Many2one('fleet.vehicle', readonly=True)
    last_odometer = fields.Float('Last Odometer', readonly=True)
    new_reading = fields.Float('New Reading', required=True)
    field_request_id = fields.Many2one("field.service.request", readonly=True)

    def action_save(self):
        service_checklist_ids = self.field_request_id.service_checklist_ids.filtered(lambda x: x.required and x.status == 'pending')
        if self.last_odometer > self.new_reading:
            raise ValidationError(_("Kindly enter the correct meter reading."))
        else:
            if service_checklist_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("There are still pending checklist items that require completion"),
                        'type': 'warning',
                    }}
            else:
                self.field_request_id.sudo().write({'state': 'completed'})
                self.fleet_id.sudo().write({'odometer': self.new_reading})
                contract = self.fleet_id.log_contracts.filtered(lambda l: l.field_service_request_id == self.field_request_id)
                if contract:
                    contract.action_close()


