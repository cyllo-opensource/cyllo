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
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class FieldServiceChecklist(models.Model):
    """In this class we are defining the fields required for the model field.service.checklist."""
    _name = "field.service.checklist"
    _rec_name = 'product_id'
    _description = "Field Service Checklist"

    required = fields.Boolean(
        help="Boolean to specify whether this checklist compulsory  or not")
    time_required = fields.Float(string="Required Time",
                                 help="Time required to complete the task")
    status = fields.Selection(
        selection=[('pending', 'Pending'), ('completed', 'Completed')],
        default='pending',
        help="Status represent the task completed or not", required=True,
        readonly=True)
    field_service_request_id = fields.Many2one('field.service.request',
                                               string="Service Request",
                                               help="Service request",
                                               ondelete='cascade')
    currency_id = fields.Many2one('res.currency', default=lambda
        self: self.env.company.currency_id)
    service_cost = fields.Monetary(currency_field='currency_id', default=0)
    product_id = fields.Many2one('product.product', 'Service product',domain=[('detailed_type', '=', 'service')],
                                 required=True)

    def action_mark_as_done(self):
        """This function used to mark the checklist as done"""
        if self.field_service_request_id.state == "in_progress":
            self.write({'status': 'completed'})
        else:
            raise ValidationError(
                _("To mark job as done, assign workers and start service"))
