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


class FieldServiceWorker(models.Model):
    """In this class we are defining the fields required for model
       field.service.worker"""
    _name = 'field.service.worker'
    _description = 'Field Service Worker'

    field_service_request_id = fields.Many2one('field.service.request',
                                               string="Service Request",
                                               help="Service request checklist related",
                                               ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Worker',
                                  help="Employee name", required=True, )
    employee_ids = fields.Many2many('hr.employee',
                                    compute="_compute_employee_ids")
    mobile_number = fields.Char(string='Mobile',
                                related='employee_id.work_phone',
                                help="Employee phone number")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('field_service_request_id',
                 'field_service_request_id.hr_skill_ids',
                 'field_service_request_id.state', 'employee_id',
                 'field_service_request_id.field_service_worker_ids.employee_id')
    def _compute_employee_ids(self):
        """Dynamic domain to return employees who are available or reserved and have the parent skills"""
        for rec in self:
            domain = [('availability_status', '!=', 'not_available'),
                      ('company_id', '=', rec.company_id.id)]
            skill_ids = rec.field_service_request_id.hr_skill_ids
            existing_employees = rec.field_service_request_id.field_service_worker_ids.mapped(
                'employee_id')
            if existing_employees:
                domain.append(('id', 'not in', existing_employees.ids))
            if skill_ids:
                domain.append(('skill_ids', 'in', skill_ids.ids))
            rec.employee_ids = self.env['hr.employee'].search(domain)
