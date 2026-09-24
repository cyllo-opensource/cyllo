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


class DashboardGlobalFilter(models.Model):
    """Model representing global filters used in dashboards."""
    _name = "dashboard.global.filter"
    _description = "Dashboard Global Filter"

    name = fields.Char()
    type = fields.Char()
    dashboard_config_id = fields.Many2one("dashboard.config")
    relation = fields.Char()
    code = fields.Char()
    operator = fields.Selection([
        ("=", "="),
        (">=", ">="),
        ("<=", "<="),
        ("in", "in")
    ])
