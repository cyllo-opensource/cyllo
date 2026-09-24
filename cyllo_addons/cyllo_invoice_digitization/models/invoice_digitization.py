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
from odoo import fields, models


class InvoiceDigitization(models.Model):
    """
    Model for configuring OCR settings and digitization options for invoices."""
    _name = 'invoice.digitization'
    _description = 'Invoice Digitization'

    name = fields.Char(
        'Name',
        required=True,
        help='Enter the name for the ocr settings')
    account_type = fields.Selection(
        selection=[
            ('out_invoice', "Customer Invoice"),
            ('in_invoice', "Vendor Bills"),
        ],
        string="Invoice Type",
        required=True,
        default='out_invoice', help='Select the Invoice type')
    automation_method = fields.Selection(
        selection=[
            ('manual_digitization', "Manual Digitization"),
            ('ai_digitization', "AI Digitization"),
        ],
        string="Digitize Method",
        default='manual_digitization',
        help='Select the digitization method')
    automation_type = fields.Selection(
        selection=[
            ('not_digitize', "Do not digitize"),
            ('request_digitize', "Digitize on request only"),
            ('auto_digitize', 'Automatically Digitize'),
        ],
        string="Digitize Type",
        default='not_digitize',
        help='Select the digitization type')

    active_configuration = fields.Boolean(
        'Active',
        help="By checking the active field, the settings "
             "will be active for digitization.")
    invoice_field_details_ids = fields.One2many(
        'invoice.field.details',
        'invoice_digitization_id',
        string='Invoice Field Details')
    invoice_line_field_details_ids = fields.One2many(
        'invoice.line.field.details',
        'invoice_digitization_id',
        string='Invoice Line Field Details')
    tax_type = fields.Selection(
        selection=[
            ('tax_per_line', "Tax Per Invoice Line"),
            ('tax_per_invoice', "Tax Per Invoice"),
        ],
        string="Tax Allocating Type",
        default='tax_per_line',
        help='tax per line-Acknowledging tax per each invoice line.'
             'tax per invoice-Single tax considered for an invoice')
    product_creation_type = fields.Selection(
        selection=[
            ('create_product', "Create Product Automatically"),
            ('not_create_product', "Do Not Create Product Automatically"),
        ],
        string="Product Creation",
        default='create_product',
        help='create product - Create Product Automatically.'
             'not create product - Do Not Create Product Automatically')

    def create(self, vals):
        """
            Overrides the create method to handle the activation of settings.
            Args:
                vals (dict): Dictionary of field values for creating the record.
            Returns:
                Record: Created record with activated settings.
            Note:
                Deactivates settings in other records of the same account type.
            """
        res = super().create(vals)
        if res.active_configuration:
            records = self.env['invoice.digitization'].search(
                [('account_type', '=', res.account_type)])
            for rec in records:
                if rec.id != res.id:
                    rec.active_configuration = False
        return res

    def write(self, vals):
        """
            Overrides the write method to update the active status of settings.
            Args:
                vals (dict): Dictionary of field values for updating the record.
            Returns:
                bool: True if the write operation is successful.
            Note:
                Deactivates settings in other records of the same account type.
            """
        res = super(InvoiceDigitization, self).write(vals)
        if vals.get('active_configuration'):
            if vals.get('account_type'):
                account_type = vals.get('account_type')
            else:
                account_type = self.account_type
            records = self.env['invoice.digitization'].search(
                [('account_type', '=', account_type)])
            for rec in records:
                if rec.id != self.id:
                    rec.active_configuration = False
        return res
