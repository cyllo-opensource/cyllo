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


class FieldServiceEmployeeSuggestion(models.TransientModel):
    """In this class we are defining the fields required for the model
    'field.service.employee.suggestion.'
    """
    _name = "field.service.employee.suggestion"
    _description = "Field Service Employee Suggestion"

    employee_id = fields.Many2one('hr.employee', required=True, readonly=True,
                                  help="Name of employee")
    skill_ids = fields.Many2many('hr.skill', string="Skills", readonly=True,
                                 help="Skills the employee mastered")
    field_service_request_id = fields.Many2one('field.service.request',
                                               string="Service Request",
                                               help="Corresponding service request of this suggestion")
    field_service_request_ids = fields.Many2many('field.service.request',
                                                 string="Assigned/Ongoing Services",
                                                 help="Assigned or ongoing services of the employee",
                                                 readonly=True)
    added_to_workers = fields.Boolean(readonly=True,
                                      help="Boolean which represent the visibility of button")
    sequence = fields.Integer(compute="_compute_sequence", store=True)
    availability_status = fields.Selection(
        related='employee_id.availability_status')

    @api.depends('added_to_workers', 'availability_status')
    def _compute_sequence(self):
        for rec in self:
            if not rec.added_to_workers and rec.availability_status == 'available':
                rec.sequence = 0
            elif not rec.added_to_workers and rec.availability_status == 'reserved':
                rec.sequence = 1
            elif rec.added_to_workers and rec.availability_status == 'available':
                rec.sequence = 2
            elif rec.added_to_workers:
                rec.sequence = 3
            else:
                rec.sequence = 4

    def action_add_workers(self):
        """Function to assign the corresponding employee to service request  """
        self.field_service_request_id = self.env.context.get(
            'field_service_request_id')
        workers = self.env['field.service.worker'].search(
            [('field_service_request_id', '=',
              self.field_service_request_id.id)]).mapped('employee_id.id')
        self.added_to_workers = True
        if self.employee_id.id not in workers:
            self.field_service_request_id.write(
                {'field_service_worker_ids': [fields.Command.create(
                    {'employee_id': self.employee_id.id})]})

    def action_add_workers_bulk(self):
        """Method to assign the selected employees to service request"""
        for rec in self.filtered(
                lambda l: l.availability_status != 'not_available'):
            rec.action_add_workers()
