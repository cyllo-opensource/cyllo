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
import json

from odoo import Command, release
from odoo.http import Controller, request, route
from odoo.addons.iap.tools import iap_tools

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'



class NewAIApp(Controller):
    # New AI Module creation controllers
    @route('/cyllo_studio/analyze/prompt', type="json", auth="user", csrf=False)
    def analyze_prompt(self, prompt, previous_response=None):
        # Check if the prompt is incomplete
        if not prompt or len(
                prompt.split()) < 5:  # Example: check if prompt has less than 3 words
            return {
                "error": "The provided prompt is incomplete. Please provide more details to proceed."
            }
        module_description_prompt = (
            "Analyze the following prompt, If the prompt is valid or meaningful, provide an Odoo 17 module structure in **only JSON format** "
            "with the following structure:"
            "{"
            '"summary": <Add a two-line summary of the module>,'
            '"module_name": <module name, for example: sale_order>,'
            '"models": ['
            '{'
            '"model_name": <model name, for example: sale.order>,'
            '"fields": ['
            '{"field_name": <field name>, "field_type": <field type>, "field_description": <field description>,"relation": <related model name strictly from the newly created models within this structure>, "string": <string of the field>},'
            ']'
            '}'
            ']'
            '}'
            "If the field type is selection? add a new key as 'options' and values like 'options': {'option_one': 'Option One', 'option_two': 'Option Two', 'option_three': 'Option Three'} like selection define in odoo"
            "Ensure that relational fields (Many2one, Many2many, and One2many) reference only the newly created models in this structure. "
            "Exclude any references to pre-existing database models such as `res.partner`, `res.users`, or others. "
            "Ensure the response contains no additional text, explanations, or formatting, strictly returning JSON with key values in double quotes.\n"
        )
        if previous_response:
            module_description_prompt += f"Previous response:\n{previous_response}\n\n"
        module_description_prompt += f"New prompt: {prompt}"
        config_parameter = request.env['ir.config_parameter'].sudo()
        olg_api_endpoint = config_parameter.get_param(
            'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
        response = iap_tools.iap_jsonrpc(
            olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': module_description_prompt,
                'conversation_history': [],
                'version': release.version}, timeout=30)
        if response['status'] == 'success':
            response_text = response['content'].strip()
            # if response_text:
            return {'content': response_text}
        else:
            return {'error': response.get('status', 'error')}

    @route('/cyllo_studio/create/module', type="json", auth="user", csrf=False)
    def create_module(self, module_details):
        module_data = module_details[-1]
        description = module_data.get('description', {})
        module_name = description.get('module_name', '')
        models = description.get('models', [])
        # Ensure module details are valid
        if not module_name or not models:
            return {"error": "Invalid module details provided."}
        # Create the module
        existing_module = request.env['ir.module.module'].sudo().search(
            [('name', '=', module_name)])
        if existing_module:
            return {"error": f"The module '{module_name}' already exists."}

        # Create Main Menu for the module
        def to_camel_case(text):
            words = text.replace('_', ' ').replace('.', ' ').split()
            return ' '.join(
                word.capitalize() for word in words)  # Convert to CamelCase

        main_menu_name = to_camel_case(module_name)
        main_menu = request.env['ir.ui.menu'].sudo().create({
            'name': main_menu_name,
            'parent_id': False,
            'action': False,
        })
        model_action = None
        model = None
        for model_data in models:
            model_name = model_data.get('model_name', '')
            fields = model_data.get('fields', [])
            # Check for existing model
            existing_model = request.env['ir.model'].sudo().search(
                [('name', '=',
                  'x_cyllo_' + '_'.join(model_name.lower().split(' ')))],
                limit=1)
            if existing_model:
                print(
                    f"Model '{model_name}' already exists, fields will be processed.")
            # Create or fetch the model
            model = existing_model or request.env['ir.model'].sudo().create({
                'name': model_name,
                'model': 'x_cyllo_' + '_'.join(model_name.lower().split(' ')),
            })
            # Create fields for the model
            for field in fields:
                field_name = 'x_cyllo_' + field.get('field_name',
                                                    '').lower().replace(' ',
                                                                        '_')
                field_type = field.get('field_type', '').lower()
                field_description = field.get('field_description', '')
                relation_model = field.get('relation', '')
                string = field.get('string', '')
                if relation_model:
                    relation_model = 'x_cyllo_' + '_'.join(
                        relation_model.lower().split(' '))
                # Check if the field already exists
                field_exists = request.env['ir.model.fields'].sudo().search(
                    [
                        ('model_id.model', '=', model.model),
                        ('name', '=', field_name),
                    ], limit=1
                )
                if field_exists:
                    continue
                if field_type in ['many2one', 'one2many', 'many2many']:
                    if relation_model:
                        related_model_record = request.env[
                            'ir.model'].sudo().search(
                            [('model', '=', relation_model)], limit=1)

                        if not related_model_record:
                            related_model_record = request.env[
                                'ir.model'].sudo().create({
                                'name': relation_model,
                                'model': relation_model,
                            })
                        field_data = {
                            'model_id': model.id,
                            'name': field_name,
                            'ttype': field_type,
                            'field_description': field_description,
                            'relation': relation_model
                        }
                        if field_type == 'one2many':
                            inverse_field_name = f"x_cyllo_{model_name.split('.')[-1]}_id"
                            many2one_field_exists = request.env[
                                'ir.model.fields'].sudo().search([
                                ('model_id.model', '=', relation_model),
                                ('name', '=', inverse_field_name),
                                ('ttype', '=', 'many2one'),
                                ('relation', '=', model.model)
                            ], limit=1)
                            if not many2one_field_exists:
                                request.env['ir.model.fields'].sudo().create({
                                    'name': inverse_field_name,
                                    'model_id': related_model_record.id,
                                    'ttype': 'many2one',
                                    'relation': model.model,
                                    'field_description': f"Inverse field for {field_name}"
                                })

                            field_data['relation_field'] = inverse_field_name

                        request.env['ir.model.fields'].sudo().create(field_data)
                elif field_type in ['selection']:
                    sequence = 0
                    selection_field = request.env['ir.model.fields'].sudo().create({
                        'model_id': model.id,
                        'name': field_name,
                        'ttype': field_type,
                        'field_description': field_description,
                    })

                    for key, value in field.get('options').items():
                        request.env['ir.model.fields.selection'].sudo().create({
                            'field_id': selection_field.id,
                            'value': key,
                            'name': value,
                            'sequence': sequence,
                        })
                        sequence += 1
                else:
                    # if not field_exists:
                    request.env['ir.model.fields'].sudo().create({
                        'model_id': model.id,
                        'name': field_name,
                        'ttype': field_type,
                        'field_description': field_description,
                    })
            fields_xml = "".join([
                f'<field name="x_cyllo_{field["field_name"]}" string="{field.get("string")}"/>'
                for field in fields
            ])
            # Form view
            form_view = request.env['ir.ui.view'].sudo().create({
                'name': f"{model.model}_form_view",
                'type': 'form',
                'model': model.model,
                'arch_base': f"""
                        <form>
                            <sheet>
                                <group>
                                    {fields_xml}
                                </group>
                            </sheet>
                        </form>
                    """,
            })
            # Tree view
            tree_view = request.env['ir.ui.view'].sudo().create({
                'name': f"{model.model}_tree_view",
                'type': 'tree',
                'model': model.model,
                'arch_base': f"""
                        <tree>
                            {fields_xml}
                        </tree>
                    """,
            })
            # View action
            model_action = request.env['ir.actions.act_window'].sudo().create({
                'name': f"{to_camel_case(model_name)}",
                'res_model': model.model,
                'view_mode': 'tree,form',
                'view_ids': [
                    Command.create(
                        {'view_id': tree_view.id, 'view_mode': 'tree'}),
                    Command.create(
                        {'view_id': form_view.id, 'view_mode': 'form'}),
                ],
                'target': 'current',
            })
            model_menu_name = to_camel_case(model_name)
            request.env['ir.ui.menu'].sudo().create({
                'name': model_menu_name,
                'parent_id': main_menu.id,
                'action': f"{model_action.type},{model_action.id}",
            })
            user_group = request.env.ref('base.group_user')
            if user_group:
                request.env['ir.model.access'].sudo().create({
                    'name': f"{user_group.name}_access_{model.model}",
                    'model_id': model.id,
                    'group_id': user_group.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                })
        action_id = model_action.id if model_action else ''  # Use the action created earlier for the model
        list_view_url = f"/web?studio=1#action={action_id}&model={model.model}&view_type=list&menu_id={main_menu.id}"
        return {
            "redirect_url": list_view_url,
            "AppMenu": main_menu.id,
            "AppName": main_menu_name,
        }
