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


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    availability_status = fields.Selection(
        selection=[('available', 'Available'),
                   ('reserved', 'Reserved'),
                   ('not_available', 'Not Available')],
        compute="_compute_availability_status", store=True)
    field_service_worker_ids = fields.One2many("field.service.worker",
                                               "employee_id")

    @api.depends('field_service_worker_ids.field_service_request_id.state')
    def _compute_availability_status(self):
        """Method to set availability of employee based on field service workers data"""
        for rec in self:
            works = self.env['field.service.worker'].search(
                [('employee_id', '=', rec.id)])
            if works.filtered(
                    lambda w: w.field_service_request_id.state == 'in_progress'):
                rec.availability_status = 'not_available'
            elif works.filtered(
                    lambda w: w.field_service_request_id.state == 'assigned'):
                rec.availability_status = 'reserved'
            else:
                rec.availability_status = 'available'

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    availability_status = fields.Selection(
        selection=[('available', 'Available'),
                   ('reserved', 'Reserved'),
                   ('not_available', 'Not Available')],
        string="Availability Status", readonly=True)
