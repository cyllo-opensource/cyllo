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
from validate_email import validate_email

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmailDigitizationConfig(models.Model):
    """Configuration model for email digitization in Cyllo."""
    _name = 'email.digitization.config'
    _description = 'Email Digitization Configuration'
    _rec_name = 'email'

    email = fields.Char(
        required=True,
        help='Enter the email for applying the configuration for only this email.'
    )
    model_id = fields.Many2one(
        'ir.model',
        'Choose Model',
        domain="([('model', 'in', ('purchase.order', 'sale.order'))])")
    model_name = fields.Char(
        related='model_id.model',
        store=True)
    active_configuration = fields.Boolean(
        'Active',
        help="By checking the active field, the settings will be active for digitization.")
    digitize_type = fields.Selection(
        selection=[('use_ai', "Digitize using AI"),
                   ('use_keyword', "Digitize using keyword")],
        string="Type",
        default='use_ai',
        help='Digitize using AI - Digitization automatically works using AI.Digitize using keyword - '
             'Digitization works only based on the keywords')
    purchase_line_field_details_ids = fields.One2many(
        'purchase.line.field.details',
        'email_digitization_id')
    sale_line_field_details_ids = fields.One2many(
        'sale.line.field.details',
        'email_digitization_id')
    tax_type = fields.Selection(
        selection=[('tax_per_line', "Tax Per Line"),
                   ('tax_per_invoice', "Tax Per Order")],
        string="Tax Allocating Type",
        default='tax_per_line',
        help='tax_per_line - Acknowledging tax per each Order line.tax_per_invoice-Single tax considered for an Order')
    product_creation_type = fields.Selection(
        selection=[('create_product', "Create Product Automatically"),
                   ('not_create_product',
                    "Do Not Create Product Automatically")],
        string="Product Creation",
        default='create_product',
        help='create_product - Create Product Automatically.not_create_product - Do Not Create Product Automatically')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company)

    @api.constrains('email')
    def _check_email(self):
        """
        Check the email is valid or not
        """
        if self.email:
            is_valid = validate_email(
                self.email,
                check_mx=False,
                verify=True,
                debug=False,
                smtp_timeout=10)
            if is_valid is not True:
                raise ValidationError(_('You can use only valid email address.'
                                        'Email address "%s" is invalid '
                                        'or does not exist') % self.email)

    def create(self, vals):
        """Overrides the create method to ensure only one active configuration
         per email.
            Args:
                vals (dict): Dictionary of field values.
            Returns:
                res (models.Model): Created record. """
        res = super().create(vals)
        if res.active_configuration:
            records = self.env['email.digitization.config'].search(
                [('email', '=', res.email)])
            for rec in records:
                if rec.id != res.id:
                    rec.active_configuration = False
        return res

    def write(self, vals):
        """
        Overrides the write method to manage the active configuration status.
        Args:
            vals (dict): Dictionary of field values.
        Returns:
            res (models.Model): Updated record."""
        res = super(EmailDigitizationConfig, self).write(vals)
        if vals.get('active_configuration'):
            if vals.get('email'):
                email = vals.get('email')
            else:
                email = self.email
            records = self.env['email.digitization.config'].search(
                [('email', '=', email)])
            for rec in records:
                if rec.id != self.id:
                    rec.active_configuration = False
        return res
