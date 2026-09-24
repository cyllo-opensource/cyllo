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
from lxml import etree

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extends res.config.settings model to customize form views."""
    _inherit = "res.config.settings"
    open_ai_key = fields.Char(
        string="Open AI Key", config_parameter='cyllo_base.open_ai_key')

    @api.model
    def get_views(self, views, options=None):
        """Override get_views method to customize form view.
        Parameters:
        - views (dict): Dictionary containing views information.
        - options (dict): Additional options for customization.
        Returns:
        - dict: Modified views dictionary.
        """
        ret_val = super().get_views(views, options)
        form_view = self.env["ir.ui.view"].browse(
            ret_val["views"]["form"]["id"])
        if (not form_view.xml_id.endswith("res_config_settings_view_form")
                and "res_config_settings" not in form_view.xml_id):
            return ret_val
        doc = etree.XML(ret_val["views"]["form"]["arch"])
        query = "//setting[field[@widget='upgrade_boolean']]"
        [elem.getparent().remove(elem) for elem in doc.xpath(query)]
        [setting.getparent().remove(setting) for setting in
         doc.xpath("//setting") if len(setting) == 0]
        [container.getparent().remove(container) for container in
         doc.xpath("//block") if len(container) == 0]
        ret_val["views"]["form"]["arch"] = etree.tostring(doc)
        return ret_val
