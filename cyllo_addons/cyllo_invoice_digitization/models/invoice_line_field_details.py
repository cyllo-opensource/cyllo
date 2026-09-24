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


class InvoiceLineFieldDetails(models.Model):
    """
    Model for defining details of fields in OCR for invoice line digitization.
    """
    _name = 'invoice.line.field.details'
    _description = 'Invoice Line Field Details'

    invoice_line_field_id = fields.Many2one(
        'ir.model.fields', "Fields",
        domain="[('model_id.model', '=', 'account.move.line'), "
               "('name', 'in', ('product_id', 'quantity', 'price_unit', "
               "'tax_ids', 'discount', 'default_code', 'discount', 'price_subtotal'))]",
        help="Choose Fields to map the data from the document")
    line_field_keyword_ids = fields.Many2many(
        'ocr.keyword',
        string="Keyword",
        help="Add keyword to map the data for a selected field")
    invoice_digitization_id = fields.Many2one(
        'invoice.digitization',
        'Invoice Digitization Reference')
