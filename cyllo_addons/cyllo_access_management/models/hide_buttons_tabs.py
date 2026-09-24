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
from odoo import fields,models


class HideButtonsTabs(models.Model):
    _name = 'hide.buttons.tabs'
    _description = 'Hide Buttons Tabs'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one(
        'profile.management',
        string='Profile Management ID',
        help="The profile management record this rule belongs to."
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="The target Cyllo model containing the buttons or tabs."
    )
    button_ids = fields.Many2many(
        'ir.buttons',
        string='Hide Buttons',
        help="Choose which model buttons to hide for this profile."
    )
    tab_ids = fields.Many2many(
        'ir.tabs',
        string='Hide Tabs',
        help="Choose which model notebook tabs to hide for this profile."
    )