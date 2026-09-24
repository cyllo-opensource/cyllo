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


class WhatsappFlowsScreens(models.Model):
    """
    Model representing individual screens within a WhatsApp flow.

    Each screen includes a title, a footer button, and various content elements,
    allowing customization of the user experience in the WhatsApp flow.
    """
    _name = 'whatsapp.flows.screens'
    _description = "Whatsapp Flow Screens"

    name = fields.Char(
        string="Screen title",
        required=True,
        help='The title of the screen displayed to users in this WhatsApp flow.'
    )
    flow_id = fields.Many2one(
        comodel_name='whatsapp.flows',
        string='Flow Reference',
        help='The WhatsApp flow to which this screen belongs.'
    )
    button_name = fields.Char(
        string="Footer Button Label",
        required=True,
        default="Continue",
        help='The label displayed on the footer button for this screen, '
             'such as "Continue" or "Next".'
    )
    content_ids = fields.One2many(
        comodel_name='whatsapp.flows.screen.contents',
        inverse_name='screen_id',
        help='Content elements for this screen, defining text, media, and '
             'user input options.'
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users',
        default=lambda self: self.env.user,
        help="User responsible for managing this screen"
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        string='Associated Company',
        help="The company to which this screen is associated."
    )
