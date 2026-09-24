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


class ScreenContentOptions(models.Model):
    """
    Represents options for screen content in a WhatsApp flow.

    This model is used to define and manage the options associated with specific
    content in a WhatsApp flow screen. Each option is linked to a specific
    content record and is associated with a responsible user and company.

    """
    _name = 'screen.content.options'
    _description = 'WhatsApp Flow Screen Content Options'

    content_id = fields.Many2one(
        comodel_name='whatsapp.flows.screen.contents',
        string='Content',
        help='The specific screen content this option belongs to in the'
             ' WhatsApp flow.'
    )
    options = fields.Char(
        string='Options',
        help='The selectable option text for the screen content.'
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users',
        default=lambda self: self.env.user,
        help='The user responsible for managing this screen content option.'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
        string='Associated Company',
        help='The company associated with this screen content option.'
    )
