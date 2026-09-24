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
from odoo import _, api, fields, models


class FieldCreate(models.TransientModel):
    """ Creates Field Create """
    _name = 'field.create'
    _description = 'Field Create'

    def get_xml_ids(self, model):
        """ Function to get external id of current form
            param: model - current model receives from js,
            Return: model and external id of form for pass to js"""
        self.model = model
        form_external_id = []
        model = self.env['ir.model'].sudo().search([('model', '=', model)])
        for view in self.env['ir.ui.view'].sudo().search(
                [('model_id.model', '=', model), ('type', '=', 'form'),
                 ('mode', '=', 'primary')]):
            if view.model_id.model == model.model:
                form_external_id.append(view.xml_id)
        if len(form_external_id) >= 1:
            form_external_id = form_external_id[0]
        return {
            'model': self.model,
            'form_external_id': form_external_id,
        }

    @api.model
    def get_possible_field_types(self):
        """Return all available field types"""
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        field_list.remove(('monetary', 'monetary'))
        field_list.remove(('json', 'json'))
        return field_list

    name = fields.Char(string="Field Name", help="Technical name of field",
                       default="x_", required=True)
    same_name = fields.Boolean(
        string="Is Same Name",
        help="Is same name is used for field in this model")
    name_x_ = fields.Boolean(string="Is Name Correct",
                             help="Is name starts with 'x_'")
    display_name = fields.Char(help='Display name of field', required=True)
    model = fields.Char(help="Stores current model to filter the fields")
    ref_model_id = fields.Many2one(
        'ir.model', string='Reference Model',
        help="Reference model for Many2one and Many2many field creation")
    field_id = fields.Many2one(
        'ir.model.fields', string='Position Field', required=True,
        help="Select a position field for create new field",
        domain=lambda self: "[('model', '=', model)]")
    form_view_external_id = fields.Char(
        string="External Id", help="Form View External Id", readonly=True)
    position = fields.Selection(
        selection=[('before', 'Before'), ('after', 'After')],
        help="Position of field", required=True)
    field_type = fields.Selection(
        selection='get_possible_field_types', help="Type of field",
        required=True)
    widget_id = fields.Many2one(
        'field.widget', help="Widget for the field",
        domain=lambda self: "[('datatype', '=', ""field_type)]")
    selection_ids = fields.One2many(
        'field.selection', 'create_id', help="Options for new selection field")
    required = fields.Boolean(help="Does this a required field")
    readonly = fields.Boolean(help="Is this is a readonly field")
    store = fields.Boolean(
        default=False, help="Whether the value is stored in database")
    index = fields.Boolean(
        string="Indexed", help="Does the field need to be indexed")
    copied = fields.Boolean(
        help="Does the value in the field can be copied, eg: while duplicating"
             " the record", default=True)
    help = fields.Text(string="Field Help", help="Use of the Field")

    @api.onchange('name')
    def _onchange_name(self):
        """Check if there is any field with same technical_name in this
        model"""
        if self.name and self.env['ir.model.fields'].search([]).filtered(
                lambda field: field.name == self.name and field.model == self.model):
            self.same_name = True
        else:
            self.same_name = False
        if self.name and not self.name.startswith("x_"):
            self.name_x_ = True
        else:
            self.name_x_ = False

    @api.onchange('field_type')
    def _onchange_field_type(self):
        """ Set store to True is field type is selection
            Use: To show the newly creating selection even in the saved view 
                    if it's not stored after saved the value not displayed."""
        if self.field_type == 'selection':
            self.store = 1

    def action_create_field(self):
        """ Function to create dynamic field in current record
            @Return: A client action and reload the page."""
        tree_xml_id = []
        tree_view_id = []
        form_view_id = []
        model = self.env['ir.model'].search(
            [('model', '=', self.env.context['active_model'])])
        for view in self.env['ir.ui.view'].search(
                [('model_id.model', '=', model), ('type', '=', 'tree'),
                 ('mode', '=', 'primary'), ('inherit_id', '=', False)]):
            if view.model_id.model == model.model:
                tree_view_id.append(view.id)
                tree_xml_id.append(view.xml_id)
        for view in self.env['ir.ui.view'].search(
                [('model_id.model', '=', model), ('type', '=', 'form'),
                 ('mode', '=', 'primary')]):
            if view.model_id.model == model.model:
                form_view_id.append(view.id)
                tree_xml_id.append(view.xml_id)
        if len(form_view_id) >= 1:
            form_view_id = form_view_id[0]
        if len(tree_view_id) >= 1:
            tree_view_id = tree_view_id[0]
        field_data = {
            'name': self.name,
            'field_description': self.display_name,
            'model_id': model.id,
            'ttype': self.field_type,
            'is_dynamic_field': True
        }
        if self.ref_model_id:
            field_data['relation'] = self.ref_model_id.model
        if self.required:
            field_data['required'] = True
        if self.index and not self.widget_id.name == 'image':
            field_data['index'] = True
        if self.store:
            field_data['store'] = True
        if self.copied:
            field_data['copied'] = True
        if self.readonly:
            field_data['readonly'] = True
        if self.help:
            field_data['help'] = self.help
        self.env['ir.model.fields'].sudo().create(field_data)
        if self.field_type == 'selection':
            sequence = 0
            new_field_id = (self.env['ir.model.fields'].search([]).filtered(
                lambda
                    field: field.name == self.name and field.model == self.model))
            for option in self.selection_ids:
                self.env['ir.model.fields.selection'].sudo().create({
                    'field_id': new_field_id.id,
                    'value': option.value,
                    'name': option.name,
                    'sequence': sequence,
                })
                sequence += 1
        form_arch_base = _('<?xml version="1.0"?>'
                           '<data>'
                           '''<field name="%s" position="%s">'''
                           '''<field name="%s"/>'''
                           '''</field>'''
                           '''</data>''') % (self.field_id.name,
                                             self.position, self.name)
        if self.widget_id:
            form_arch_base = _('<?xml version="1.0"?>'
                               '<data>'
                               '''<field name="%s" position="%s">'''
                               '''<field name="%s" widget="%s"/>'''
                               '''</field>'''
                               '''</data>''') % (self.field_id.name,
                                                 self.position, self.name,
                                                 self.widget_id.name)
        view_rec = self.env['ir.ui.view'].sudo().create(
            {'name': str(model.model) + ".form." + "add.field." + self.name,
             'type': 'form',
             'model': model.model,
             'mode': 'extension',
             'inherit_id': form_view_id,
             'arch_base': form_arch_base,
             'active': True})
        data_list = [{
            'xml_id': "bg_dynamic_field." + model.model.replace('.', '_') +
                      '_form_field.' + self.name,
            'record': view_rec}]
        self.env['ir.model.data']._update_xmlids(data_list)
        tree_arch_base = _('<?xml version="1.0"?>'
                           '''<data>'''
                           '''<xpath expr="//tree" position="inside">'''
                           '''<field name="%s" optional="hide"/>'''
                           '''</xpath>'''
                           '''</data>''') % self.name
        view_rec = self.env['ir.ui.view'].sudo().create(
            {'name': str(model.model) + ".tree." + "add.field." + self.name,
             'type': 'tree',
             'model': model.model,
             'mode': 'extension',
             'inherit_id': tree_view_id,
             'arch_base': tree_arch_base,
             'active': True})
        data_list = [{
            'xml_id': "bg_dynamic_field." + model.model.replace('.', '_') +
                      '_tree_field.' + self.name,
            'record': view_rec}]
        self.env['ir.model.data']._update_xmlids(data_list)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'form_view_id': form_view_id,
        }
