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


class ProjectTask(models.Model):
    """In this class we are defining the additional fields required for the
    model project.task."""
    _inherit = 'project.task'

    employee_ids = fields.Many2many('hr.employee', string="Employees",
                                    help="Employees assigned to the task")
    service_id = fields.Many2one('field.service.request',
                                 compute='compute_service_id')

    def compute_service_id(self):
        """
            This method computes the service ID for each record in the current
            recordset based on the linked task.

            It iterates through each record and searches for a matching service
            request record in the `field.service.request` model.
            The search criteria is based on the `task_id` field of the service
            request being equal to the current record's ID.

            If a matching service request is found, its ID is assigned to the `
            service_id` field of the current record.
            Otherwise, the `service_id` field remains False.

        """
        self.service_id = False
        for rec in self:
            service = self.env['field.service.request'].search(
                [('task_id', '=', rec.id)], limit=1)
            rec.service_id = service.id

    def _create_fsm_request(self):
        """Create a draft field.service.request for tasks that:
        - belong to an is_fsm project
        - have a customer (partner_id) set
        - don't already have a linked request
        skill_category_id is required on field.service.request, so we fetch
        the first available category; if none exists the creation is skipped.
        """
        if self.env.context.get('skip_fsm_request_creation'):
            return
        FSR = self.env['field.service.request'].sudo()
        for task in self:
            # Must belong to an FSM project
            if not task.project_id or not task.project_id.is_fsm:
                continue
            # Skip if a request already exists for this task
            if FSR.search([('task_id', '=', task.id)], limit=1):
                continue
            # Resolve customer: task partner → project partner
            partner = task.partner_id or task.project_id.partner_id
            FSR.create({
                'name': task.name or 'New',
                'task_id': task.id,
                'project_id': task.project_id.id,
                'partner_id': partner.id if partner else False,
                # 'skill_category_id': category.id,
                'company_id': self.env.company.id,
                'state': 'draft',
            })

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._create_fsm_request()
        return tasks

    def write(self, vals):
        res = super().write(vals)
        # Re-check if project changed or partner was set for the first time
        if 'project_id' in vals or 'partner_id' in vals:
            self._create_fsm_request()
        return res