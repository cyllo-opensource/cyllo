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


class PurchaseFieldDetails(models.Model):
    """
        Defines the details of purchase order fields for purchase digitization
        in cyllo.
        """
    _name = 'purchase.field.details'
    _description = 'Purchase Field Details'

    purchase_field_id = fields.Many2one(
        'ir.model.fields',
        string="Fields",
        domain="[('model_id.model', '=', 'purchase.order'), ('name', 'in', "
               "('partner_ref', 'payment_term_id', 'incoterm_id', "
               "'incoterm_location'))]",
        help="Choose Fields to map the data from the document", required=True, ondelete="cascade")
    field_keyword_ids = fields.Many2many(
        'ocr.keyword',
        string="Keyword",
        help="Add keyword to map the data for a selected field")
    purchase_digitization_id = fields.Many2one(
        'purchase.digitization',
        string='Purchase Digitization Reference')
