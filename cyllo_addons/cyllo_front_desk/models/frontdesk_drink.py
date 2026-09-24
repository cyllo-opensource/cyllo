# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields

class FrontdeskDrink(models.Model):
    _name = 'frontdesk.drink'
    _description = 'Frontdesk Drink'
    _order = 'sequence, id'

    name = fields.Char(string='Drink Name', required=True, translate=True)
    sequence = fields.Integer(default=10, string='Sequence')
    notify_user_ids = fields.Many2many('hr.employee', string='People to Notify', help='Employees to notify when this drink is selected')
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    active = fields.Boolean(default=True, string='Active')
