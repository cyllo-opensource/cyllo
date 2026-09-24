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
from odoo.exceptions import ValidationError


class FieldServiceInvoice(models.TransientModel):
    """wizard for choosing invoice methods"""
    _name = 'field.service.invoice'
    _description = 'Field Service Invoice'

    invoice_service = fields.Boolean()
    invoice_timesheet = fields.Boolean()
    timesheet_ids = fields.One2many('field.service.invoice.line', "field_service_invoice_id")
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)

    def action_create_invoice(self):
        """
        Trigger the creation of an invoice based on service, timesheet or both type.
        :return: Action to open the created invoice in the current window.
        """
        if not self.invoice_timesheet and not self.invoice_service:
            raise ValidationError("At least one should be selected to create invoice!")
        invoice_action = {
            'name': 'create_invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current'
        }
        fs_request = self.env['field.service.request'].browse(
            self.env.context.get('active_id'))
        if self.invoice_service and not self.invoice_timesheet:
            invoice = fs_request.action_create_invoices('service')
        elif self.invoice_timesheet and not self.invoice_service:
            total_amount = sum(self.timesheet_ids.mapped('total'))
            invoice = fs_request.action_create_invoices('timesheet', total_amount)
        else:
            total_amount = sum(self.timesheet_ids.mapped('total'))
            invoice = fs_request.action_create_invoices('service_timesheet', total_amount)

        if not invoice:
            raise ValidationError(
                "No invoice could be created. Please ensure that:\n"
                "- The Service Checklist has at least one item marked as 'Completed' with a cost greater than 0, if invoicing for Service.\n"
                "- Timesheet entries exist with hours and cost recorded, if invoicing for Timesheet."
            )
        invoice_action['res_id'] = invoice.id
        return invoice_action

class FieldServiceInvoiceLine(models.TransientModel):
    _name = 'field.service.invoice.line'
    _description = 'Field service invoice line'

    field_service_invoice_id = fields.Many2one('field.service.invoice')
    employee_id = fields.Many2one('hr.employee', readonly=True)
    cost = fields.Float(compute="_compute_hourly_cost", readonly=False,
                        string="Cost Per Hour")
    hours = fields.Float("Hours Spent")
    description = fields.Char()
    date = fields.Date()
    total = fields.Float(compute="_compute_total", store=True)

    @api.depends('employee_id.hourly_cost')
    def _compute_hourly_cost(self):
        for rec in self:
            if rec.employee_id:
                rec.cost = rec.employee_id.hourly_cost
            else:
                rec.cost = 0

    @api.depends('hours', 'cost')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.cost*rec.hours
