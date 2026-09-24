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


class PurchaseDigitization(models.Model):
    """
       Model for configuring settings related to purchase digitization.
       """
    _name = 'purchase.digitization'
    _description = 'Purchase Digitization'

    name = fields.Char(
        'Name',
        required=True,
        help='Enter the name for the ocr settings')
    automation_type = fields.Selection(
        selection=[
            ('not_digitize', "Do not digitize"),
            ('request_digitize', "Digitize on request only"),
            ('auto_digitize', 'Automatically Digitize'),
        ],
        string="Digitize Type",
        default='not_digitize',
        help='Select the digitization type')
    automation_method = fields.Selection(
        selection=[
            ('manual_digitization', "Manual Digitization"),
            ('ai_digitization', "AI Digitization"),
        ],
        string="Digitize Method",
        default='manual_digitization',
        help='Select the digitization method')
    active_configuration = fields.Boolean(
        'Active',
        help="By checking the active field, the settings "
             "will be active for digitization.")
    purchase_field_details_ids = fields.One2many(
        'purchase.field.details',
        'purchase_digitization_id',
        'Purchase Field Details')
    purchase_line_field_details_ids = fields.One2many(
        'purchase.line.field.details',
        'purchase_digitization_id',
        string='Purchase Line Field Details')
    tax_type = fields.Selection(
        selection=[
            ('tax_per_line', "Tax Per Purchase Line"),
            ('tax_per_invoice', "Tax Per Purchase Order"),
        ],
        string="Tax Allocating Type",
        default='tax_per_line',
        help='tax per line-Acknowledging tax per each purchase line.'
             'tax per invoice-Single tax considered for an Purchase order')
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
        Override of the create method to ensure only one active configuration.
        :param vals: Dictionary of field values.
        :return: Created record.
        """
        res = super().create(vals)
        if res.active_configuration:
            records = self.env['purchase.digitization'].search([])
            for rec in records:
                if rec.id != res.id:
                    rec.active_configuration = False
        return res

    def write(self, vals):
        """
        Override of the write method to manage the active configuration setting.
        :param vals: Dictionary of field values.
        :return: True if successful.
        """
        res = super(PurchaseDigitization, self).write(vals)
        if vals.get('active_configuration'):
            records = self.env['purchase.digitization'].search([])
            for rec in records:
                if rec.id != self.id:
                    rec.active_configuration = False
        return res
