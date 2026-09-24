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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    """Extends the 'res.partner' model to add fields related to WhatsApp numbers."""
    _inherit = 'res.partner'

    phone_country_code_id = fields.Many2one('res.country',
                                            string="Country Code",
                                            help="Enter the whatsapp phone number country code",
                                            compute="_compute_phone_country_code",
                                            store=True)
    phone_number = fields.Char(help="Enter the whatsapp phone number",
                               compute="_compute_phone_country_code",
                               store=True)
    whatsapp_number = fields.Char(help="Whatsapp phone number",
                                  compute="_compute_whatsapp_number",
                                  readonly=False, store=True)

    @api.depends('phone_country_code_id', 'phone_number')
    def _compute_whatsapp_number(self):
        """Compute the WhatsApp number based on the country code and phone number."""
        for record in self:
            if record.phone_country_code_id and record.phone_number:
                country_code = record.phone_country_code_id.phone_code
                if type(record.id) == fields.Integer:
                    contacts = self.sudo().search([('whatsapp_number', '=',
                                                    f"{country_code}{record.phone_number}"),
                                                   ('id', '!=', record.id)])
                    if contacts:
                        record.phone_number = False
                        raise UserError(
                            _('Whatsapp number already exist!. Change whatsapp number'))
                record.whatsapp_number = f"{country_code}{record.phone_number}"

    @api.depends('whatsapp_number')
    def _compute_phone_country_code(self):
        """Compute the WhatsApp number based on the country code and phone number."""
        for partner in self:
            if not partner.whatsapp_number:
                partner.phone_country_code_id = False
                partner.phone_number = False
                continue

            countries = self.env['res.country'].search([])
            found = False

            if partner.whatsapp_number.startswith('+'):
                partner.whatsapp_number = partner.whatsapp_number.lstrip('+')

            for country in countries:
                code = str(country.phone_code)
                if partner.whatsapp_number.startswith(code):
                    partner.phone_country_code_id = country
                    partner.phone_number = partner.whatsapp_number[len(code):]
                    found = True
                    break

            if not found:
                partner.phone_country_code_id = False
                partner.phone_number = partner.whatsapp_number
