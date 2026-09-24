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


class FlowUserResponseLine(models.Model):
    """
    Represents a line item for user responses in a WhatsApp flow. Each line
    corresponds to a specific field in the flow screen and captures the user's
    input.
    """
    _name = "flows.user.response.line"
    _description = "Flow User Response Line"

    response_id = fields.Many2one(
        comodel_name='flows.user.response',
        string='Response',
        help="The user response record this line belongs to."
    )
    field_label = fields.Char(
        string='Field Label',
        help="The label of the field in the WhatsApp flow screen."
    )
    user_input = fields.Char(
        string='User Input',
        help="The input provided by the user in response to the field."
    )
    screen_id = fields.Many2one(
        comodel_name='whatsapp.flows.screens',
        help="The screen where this response line belongs in the WhatsApp flow."
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        help="The product associated with this user response, if applicable."
    )
    response_key = fields.Char(
        string='Response Key',
        help="A unique key identifying the response field."
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users', default=lambda self: self.env.user,
        help='The user is responsible for this response'
    )
    company_id = fields.Many2one(
        comodel_name='res.company', required=True,
        default=lambda self: self.env.company,
        string='Associated Company',
        help='Select the company under which this WhatsApp response line is managed.'
    )
