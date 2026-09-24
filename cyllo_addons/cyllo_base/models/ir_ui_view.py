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
from xml.etree import ElementTree

from odoo import api, fields, models


class IrUiView(models.Model):
    """Inherits ir ui view"""
    _inherit = 'ir.ui.view'

    flag = fields.Boolean(
        default=False,
        help="Uses to know if the label changing is done correctly")

    @api.model
    def edit_xml_field_label(self, model_name, view_type, field_string,
                             input_field_name, value):
        """ Function to change label(string) of fields for which the changes
           made from form view.
           args: Current model, View type, field's current string, field
           technical name, changed string """
        # remove input_field_name's suffix '_0'
        input_field_name = input_field_name.replace("_0", "")
        # remove input_field_name's suffix '?'
        field_string = field_string.replace("?", "")
        views = self.env['ir.ui.view'].search(
            [('model', '=', model_name), ('type', '=', view_type)])
        use_lang = self.env.context.get('lang') or 'en_US'
        for view_id in views:
            arch = ElementTree.fromstring(view_id.arch)
            for label in arch.iter('label'):
                if label.get('string') == field_string:
                    label.set('string', value)
                    vals = ElementTree.tostring(arch, encoding='unicode')
                    final_view = self.env['ir.ui.view'].sudo().search(
                        [('model', '=', model_name), ('type', '=', view_type),
                         ('xml_id', '=', view_id.xml_id)])
                    for form_view in final_view.filtered(
                            lambda xml: xml.xml_id == view_id.xml_id):
                        form_view.arch = vals
                    self.flag = True
            for field in arch.iter('field'):
                if field.get('string') == field_string:
                    self.flag = True
                    field.set('string', value)
                    vals = ElementTree.tostring(arch, encoding='unicode')
                    final_view = self.env['ir.ui.view'].sudo().search(
                        [('model', '=', model_name), ('type', '=', view_type),
                         ('xml_id', '=', view_id.xml_id)])
                    for form_view in final_view.filtered(
                            lambda xml: xml.xml_id == view_id.xml_id):
                        form_view.arch = vals
        if self.flag:
            return True
        else:
            try:
                self.env.cr.execute("""UPDATE ir_model_fields SET field_description = 
                '{"%s":"%s"}' WHERE model = '%s' AND name = '%s' """ % (
                use_lang, value, model_name, input_field_name))
                self.env.cr.commit()
                self.env.registry.clear_cache()
                return True
            except:
                return False
