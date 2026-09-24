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
from odoo import api, Command, models, fields


class IrModel(models.Model):
    _inherit = 'ir.model'

    cy_display_field = fields.Char("Cyllo Display Field")

    def create_access_right(self, access_rights):
        """Create access rights for the model."""
        if access_rights:
            self.access_ids = [
                Command.create({
                    'name': access['name'],
                    'group_id': access['groupId'],
                    'perm_read': access['permRead'],
                    'perm_write': access['permWrite'],
                    'perm_create': access['permCreate'],
                    'perm_unlink': access['permDelete']}) for access in
                access_rights]

    def create_record_rule(self, record_rules):
        """Create record rules for the model."""
        if record_rules:
            self.rule_ids = [
                Command.create({
                    'name': record['name'],
                    'groups': record['groups'],
                    'domain_force': record['domain_force'],
                    'perm_read': record['permRead'],
                    'perm_write': record['permWrite'],
                    'perm_create': record['permCreate'],
                    'perm_unlink': record['permDelete']}) for record in
                record_rules]

    @api.model
    def create_new_model(self, appname, modulename):
        """Create a new custom model with default views, menus, and access rights."""
        ir_model = self.create({
            'name': appname,
            'model': 'x_cyllo_' + '_'.join(modulename.lower().split(' ')),
            'field_id': [
                Command.create({'name': 'x_cyllo_name', 'ttype': 'char',
                                'field_description': 'Name'}),
            ]
        })
        ir_model_access_user = self.env['ir.model.access'].create({
            'name': "user_access_" + '_'.join(modulename.lower().split(' ')),
            'model_id': ir_model.id,
            'group_id': self.env.ref('base.group_user').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
        })
        ir_model_access_administrator = self.env['ir.model.access'].create({
            'name': "admin_access_" + '_'.join(modulename.lower().split(' ')),
            'model_id': ir_model.id,
            'group_id': self.env.ref('base.group_system').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })
        form_view = self.env['ir.ui.view'].create({
            'name': 'Default_Form_' + '_'.join(modulename.lower().split(' ')),
            'type': 'form',
            'model': ir_model.model,
            'model_id': ir_model.id,
            'arch': f"""
                <form>
                    <header/>
                    <sheet string="{ir_model.name}"> <div class="oe_title"> 
                    <h1> <field name="x_cyllo_name" required="1" 
                    placeholder="Name..."/> </h1> </div> <group></group> </sheet> </form>"""
        })
        list_view = self.env['ir.ui.view'].create({
            'name': 'Default_List_' + '_'.join(modulename.lower().split(' ')),
            'type': 'tree',
            'model': ir_model.model,
            'model_id': ir_model.id,
            'arch': """
                <tree>
                    <field name="x_cyllo_name"/>
                </tree>
            """
        })
        search_view = self.env['ir.ui.view'].create({
            'name': 'Default_Search_' + '_'.join(modulename.lower().split(' ')),
            'type': 'search',
            'model': ir_model.model,
            'model_id': ir_model.id,
            'arch': """
                <search>
                    <field name="x_cyllo_name"/>
                </search>
            """
        })
        menu_action = self.env['ir.actions.act_window'].create({
            'name': ir_model.name,
            'res_model': ir_model.model,
            'view_mode': 'tree,form',
        })
        menu_item = self.env['ir.ui.menu'].create({
            'name': appname,
            'action': 'ir.actions.act_window,%d' % menu_action.id,
            'is_studio': True,
            # 'parent_id': '',
        })
        return (
            ir_model.name, ir_model.model, ir_model.id, ir_model_access_user,
            ir_model_access_administrator, form_view, list_view,
            search_view, menu_action, menu_item)

    @api.model
    def cyllo_get_studio_action_acl(self, model,current_model):
        """Return studio action views for ACL and related records."""
        model_view=self.search([('model', '=', model)],limit=1)

        view_refs = {
            'ir.model.access': 'cyllo_studio.view_ir_model_access_tree',
            'ir.rule': 'cyllo_studio.view_ir_rule_tree',
            'mail.template': 'cyllo_studio.cyllo_email_template_kanban',
            'ir.actions.report':'cyllo_studio.view_ir_actions_report_kanban'
        }

        n_list = self.env.ref(view_refs.get(current_model))
        if current_model=='mail.template':
            n_form = self.env.ref('cyllo_studio.cyllo_email_template_form')
            return model_view.id, n_list.id if n_list else None,n_form.id if n_form else None
        return model_view.id, n_list.id if n_list else None

    @api.model
    def get_model_actions(self, model_name):
        """
        Get all action methods available for a given model
        """
        try:
            model_obj = self.env[model_name]
            actions = []

            # Get all methods that could be button actions
            for attr_name in dir(model_obj):
                if attr_name.startswith('_'):
                    continue

                try:
                    attr = getattr(model_obj, attr_name)
                    if callable(attr) and (
                            attr_name.startswith('action_') or
                            attr_name.startswith('button_') or
                            attr_name in ['write', 'create', 'unlink']  # Common actions
                    ):
                        actions.append(attr_name)
                except:
                    continue

            return actions
        except KeyError:
            return []

    @api.model
    def validate_model_action(self, model_name, action_name):
        """
        Validate if an action exists on a model
        """
        try:
            model_obj = self.env[model_name]
            return hasattr(model_obj, action_name) and callable(getattr(model_obj, action_name))
        except KeyError:
            return False

class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.model
    def field_types(self):
        """Return grouped field types and available user groups."""
        groups = {
            'char': ['char', 'text', 'html', 'json'],
            'integer': ['integer', 'float', 'monetary'],
            'date': ['date', 'datetime'],
            'binary': ['binary', 'image'],
            'selection': ['selection'],
            'boolean': ['boolean'],
            'relationship': ['many2one', 'one2many', 'many2many'],
            'other': ['json', 'reference', 'many2one_reference']
        }
        grouped_types = {}
        for group, types in groups.items():
            grouped_types[group] = types
        groups = [{'id': i.id, 'full_name': i.full_name} for i in
                  self.env['res.groups'].search([])]
        return grouped_types, groups

    @api.model
    def get_field(self, modelValue):
        """Return fields of a given model."""
        field_value = [{'id': i.id, 'full_name': i.name} for i in
                       self.search([('model', '=', modelValue)])]
        return field_value
