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
import json
from odoo import api, fields, models, _


class FieldServiceRequest(models.Model):
    """
    In this class we are defining the additional fields required for the model
        field.service.request.
            """
    _inherit = 'field.service.request'

    fleet_domain = fields.Char(compute='_compute_fleet_domain')
    fleet_id = fields.Many2one('fleet.vehicle',
                               domain='fleet_domain',
                               help="Choose fleet for this field service")

    @api.depends('name')
    def _compute_fleet_domain(self):
        """Compute method for fleet_domain field based on open vehicle log
        contracts and new/running log services."""
        log_contract = self.env['fleet.vehicle.log.contract'].search(
            [('state', '=', 'open')])
        log_service = self.env['fleet.vehicle.log.services'].search(
            [('state', 'in', ('new', 'running'))])
        running_services = self.env['field.service.request'].search(
            [('state', 'in', ['assigned', 'in_progress'])])
        vehicle_ids = list(
            set(log_contract.mapped('vehicle_id').ids + log_service.mapped(
                'vehicle_id').ids + running_services.mapped('fleet_id').ids))
        for rec in self:
            rec.fleet_domain = json.dumps([
                ('state_id', '=',
                 self.env.ref('fleet.fleet_vehicle_state_registered').id),
                ('id', 'not in', vehicle_ids)
            ])

    def action_assign_workers(self):
        """Override method to create new contract for vehicle"""
        res = super(FieldServiceRequest, self).action_assign_workers()
        if res and res.get('type', False):
            return res
        else:
            if self.fleet_id:
                self.fleet_id.write({
                    'log_contracts': [fields.Command.create({
                        'name': f"{self.fleet_id.name} for field service - {self.name}",
                        'start_date': fields.Date.today(),
                        'user_id': self.env.user.id,
                        'state': 'futur',
                        'field_service_request_id': self.id
                    })]
                })
        return res

    def action_service_start(self):
        """Override method to start fleet contract when service has started"""
        res = super().action_service_start()
        if self.fleet_id:
            contract = self.fleet_id.log_contracts.filtered(
                lambda c: c.field_service_request_id == self)
            if contract:
                contract[0].action_open()
        return res

    def action_cancel(self):
        """Override method to remove contract when the service has cancelled"""
        res = super().action_cancel()
        contract = self.fleet_id.log_contracts.filtered(
            lambda c: c.field_service_request_id == self)
        if contract:
            contract[0].unlink()
        return res

    def action_mark_as_done(self):
        """In this function, change the task to done if all checklist completed"""
        service_checklist_ids = self.service_checklist_ids.filtered(
            lambda x: x.required and x.status == 'pending')
        if service_checklist_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "There are still pending checklist items that require"
                        " completion"),
                    'type': 'warning',
                }}
        if self.fleet_id:
            return {
                'name': 'Odometer Reading',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'odometer.reading',
                'target': 'new',
                'context': {
                    'default_fleet_id': self.fleet_id.id,
                    'default_last_odometer': self.fleet_id.odometer,
                    'default_field_request_id': self.id,
                }
            }
        self.sudo().write({'state': 'completed'})
