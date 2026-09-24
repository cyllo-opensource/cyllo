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


class InvoiceFieldDetails(models.Model):
    """Model for defining details of fields in OCR for invoice digitization."""
    _name = 'invoice.field.details'
    _description = 'Invoice Field Details'

    invoice_field_id = fields.Many2one(
        'ir.model.fields',
        string="Fields",
        domain="[('model_id.model', '=', 'account.move'), ('name', 'in', "
               "('partner_id', 'invoice_date', 'invoice_date_due', "
               "'payment_reference', 'ref', 'invoice_incoterm_id', "
               "'invoice_payment_term_id', 'delivery_date', "
               "'incoterm_location'))]",
        help="Choose Fields to map the data from the document")
    field_keyword_ids = fields.Many2many(
        'ocr.keyword',
        string="Keyword",
        help="Add keyword to map the data for a selected field")
    invoice_digitization_id = fields.Many2one(
        'invoice.digitization',
        string='Invoice Digitization Reference')
