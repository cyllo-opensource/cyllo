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


class SignField(models.Model):
    """
       Model representing the different types of fields that can be placed
       on a signable document (e.g., text box, signature box, or date field).
    """
    _name = 'sign.field'
    _description = "Sign Field"

    name = fields.Char('Field Name', required=True)
    field_type = fields.Selection([('text', 'Text'), ('signature', 'Signature'),
                                   ('date', 'Date')], default="text",
                                  string='Field Type')
    icon = fields.Char("Icon")
    default_width = fields.Float()
    default_height = fields.Float()
    placeholder = fields.Char()
