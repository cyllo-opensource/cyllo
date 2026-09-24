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


class DashboardConfigMenu(models.TransientModel):
    """Dashboard Configuration Menu Model"""
    _name = 'dashboard.config.menu'
    _description = "Dashboard Configuration Menu"

    name = fields.Char(help='Add the name for the new menu')
    menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Parent Menu',
        help='Choose the parent menu'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=0,
        help='Set the sequence number to control the menu order'
    )
