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


class DashboardPresentation(models.TransientModel):
    """Dashboard Presentation Model"""
    _name = 'dashboard.presentation'
    _description = 'Dashboard Presentation'

    chart_data = fields.Json()
    type = fields.Char()
    style = fields.Char()
    style_json = fields.Json()
    theme = fields.Char()
    theme_json = fields.Json()
    auto_slide = fields.Boolean()
    auto_slide_time = fields.Integer(string='Auto Slide Duration')
    title_page = fields.Boolean()
    title_page_heading = fields.Char()
    title_page_subheading = fields.Char()
