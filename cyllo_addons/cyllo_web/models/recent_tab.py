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

from odoo import models, fields

class RecentTab(models.Model):
    _name = 'recent.tab'
    _description = 'Recent Tab'

    name = fields.Char(string="Name", required=True, help="The name of the tab/view")
    user_id = fields.Integer(string="User", required=True)
    item_id = fields.Integer(string="Item",default=False)
    tab_url = fields.Char(string="Url", required=True, help="Url of the tab/view")
    action_id = fields.Integer(string="Action")
    company_id = fields.Integer(string="Company")
    menu_id = fields.Integer(string="Menu")
    last_visited = fields.Char(string="Last Visited")
    res_model = fields.Char(string="Model", help="The name of the model")
    view_type = fields.Char(string="View", help="The type of view")
    path_name = fields.Char(string="Path", help="The path of the url")
    hash = fields.Char(string="Hash", help="The hash of the url")