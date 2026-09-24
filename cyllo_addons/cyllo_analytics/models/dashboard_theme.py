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


class DashboardTheme(models.Model):
    """Dashboard Theme Model"""
    _name = 'dashboard.theme'
    _description = 'Dashboard Theme'

    name = fields.Char(required=True)
    background = fields.Char()
    title = fields.Char()
    subtitle = fields.Char()
    theme_color_ids = fields.One2many(
        'dashboard.theme.color',
        'theme_id',
        string='Theme'
    )
    label_text = fields.Char()
    border_width = fields.Integer()
    border_color = fields.Char()
    body_header_background = fields.Char(default="#ecedcc")
    header_title_color = fields.Char(default="#000000")

    def read_theme(self):
        """Read the theme data from the database and return it as a dictionary"""
        data = self.read([
            "name",
            "background",
            "title",
            "subtitle",
            "theme_color_ids",
            "label_text",
            "border_width",
            "border_color",
            "body_header_background",
            "header_title_color"
        ])
        if data:
            new_vals = data[0].copy()
            new_vals["theme_color_ids"] = []
            for val in data[0]['theme_color_ids']:
                new_vals["theme_color_ids"].append(
                    self.env["dashboard.theme.color"].browse(val).name)
            return new_vals
        return {}


class DashboardThemeColor(models.Model):
    """Dashboard Theme Color Model"""
    _name = 'dashboard.theme.color'
    _description = 'Dashboard Theme Color'

    name = fields.Char(
        string='Color',
        required=True
    )
    theme_id = fields.Many2one('dashboard.theme')
