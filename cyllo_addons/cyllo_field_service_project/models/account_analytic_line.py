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


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    service_id = fields.Many2one('field.service.request',
                                 compute='compute_service_id',
                                 store=True)
    workers_ids = fields.Many2many(related="service_id.workers_ids")
    employee_ids = fields.Many2many(related="task_id.employee_ids")

    @api.depends('date')
    def compute_service_id(self):
        """
            This method computes the service ID for each record in the current
            recordset.

            It iterates through each record and retrieves the service ID from
            the context.
            If a service ID is found in the context, it is assigned to the
            `service_id` field of the record.
            Otherwise, the `service_id` field is set to False.
        """
        self.service_id = False
        for rec in self:
            service = self.env['field.service.request'].browse(
                self.env.context.get('service_id'))
            rec.service_id = service.id
