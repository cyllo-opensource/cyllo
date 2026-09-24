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
import inspect
import uuid
from html import unescape, escape
import xml.etree.ElementTree as ET
from odoo import http, api, _, tools
import json
import ast
from odoo.exceptions import ValidationError, AccessError,UserError
from odoo.http import Controller, route, request, _logger
from odoo import Command
from lxml import etree
import re
from odoo.tools import ustr

random_uuid = uuid.uuid4()


class StudioMode(Controller):
    """
    A controller for Odoo Studio mode, handling various view and model modifications.
    """

    def create_invisible(self, args):
        """
        Generates XML to make fields invisible in a view based on conditions.

        Args:
            args (list): A list containing a dictionary with view and field information.

        returns:
            str: An XML string for adding invisible fields to the view.
        """

        model = args[0]['model']
        view_type = args[0].get('viewType') or args[0].get('view_type')

        # Get fields that are actually in the current view's XML
        view_id = args[0].get('view_id')
        actual_fields_in_view = []

        if view_id:
            view_rec = request.env['ir.ui.view'].browse(view_id)
            view_arch = etree.fromstring(view_rec.arch_base)
            actual_fields_in_view = [field.get('name') for field in view_arch.xpath('//field[@name]')]

        # Get all fields from the model
        all_model_fields = request.env['ir.model.fields'].search(
            [('model', '=', model)]).mapped('name')

        attrs = args[0].get('attrs', {})
        value = args[0].get('value', {})
        invisible_direct = args[0].get('invisible', False)

        conditions = {
            'invisible': invisible_direct or attrs.get('invisible', False) or value.get('invisible', False),
            'readonly': attrs.get('readonly', False) or value.get('readonly', False),
            'required': attrs.get('required', False) or value.get('required', False),
        }

        # Extract field names from conditions
        pattern1 = r'\b(\w+)\b(?=\s*(?:in|not in|==|!=|=|<|>|<=|>=))'
        pattern2 = r'set\((.*?)\)\.intersection'
        pattern3 = r'\bnot\s+(\w+)\b'  # Match 'not field_name'

        left_hand_names = []
        for condition in conditions.values():
            if isinstance(condition, str) and condition:
                matches1 = re.findall(pattern1, condition)
                matches2 = re.findall(pattern2, condition)
                matches3 = re.findall(pattern3, condition)
                left_hand_names.extend([*matches1, *matches2, *matches3])

        # Handle dynamic_placeholder
        dynamic_placeholder = attrs.get('dynamic_placeholder') or value.get('dynamic_placeholder')
        if dynamic_placeholder and isinstance(dynamic_placeholder, str):
            left_hand_names.append(dynamic_placeholder)

        # Remove 'not' and duplicates
        left_hand_names = [name for name in left_hand_names if name != 'not']
        left_hand_names = list(set(left_hand_names))

        # Find fields that need to be added invisibly
        keys_not_present = [
            key for key in left_hand_names
            if key in all_model_fields and key not in actual_fields_in_view
        ]

        fields_to_include = ''
        if keys_not_present:
            view_type = args[0].get('viewType') or args[0].get('view_type')
            if view_type in ['tree', 'kanban']:
                xpath_expr = "kanban" if view_type == "kanban" else args[0].get("path", "tree")
                fields_to_include += f'<xpath expr="/{xpath_expr}" position="inside">'

                if view_type == "tree":
                    fields_to_include += ''.join(
                        f'<field name="{field}" invisible="1" column_invisible="1"/>'
                        for field in keys_not_present
                    )
                else:  # kanban
                    fields_to_include += ''.join(
                        f'<field name="{field}" invisible="1"/>'
                        for field in keys_not_present
                    )
                fields_to_include += '</xpath>'
            else:  # form and other views
                fields_to_include = ''.join(
                    f'<field name="{field}" invisible="1"/>' for field in keys_not_present
                )
        return fields_to_include

    def create_header(self, header_path):
        """
                Generates an XML snippet for a header element.

                Args:
                    header_path (str): The XPath for the header's position.

                Returns:
                    str: An XML string for the header element.
                """
        if not header_path:
            return ''
        path = header_path
        position = 'before'

        if path == "/form/":
            path = "/form"
            position = "inside"
        header_arch = f'<xpath expr="/{path}" position="{position}"><header/></xpath> '
        return header_arch

    @http.route('/web/webclient/cyllo_load_menus/<string:unique>', type='http', auth='user', methods=['GET'])
    def web_cyllo_load_menus(self, unique=None, lang=None):
        """
        //Removed the reload and odoo.loadparams for not taking cached menu and getting newly created menu from studio

        Loads the menus for the webclient
        :param unique: this parameters is not used, but mandatory: it is used by the HTTP stack to make a unique request
        :param lang: language in which the menus should be loaded (only works if language is installed)
        :return: the menus (including the images in Base64)
        """
        self.is_studio_user()
        if lang:
            request.update_context(lang=lang)
        menus = request.env["ir.ui.menu"].load_web_menus(request.session.debug)
        body = json.dumps(menus, default=ustr)
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            # ('Cache-Control', 'public, max-age=' + str(http.STATIC_CACHE_LONG)), # INTENTIONAL: Removed this to get the newly created menus via calling load_menus from the load_web_menus
        ])
        return response

    @route('/cyllo_studio/create/list/view', auth="user", csrf=False,
           type='json')
    def create_list_view(self, args, kwargs=None):
        """
        creates a new list view for a given model.
        Args:
            args (list): A list containing a dictionary with model information.
            kwargs (dict, optional): Additional keyword arguments. Defaults to None.

         Returns:
            dict: A dictionary containing the ID, model, type, and name of the newly created view.
        """
        self.is_studio_user()
        view_arch = """<tree>
           <field name="id"/>
       </tree>"""
        new_view = request.env['ir.ui.view'].sudo().create({
            'name': '_'.join(args[0]['relationModel'][0]['name'].lower().split(' ')) + '_tree', 'type': 'tree',
            'model': args[0]['relationModel'][0]['model'],
            'model_id': args[0]['relationModel'][0]['id'],
            'arch': view_arch,
        })
        return {'id': new_view.id, 'model': new_view.model, 'type': new_view.type, 'name': new_view.name}

    def is_studio_user(self):
        """
        Checks if the current user is a studio user and has the necessary access rights.
        """
        studio = request.session.get('studio')
        is_studio_debug = bool(studio) and '1' in studio
        is_studio_user = request.env.user.has_group('cyllo_studio.group_cyllo_studio_user')
        if is_studio_user and not is_studio_debug:
            request.session.studio = '1'
        if not is_studio_user:
            raise AccessError(_("You don't have the access to this request."))

    def is_studio_admin(self):
        self.is_studio_user()
        if not (request.env.user.has_group('cyllo_studio.group_cyllo_studio_admin') or request.env.user.has_group('cyllo_studio.group_cyllo_studio_user')):
            raise AccessError(_("You need administrator access to make this structural change."))
    def get_studio_view(self, view_id, model, view_type):
        """
                Retrieves or creates an Odoo Studio view for a given model and view type.

                If a Studio view already exists inheriting the specified view_id, it returns that view.
                Otherwise, it creates a new Studio view with a unique name and inherits the base view.

                Args:
                    view_id (int): The ID of the base view to inherit.
                    model (str): The name of the model.
                    view_type (str): The type of the view (e.g., 'form', 'tree', 'kanban').

                Returns:
                    odoo.models.Model: The Studio view record.
                """
        self.is_studio_user()
        view_rec = request.env['ir.ui.view'].sudo().search([('inherit_id', '=', view_id)],
                                                           order='priority desc, id desc',
                                                           limit='1')
        base_view = request.env['ir.ui.view'].sudo().browse(view_id)
        actual_model = base_view.model or model
        actual_view_type = base_view.type if base_view else view_type
        if not view_rec.is_studio:
            priority = view_rec.priority + 1 if len(view_rec) == 1 else 16
            view_rec = view_rec.sudo().create(
                {'name': f"Cyllo Studio {actual_model} {actual_view_type} view",
                 'type': actual_view_type,
                 'model': actual_model,
                 'mode': 'extension',
                 'inherit_id': view_id,
                 'arch_base': '<data></data>',
                 'active': True,
                 'priority': priority,
                 'is_studio': True})
            request.env['ir.model.data']._update_xmlids([{
                'xml_id': f"cy_studio.{actual_model.replace('.', '_')}_{actual_view_type}_view_{str(uuid.uuid4())[:8]}",
                'record': view_rec,
            }])
        elif actual_model and view_rec.model != actual_model:
            view_rec.sudo().write({'model': actual_model})
        return view_rec

    def check_arch_path(self, view_id, path):
        """
        Refuse a path that does not identify exactly one node of ``view_id``.

        Studio writes ``<xpath expr="/{path}" …/>``, so a path of ``/tree``
        becomes ``//tree`` — a *descendant* search that silently matches whatever
        it finds first instead of failing. The x2many list renderer emits
        subview-relative paths rooted at ``/tree``
        (views/cyllo_list/cyllo_list_renderer.js), and those mean nothing in the
        parent form's arch: ``//tree`` matched the order lines' inline ``<tree>``
        and a ``position="replace"`` wiped the whole list, leaving the x2many with
        a ``<label>`` root. That fails server validation against the line model
        ("action_confirm is not a valid action on sale.order.line") or, once
        written, crashes the client with
        "KeyNotFoundError: Cannot find label in this registry!".

        cy-xpath values are absolute paths from ``lxml.getpath()`` (see
        models/ir_ui_view.py), so they are resolved as absolute here: a path that
        does not belong to this view simply does not match, and we stop before
        destroying anything.

        :raise ValidationError: when the path matches zero or several nodes.
        """
        if not path:
            return
        base_view = request.env['ir.ui.view'].sudo().browse(view_id)
        if not base_view:
            return
        try:
            nodes = base_view._get_combined_arch().xpath('/%s' % path.lstrip('/'))
        except Exception:
            # A malformed path is not something to guess about either.
            nodes = []
        if len(nodes) != 1:
            raise ValidationError(_(
                "This change cannot be applied: '%(path)s' does not point at a "
                "single element of this view (%(count)s matches). That usually "
                "means the element belongs to an embedded list or form, whose "
                "paths are not valid in the parent view — open that sub-view in "
                "Studio and make the change there.",
                path=path, count=len(nodes),
            ))

    def create_view(self, data, ttype, arch):
        """
        Creates a new view record in the database.

        Args:
             data (dict): A dictionary containing view-related data, such as 'name' and 'resModel'.
             type (str): The type of the view (e.g., 'form', 'tree').
             arch (str): The XML architecture of the view.

        Returns:
            odoo.models.Model: The newly created view record.
        """
        view_data = request.env['ir.ui.view'].sudo().create({
            'name': f"view_{data['name']}_{ttype}_{str(uuid.uuid4())[:8]}",
            'type': ttype,
            'model': data['resModel'],
            'model_id': request.env['ir.model']._get_id(data['resModel']),
            'arch': arch
        })
        return view_data

    def get_default_view_arch(self, view_type, data):
        """
        Generates the default architecture for a specified view type.

        This method returns a template XML structure based on the specified view type,
        which can be used as a default for creating new views.

        Args:
            view_type (str): The type of view to generate (e.g., 'calendar', 'kanban', 'form').
            data (dict): A dictionary containing data relevant to the view, such as field names.

        Returns:
            str: An XML string representing the default architecture for the specified view type.
        """

        arch = ""
        if view_type == "calendar":
            arch = f"""<calendar date_start="{data['startDateField']}" date_stop="{data['stopDateField']}">
                           <field name="{data['startDateField']}"/>
                       </calendar>"""
        elif view_type == "kanban":
            arch = """<kanban>
                        <field name="display_name" />
                        <templates>
                            <t t-name="kanban-box">
                                <div class="oe_kanban_global_click">
                                    <div class="oe_kanban_details">
                                        <field name="display_name" />
                                    </div>
                                </div>
                            </t>
                        </templates>
                    </kanban>"""
        elif view_type == "form":
            arch = """<form>
                        <header />
                        <sheet>
                            <div class="oe_title">
                                <h1>
                                    <field name="x_name" required="1" placeholder="Name..." />
                                </h1>
                            </div>
                            <group />
                        </sheet>
                    </form>"""
        elif view_type == "pivot":
            arch = """<pivot>
                        <field name="display_name"/>
                    </pivot>"""

        elif view_type == "graph":
            arch = """<graph>
                        <field name="display_name"/>
                    </graph>"""
        elif view_type == "activity":
            arch = f"""<activity string='{data['resModel']} Activity View'>
                        <field name="display_name" />
                        <templates>
                             <div t-name="activity-box">
                                <field name="display_name"/>
                             </div>
                        </templates>
                    </activity>"""
        elif view_type == "tree":
            arch = """<tree>
                       <field name="x_name"/>
                   </tree>"""
        return arch

    def ensure_unique_relation_table(self, field):
        """
        Ensures that the relation_table for a many2many field is unique.
        If the relation_table already exists, appends an integer to make it unique.

        :param field: The field object to check and update.
        :return: None (updates the field.relation_table in place).
        """
        if field.ttype == 'many2many':
            base_relation_table = field.relation_table
            relation_tables = request.env['ir.model.fields'].search([
                ('ttype', '=', 'many2many'),
                ('relation_table', '=', base_relation_table)
            ])

            if len(relation_tables) > 1:
                counter = 1
                new_relation_table = f"{base_relation_table}_{counter}"

                # Check if the new_relation_table already exists
                while request.env['ir.model.fields'].search_count([
                    ('ttype', '=', 'many2many'),
                    ('relation_table', '=', new_relation_table)
                ]) > 0:
                    counter += 1
                    new_relation_table = f"{base_relation_table}_{counter}"

                # Update the relation_table with the new unique name
                field.relation_table = new_relation_table

    def get_currency_field(self, model_id, field_name):
        """
        Gets the currency field name associated with a monetary field.

        Args:
            model_id (int): The ID of the model.
            field_name (str): The name of the monetary field.

        Returns:
            str or None: The name of the currency field, or None if not found.
        """

        ir_model = request.env["ir.model"].browse(model_id)
        res_model = request.env[ir_model.model]
        if field_name not in res_model._fields:
            return None
        currency_field_name = res_model._fields[field_name].get_currency_field(res_model)
        return currency_field_name

    def set_app_sequence(self, module_id, position):
        """
        Sets the sequence for a new app menu item.

        Args:
            module_id (int): The ID of the module (app menu).
            position (str): The position for the new app ('After' or 'Before').

        Returns:
            int: The calculated sequence number.
        """
        sequence = 10
        if module_id:
            apps = request.env['ir.ui.menu'].search([('parent_id', '=', False)])
            update_sequence = False

            for i, app in enumerate(apps):
                if update_sequence:
                    app.sequence += 2
                    continue

                if app.id == module_id:
                    if position == 'After':
                        next_app_sequence = apps[i + 1].sequence if i + 1 < len(apps) else None
                        if next_app_sequence is None or (app.sequence + 1) < next_app_sequence:
                            sequence = app.sequence + 1
                            break
                        update_sequence = True
                    else:
                        prev_app_sequence = apps[i - 1].sequence if i - 1 >= 0 else None
                        if prev_app_sequence is None or (app.sequence - 1) > prev_app_sequence:
                            sequence = app.sequence - 1
                            break
                        app.sequence += 2
                        update_sequence = True
        return sequence

    def get_last_element_from_path(self, xpath_string):
        """
        Extracts the last element name from an XPath string.

        Args:
            xpath_string (str): The XPath string.

        Returns:
            str: The name of the last element.
        """
        return re.sub(r'\[\d+\]', '', xpath_string.strip('/').split('/')[-1])

    def get_default_view_template(self, view_type, editable=False):
        """
        Generates a default view template in XML format.

        Args:
            view_type (str): The type of the view (kanban, form, or tree).
            editable (bool, optional): Whether the view should be editable. Defaults to False.

        Returns:
            str: An XML string representing the view template.
        """
        if view_type == 'kanban':
            return """<kanban>
                                <field name="x_name"/>
                               <templates>
                                   <t t-name="kanban-box">
                                       <div class="oe_kanban_global_click">
                                           <div class="oe_kanban_details">
                                               <field name="x_name"/>
                                           </div>
                                       </div>
                                   </t>
                               </templates>
                       </kanban>"""
        elif view_type == 'form':
            return """ <form>
                            <header/>
                            <sheet> 
                                <div class="oe_title">
                                    <h1><field name="x_name" required="1" placeholder="Name..."/></h1> 
                                </div> 
                                <group/> 
                            </sheet> 
                        </form>"""
        elif view_type == 'tree':
            tree = "<tree"
            if editable:
                tree += ' editable="top"'
            tree += """>
                        <field name="x_name"/>
                    </tree>"""
            return tree

    @route('/cyllo_studio/find/functions', type="json", auth="user",
           csrf=False)
    def find_functions(self, model_name, check_unusual_days=False):
        """
        Finds and returns action methods on a given model.

        This method inspects the model's class to find custom methods that start with
        'action' or 'button' and have a signature with only one parameter (self).
        It can also be used to specifically check for the existence of 'get_unusual_days'.

        Args:
            model_name (str): The name of the model to inspect.
            check_unusual_days (bool, optional): If True, the method returns True if 'get_unusual_days' exists and False otherwise. Defaults to False.

        Returns:
            list or bool: A list of method names, or a boolean if `check_unusual_days` is True.
        """
        self.is_studio_user()
        model = request.env[model_name]
        model_class = type(model)

        is_custom_extended = lambda cls: not cls.__module__.startswith("odoo.api")
        custom_extended_classes = [cls for cls in getattr(model_class, '_BaseModel__base_classes', []) if
                                   is_custom_extended(cls)]

        classes = [cls.__name__ for cls in custom_extended_classes]

        active_include = request.env['ir.model.fields'].search(
            [('model', '=', model_name), '|', ('name', '=', 'active'), ('name', '=', 'x_active')])

        methods = []

        for attr_name in dir(model_class):
            attr = getattr(model_class, attr_name)

            if (inspect.isfunction(attr) or inspect.ismethod(attr)) and not getattr(attr, '__self__', None):

                if any(name in str(attr.__qualname__) for name in classes) or 'BaseModel' in str(attr.__qualname__):
                    if check_unusual_days and attr_name == 'get_unusual_days':
                        return True  # Return True immediately if we are checking for 'get_unusual_days'

                    signature = inspect.signature(attr)
                    parameters = signature.parameters

                    if len(parameters) == 1 and (attr_name.startswith("action") or attr_name.startswith("button")):
                        methods.append(attr_name)

        if not active_include:
            methods = [method for method in methods if method not in {'action_archive', 'action_unarchive'}]

        return False if check_unusual_days else methods

    @route('/cyllo_studio/view/active_views', type="json", auth="user",
           csrf=False)
    def active_views(self, args):
        """
        Handles the activation and deactivation of views based on the input arguments.

        This method processes a request to activate or deactivate views within an action window.
        It checks the current state of the specified view type and modifies the view accordingly.

        Args:
            args (list): A list containing a single dictionary with the following keys:
                - 'viewType' (str): The type of the view (e.g., 'list', 'form').
                - 'actionId' (int): The ID of the action window.
                - 'activeView' (bool): Whether to activate or deactivate the view.
                - 'resModel' (str, optional): The model name.

        Returns:
            None
        """
        self.is_studio_user()
        data, = args
        view_type = 'tree' if data['viewType'] == 'list' else data['viewType']
        act_window_id = request.env['ir.actions.act_window'].browse(data['actionId'])
        active_view_id = act_window_id.view_ids.search(
            [('act_window_id', '=', act_window_id.id), ('view_mode', '=', view_type),
             ('active', 'in', [True, False])],
            limit=1)
        res_model = data.get("resModel", "")
        if data.get("activeView"):
            if active_view_id:
                active_view_id.active = True
            else:
                view_id = False
                if res_model.startswith("x_") or view_type in ['calendar']:
                    arch = self.get_default_view_arch(view_type, data)
                    view_id = self.create_view(data, view_type, arch).id
                act_window_id.view_ids = [Command.create({
                    'view_mode': view_type,
                    'sequence': len(act_window_id.view_ids),
                    'view_id': view_id,
                    'active': True
                })]
        else:
            if active_view_id:
                active_view_id.write({
                    'active': False,
                    'sequence': len(act_window_id.view_ids) + 1
                })
            view_mode = act_window_id.view_mode.split(",")
            if view_type in view_mode:
                view_mode.remove(view_type)
            elif view_type == 'tree' and 'list' in view_mode:
                view_mode.remove("list")
            if not view_mode and act_window_id.view_ids:
                view = act_window_id.view_ids[0]
                view_mode.append(view.view_mode)

            act_window_id.view_mode = ",".join(view_mode)

    @route('/cyllo_studio/view/active_views/set_default_view', type="json", auth="user",
           csrf=False)
    def set_default_view(self, args):
        """
        Sets the specified view type as the default for an action window.

        This method updates the view sequence in an action window, placing the specified view type as the first view,
        and activates it if necessary. It also adjusts the sequence of other views to maintain order.

        Args:
            args (list): A list containing a single dictionary with the following keys:
                - 'siblingType' (str): The type of the view to set as default (e.g., 'list', 'form').
                - 'actionId' (int): The ID of the action window.

        Returns:
            None
        """
        self.is_studio_user()
        data, = args
        view_type = 'tree' if data['siblingType'] == 'list' else data['siblingType']
        act_window_id = request.env['ir.actions.act_window'].browse(data['actionId'])
        if act_window_id:
            view_mode = act_window_id.view_mode.split(",")
            if view_type in view_mode:
                view_mode.remove(view_type)
            active_view_ids = act_window_id.view_ids.search(
                [('act_window_id', '=', act_window_id.id), ('view_mode', '=', view_type),
                 ('active', 'in', [True, False])],
                limit=1)
            if active_view_ids:
                active_view_ids.write({
                    'active': True,
                    'sequence': 0
                })
            else:
                act_window_id.view_ids = [Command.create({
                    'view_mode': view_type,
                    'sequence': 0,
                })]
            seq = 1
            for rec in act_window_id.view_ids.filtered(lambda record: record.view_mode != view_type):
                rec.sequence = seq
                seq += 1
            if not view_mode and act_window_id.view_ids:
                view_mode.append(act_window_id.view_ids[0].view_mode)
            act_window_id.view_mode = ",".join(view_mode)

    @route('/cyllo_studio/find/invisible', type="json", auth="user",
           csrf=False)
    def find_invisible_fields(self, args, kwargs):
        """
        Sets a session variable to indicate whether fields should be invisible.

        Args:
            args (list): A list containing a dictionary with an 'invisible' key.
            kwargs (dict): Additional keyword arguments.
        """
        self.is_studio_user()
        if args[0].get('invisible') is True:
            request.session['invisible'] = 'True'
        else:
            request.session['invisible'] = 'False'

    @route('/cyllo_studio/edit/overall_view', type="json", auth="user", csrf=False)
    def edit_overallView(self, args, kwargs):
        """
        Edits the overall view by adding or updating attributes on the root node.

        Args:
            args (list): A list containing a dictionary with view information.
            kwargs (dict): A dictionary with attribute, path, value, and order information.

        Returns:
            str: An XML string representing the changes made.
        """
        self.is_studio_user()
        model = args[0].get('model')
        view_type = args[0].get('view_type')
        view_id = args[0].get('view_id')

        form_arch_base = ' '
        if kwargs['attr']:
            if kwargs['attr'] == 'default_order':
                form_arch_base = f'''<xpath expr="/{kwargs['path']}" position="attributes">
                                              <attribute name="{kwargs['attr']}">{kwargs['value']} {kwargs['order']}</attribute>
                                            </xpath>    '''
            elif kwargs['attr'] == 'quick_create_view_id':
                form_arch_base = f'''
                    <xpath expr="/{kwargs['path']}" position="attributes">
                            <attribute name='quick_create'>true</attribute>
                            <attribute name="{kwargs['attr']}">{kwargs['value']}</attribute>
                    </xpath>
                '''
            else:
                form_arch_base = f'''<xpath expr="/{kwargs['path']}" position="attributes">
                                      <attribute name="{kwargs['attr']}">{kwargs['value']}</attribute>
                                    </xpath>    '''

        if form_arch_base:
            view_rec = self.get_studio_view(view_id, model, view_type)
            view_node = etree.fromstring(view_rec.arch_base)
            view_node.append(etree.fromstring(form_arch_base))
            view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
            return form_arch_base

    @route('/cyllo_studio/pivot/edit_element', type="json", auth="user",
           csrf=False)
    def edit_pivot_element(self, kwargs):
        """
        Adds or modifies an element in a pivot view.

        Args:
            kwargs (dict): A dictionary containing the view ID, model, view type, and element details.

        Returns:
            str: The XML string representing the added/modified element.
        """
        self.is_studio_user()

        # Validate that measure fields are numeric types only (prevents "No aggregate function" crash)
        if kwargs.get('position') == 'inside' and kwargs.get('item_type') == 'measure':
            field_name = kwargs.get('name', '')
            model_name = kwargs.get('model', '')
            if field_name and model_name:
                try:
                    ir_model = request.env['ir.model'].search([('model', '=', model_name)], limit=1)
                    field_rec = request.env['ir.model.fields'].search([
                        ('model_id', '=', ir_model.id),
                        ('name', '=', field_name),
                    ], limit=1)
                    allowed_types = ('integer', 'float', 'monetary')
                    if field_rec and field_rec.ttype not in allowed_types:
                        return False
                except Exception:
                    pass  # If validation fails, let it through gracefully

        pivot_arch_base = f'''<xpath expr="//pivot" position="{kwargs['position']}">'''
        if kwargs['position'] == 'inside':
            pivot_arch_base += f'''<field name="{kwargs['name']}" type="{kwargs['item_type']}"  '''
            if kwargs['interval']:
                pivot_arch_base += f'''interval="{kwargs['interval']}"'''
            pivot_arch_base += '/></xpath>'
        else:
            pivot_arch_base += f'''<attribute name="{kwargs['name']}">{kwargs['item_type']}</attribute></xpath>'''
        view_rec = self.get_studio_view(kwargs['viewId'], kwargs['model'], kwargs['view_type'])
        pivot_node = etree.fromstring(view_rec.arch_base)
        pivot_node.append(etree.fromstring(pivot_arch_base))
        view_rec.arch_base = etree.tostring(pivot_node, pretty_print=True,
                                            encoding='unicode')
        return pivot_arch_base

    @route('/cyllo_studio/add/existing_field', type="json", auth="user",
           csrf=False)
    def add_existing_field(self, args, kwargs):
        """
        Adds one or more existing fields to a view.

        Args:
            args (list): A list containing a dictionary with view and field information.
            kwargs (dict): A dictionary containing the field names to add.

        Returns:
            str: An XML string representing the added fields.
        """
        self.is_studio_user()
        model = args[0].get('model')
        view_type = args[0].get('view_type')
        view_id = args[0].get('view_id')

        arch_base = f'''<xpath expr="/{args[0].get('path')}" position="{args[0].get('position')}">'''
        if kwargs.get('value'):
            for value in kwargs.get('value'):
                arch_base += f'''<field name="{value}"/>'''
        arch_base += '</xpath>'
        if arch_base:
            view_rec = self.get_studio_view(view_id, model, view_type)
            view_node = etree.fromstring(view_rec.arch_base)
            view_node.append(etree.fromstring(arch_base))
            view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
            return arch_base

    @http.route('/cyllo_studio/get_non_abstract_non_transient_models', type='json', auth='user')
    def get_non_abstract_non_transient_models(self):
        """
        Retrieves a list of all non-abstract and non-transient models.

        Returns:
            list: A list of dictionaries, where each dictionary contains the 'id', 'model', and 'name' of a model.
        """
        self.is_studio_user()
        Model = request.env['ir.model']
        non_abstract_non_transient_models = []

        for model in Model.search([('transient', '=', False)]):
            try:
                # Check if the model exists in the environment and get its class safely
                model_env = http.request.env.get(model.model)
                is_abstract = model_env._abstract or not model_env._auto
                # Ensure the model class exists and isn't abstract or transient
                if not is_abstract:
                    non_abstract_non_transient_models.append({
                        'id': model.id,
                        'model': model.model,
                        'name': model.name
                    })
            except Exception as e:
                request.env.cr.rollback()  # Avoid transaction issues
                continue
        return non_abstract_non_transient_models

    # --------------------------Kanban View functionality ----------------------------------------------------

    @route('/cyllo_studio/kanban/add/field', type="json", auth="user",
           csrf=False)
    def add_kanban_field(self, view_id, view_type, model, path, position, field, x2many):
        """
        Adds a new field to a kanban view.

        Args:
            view_id (int): The ID of the kanban view.
            view_type (str): The type of the view ('kanban').
            model (str): The name of the model.
            path (str): The XPath to the target element.
            position (str): The position for the new field ('inside', 'after', 'before').
            field (str): The name of the field to add.
            x2many (str): The XPath for the many-to-many relationship.

        Returns:
            str: A combined XML string representing the added field.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        # view_arch_1 = f'''
        #                      <xpath expr="{x2many}" position="inside">
        #                           <field name="{field}"/>
        #                      </xpath>'''
        view_arch_2 = f'''
                             <xpath expr="/{path}" position="{position}">
                                 <field name="{field}"/>
                             </xpath>'''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch_2))
        combined_arch = view_arch_2
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return combined_arch

    @route('/cyllo_studio/kanban/add/text', type="json", auth="user",
           csrf=False)
    def add_kanban_text(self, viewId, viewType, model, path, position,
                        properties):
        """
        Adds a new text element (span) to a kanban view.

        Args:
            viewId (int): The ID of the kanban view.
            viewType (str): The type of the view ('kanban').
            model (str): The name of the model.
            path (str): The XPath to the target element.
            position (str): The position for the new text element.
            properties (dict): A dictionary of properties for the text element.

        Returns:
            str: An XML string representing the added text element.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(viewId, model, viewType)

        # Check if the 'invisible' property is set to a non-false value.
        is_invisible = properties.get('invisible') and properties[
            'invisible'] != 'false'
        invisible_attr = f'invisible="{properties["invisible"]}"' if is_invisible else ''
        if properties.get('sibling'):
            if properties.get('item_type') == "normal":
                existing_field_name = properties['field_info']['name']
                element_arch = f"""
                    <xpath expr="/{path}" position="replace">
                        <label for="{existing_field_name}"/>
                        <div class="o_row">
                            <field name="{existing_field_name}"/>
                            <span class="{properties['class_names']}" {invisible_attr}>{escape(properties['string'])}</span>
                        </div>
                    </xpath>
                """
            else:
                element_arch = f"""
                    <xpath expr="/{path}" position="inside">
                        <span class="{properties['class_names']}" {invisible_attr}>{escape(properties['string'])}</span>
                    </xpath>
                """
        else:
            element_arch = f"""
                <xpath expr="/{path}" position="{position}">
                    <span class="{properties['class_names']}" {invisible_attr}>{escape(properties['string'])}</span>
                </xpath>
            """

        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(element_arch))
        view_rec.arch_base = etree.tostring(view_node, pretty_print=True,
                                            encoding='unicode')
        return element_arch

    @route('/cyllo_studio/kanban/update/text', type="json", auth="user",
           csrf=False)
    def update_kanban_text(self, view_id, view_type, model, path, properties):
        """
        Updates an existing text element in a kanban view.

        Args:
            view_id (int): The ID of the kanban view.
            view_type (str): The type of the view ('kanban').
            model (str): The name of the model.
            path (str): The XPath to the text element to be updated.
            properties (dict): A dictionary of new properties for the text element.

        Returns:
            str: An XML string representing the updated text element.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = f'''
                                   <xpath expr="/{path}" position="replace">
                                          <span class="{properties['class_names']}">{escape(properties['string'])}</span>
                                   </xpath>
                               '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    @route('/cyllo_studio/kanban/add/ribbon', type="json", auth="user",
           csrf=False)
    def add_kanban_ribbon(self, viewId, viewType, model, path, position, properties, active_fields=None):
        """
        Adds a new ribbon element to a kanban view.

        Args:
            viewId (int): The ID of the kanban view.
            viewType (str): The type of the view ('kanban').
            model (str): The name of the model.
            path (str): The XPath to the target element.
            position (str): The position for the new ribbon.
            properties (dict): A dictionary of properties for the ribbon.

        Returns:
            str: An XML string representing the added ribbon.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(viewId, model, viewType)

        view_arch = f'''
                           <xpath expr="/{path}" position="{position}">
                               <div class="ribbon ribbon-top-right" invisible='{properties['invisible']}' style="position: absolute !important; top: 0 !important; right: 0 !important; z-index: 5 !important; margin: 0 !important; pointer-events: auto !important; cursor: pointer !important;">
                                  <span class="{properties['color']}" style="pointer-events: auto !important; cursor: pointer !important;">{escape(properties['string'])}</span>
                               </div>
                           </xpath>
                       '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        not_present_field = self.create_invisible([{
            'invisible': properties['invisible'],
            'active_fields': active_fields or {},
            'model': model,
            'viewType': viewType,
            'path': path,
            'position': position
        }])
        if not_present_field:
            view_node.append(etree.fromstring(not_present_field))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    def extract_index(self, path):
        if '[' in path and ']' in path:
            try:
                return int(path.split('[')[-1].split(']')[0])
            except:
                return 0
        return 0

    @route('/cyllo_studio/kanban/update/ribbons', type="json", auth="user", csrf=False)
    def update_kanban_ribbons(self, **kwargs):
        """
        Updates existing ribbon elements in a kanban view.

        Args:
            **kwargs: Keyword arguments containing view information and ribbon data.
                - viewId (int): The ID of the kanban view.
                - viewType (str): The type of the view ('kanban').
                - model (str): The name of the model.
                - ribbons (list): A list of dictionaries, where each dictionary represents a ribbon.

        Returns:
            None
        """
        self.is_studio_user()
        view_id = kwargs.get("viewId")
        view_type = kwargs.get("viewType")
        model = kwargs.get("model")
        ribbons = kwargs.get("ribbons")
        active_fields = kwargs.get("active_fields")
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_node = etree.fromstring(view_rec.arch_base)
        # Separate ribbons into deleted and edited ribbons
        deleted_ribbons = [r for r in ribbons if r.get("hasDelete")]
        edited_ribbons = [r for r in ribbons if not r.get("hasDelete") and r.get("hasEdit")]
        # Loop through the edited ribbons and modify the view
        for ribbon in edited_ribbons:

            # view_arch = f'''
            #                     <xpath expr="/{ribbon['path']}" position="replace">
            #                         <div class="ribbon ribbon-top-right" invisible='{escape(ribbon['invisible'])}'>
            #                             <span class="{ribbon['color']}">{escape(ribbon['firstElementContent'])}</span>
            #                         </div>
            #                     </xpath>
            #                 '''
            view_arch = f'''
                                <xpath expr="/{ribbon['path']}" position="replace">
                                    <div class="ribbon ribbon-top-right"
                                         invisible='{escape(ribbon['invisible'])}'
                                         style="position: absolute !important; top: 0 !important; right: 0 !important; z-index: 5 !important; margin: 0 !important; pointer-events: auto !important; cursor: pointer !important;">
                                        <span class="{ribbon['color']}" style="pointer-events: auto !important; cursor: pointer !important;">{escape(ribbon['firstElementContent'])}</span>
                                    </div>
                                </xpath>
                            '''
            view_node.append(etree.fromstring(view_arch))
            not_present_field = self.create_invisible(
                [{'invisible': ribbon['invisible'], 'active_fields': active_fields, 'model': model, }])
            not_present_field1 = ''
            not_present_field2 = ''
            if not_present_field:
                not_present_field1 = f'''<xpath expr="/kanban" position="inside">
                                                          {not_present_field}
                                                     </xpath>'''
                not_present_field2 = f''' <xpath expr="{ribbon['path']}" position="after">{not_present_field}</xpath>'''
                view_node.append(etree.fromstring(not_present_field1))
                view_node.append(etree.fromstring(not_present_field2))
        # Loop through the deleted ribbons and modify the view
        deleted_ribbons = sorted(
            deleted_ribbons,
            key=lambda ribbon: int(''.join([character for character in ribbon['path'] if character.isdigit()]) or 0),
            reverse=True
        )
        for ribbon in deleted_ribbons:
            view_arch = f'''
                                <xpath expr="/{ribbon['path']}" position="replace"/>
                            '''
            view_node.append(etree.fromstring(view_arch))

        # Update the arch_base attribute with the modified XML
        view_rec.arch_base = etree.tostring(view_node, pretty_print=True, encoding='unicode')

        # Return the updated view base, not view_arch, since view_arch is overwritten in each loop
        return view_rec.arch_base

    @route('/cyllo_studio/kanban/update/field', type="json", auth="user", csrf=False)
    def update_kanban_field(self, args):
        """
          Update an existing Kanban field's attributes (widget, invisibility)
          and optionally add invisible placeholder fields if they do not exist.

          Parameters:
              args (dict): Dictionary containing:
                  - view_id (int): ID of the Kanban view.
                  - model (str): Model name associated with the view.
                  - view_type (str): Type of view ('kanban').
                  - path (str): XPath to the field in the view.
                  - widget (str): Widget name to set on the field.
                  - invisible (bool/str): Visibility status of the field.
                  - active_fields (list): List of active fields to add if not present.

          Returns:
              str: XML snippets representing updated field and any added placeholders.
          """
        self.is_studio_user()
        view_rec = self.get_studio_view(args['view_id'], args['model'], args['view_type'])
        widget = args.get('widget') or ''
        widget_attr = f'<attribute name="widget">{widget}</attribute>' if widget else '<attribute name="widget"/>'
        view_arch = f'''
                                        <xpath expr="{args['path']}" position="attributes">
                                           <attribute name="invisible">{args.get('invisible', 'False')}</attribute>
                                            {widget_attr}
                                        </xpath>'''

        not_present_field = self.create_invisible(
            [{'invisible': args['invisible'], 'active_fields': args['active_fields'], 'model': args['model'], }])
        view_node = etree.fromstring(view_rec.arch_base)
        not_present_field1 = ''
        not_present_field2 = ''
        if not_present_field:
            not_present_field1 = f'''<xpath expr="/kanban" position="inside">
                                      {not_present_field}
                                 </xpath>'''
            not_present_field2 = f''' <xpath expr="{args['path']}" position="after">{not_present_field}</xpath>'''
            view_node.append(etree.fromstring(not_present_field1))
            view_node.append(etree.fromstring(not_present_field2))
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch + not_present_field1 + not_present_field2

    @route('/cyllo_studio/delete/kanban/field', type="json", auth="user",
           csrf=False)
    def delete_kanban_field(self, view_id, view_type, model, path, field_name=None, child_field_name=None):
        """
           Delete a field from a Kanban view, optionally removing child fields as well.

           Parameters:
               view_id (int): ID of the Kanban view.
               view_type (str): Type of view ('kanban').
               model (str): Model name associated with the view.
               path (str): XPath to the field in the view to be removed.
               field_name (str, optional): Name of the field to remove from templates.
               child_field_name (list, optional): List of child field names to remove.

           Returns:
               str: XML string representing the deletions applied to the view.
           """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_node = etree.fromstring(view_rec.arch_base)

        view_arch = f'''
                                <xpath expr="/{path}" position="replace"/>
                           '''
        view_node.append(etree.fromstring(view_arch))
        arch = view_arch

        if field_name:
            view_arch_2 = f'''
                                     <xpath expr="//templates" position="before">
                                          <field name="{field_name}"/>
                                     </xpath>
                                 '''
            view_node.append(etree.fromstring(view_arch_2))
            arch += view_arch_2

        if child_field_name:
            for field_name in child_field_name:
                view_arch_3 = f'''
                                             <xpath expr="//templates" position="before">
                                                  <field name="{field_name}"/>
                                             </xpath>
                                         '''
                view_node.append(etree.fromstring(view_arch_3))
                arch += view_arch_3

        view_rec.arch_base = etree.tostring(view_node, pretty_print=True,
                                            encoding='unicode')
        return arch

    @route('/cyllo_studio/kanban/add/div', type="json", auth="user",
           csrf=False)
    def add_kanban_div(self, view_id, view_type, model, path, position):
        """
            Add a <div> element to a Kanban view at a specific position.

            Parameters:
                view_id (int): ID of the Kanban view.
                view_type (str): Type of view ('kanban').
                model (str): Model name.
                path (str): XPath to the target position in the view.
                position (str): Position relative to the XPath ('before', 'after', 'inside').

            Returns:
                str: XML snippet representing the added <div> element.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = f'''
                             <xpath expr="/{path}" position="{position}">
                                 <div class="d-flex"/>
                             </xpath>'''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    @route('/cyllo_studio/kanban/update/div', type="json", auth="user",
           csrf=False)
    def update_kanban_div(self, view_id, view_type, model, path, properties):
        """
        Update attributes of an existing <div> element in a Kanban view,
        including class names and inline styles.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            path (str): XPath to the target <div> element.
            properties (dict): Properties to update:
                - is_class (bool): Whether to update class attribute.
                - class_list (list): List of classes to set.
                - is_style (bool): Whether to update style attribute.
                - style (dict): Dictionary with margin and padding values.

        Returns:
            str: XML snippet representing the updated <div> element.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = f'''
                         <xpath expr="/{path}" position="attributes">
                        '''
        if properties['is_class']:
            view_arch += f'''
                                <attribute name="class">{" ".join(properties['class_list'])}</attribute>
                             '''
        if properties['is_style']:
            style = properties['style']
            view_arch += f'''<attribute name="style">margin: {style['marginTop']}px {style['marginRight']}px {style['marginBottom']}px {style['marginLeft']}px !important;
                    padding: {style['paddingTop']}px {style['paddingRight']}px {style['paddingBottom']}px {style['paddingLeft']}px !important;
                    </attribute>
                '''
        view_arch += '</xpath>'
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    @route('/cyllo_studio/kanban/add/menu', type="json", auth="user",
           csrf=False)
    def add_kanban_menu(self, view_id, view_type, model):
        """
            Add an editable dropdown menu to Kanban cards containing Edit/Delete actions.

            Parameters:
                view_id (int): ID of the Kanban view.
                view_type (str): Type of view ('kanban').
                model (str): Model name.

            Returns:
                None: Updates the view directly.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = '''
                              <xpath expr="//kanban/templates" position="inside">
                                  <t t-name="kanban-menu">
                                    <t t-if="widget.editable">
                                        <a role="menuitem" type="edit" class="dropdown-item">Edit
                                        </a>
                                    </t>
                                    <t t-if="widget.deletable">
                                        <a role="menuitem" type="delete" class="dropdown-item">Delete</a>
                                    </t>
                                </t>
                              </xpath>'''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/remove/menu', type="json", auth="user",
           csrf=False)
    def remove_kanban_menu(self, view_id, view_type, model):
        """
           Remove the custom dropdown menu from Kanban cards.

           Parameters:
               view_id (int): ID of the Kanban view.
               view_type (str): Type of view ('kanban').
               model (str): Model name.

           Returns:
               None: Updates the view directly.
           """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = '''
                          <xpath expr="//t[@t-name='kanban-menu']" position="replace"/>
                         '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/add/color_picker', type="json", auth="user",
           csrf=False)
    def add_kanban_color_picker(self, view_id, view_type, model, has_field, field):
        """
        Add a color picker field to Kanban cards, creating the field if it doesn't exist.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            has_field (bool): True if field already exists.
            field (str): Field name to add for color picking.

        Returns:
            None: Updates the view directly.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_node = etree.fromstring(view_rec.arch_base)
        if not has_field:
            request.env['ir.model.fields'].create({
                'name': field,
                'field_description': 'Color Index',
                'ttype': 'integer',
                'model_id': view_rec.model_id.id,
            })
        view_arch = f'''
                          <xpath expr="//templates" position="before">
                              <field name="{field}"/>
                          </xpath>
                          '''
        view_node.append(etree.fromstring(view_arch))
        view_arch = f'''
                              <xpath expr="//t[@t-name='kanban-menu']" position="inside">
                                  <ul class="oe_kanban_colorpicker" data-field="{field}"/>
                              </xpath>
                              '''
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/remove/color_picker', type="json", auth="user",
           csrf=False)
    def remove_kanban_color_picker(self, view_id, view_type, model, path):
        """
        Add a progress bar to a Kanban view with configurable field, help text, and color ranges.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            properties (dict): Properties for the progress bar:
                - field (str): Field to track progress.
                - sum_field (str, optional): Field to calculate sum for progress.
                - help (str): Help text for the progress bar.
                - colors (list of tuples): Color ranges for the progress bar.

        Returns:
            None: Updates the view directly.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = f'''
                             <xpath expr="/{path}" position="replace"/>
                             '''
        view_node = etree.fromstring(view_rec.arch_base)

        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/add/progressbar', type="json", auth="user",
           csrf=False)
    def add_kanban_progressbar(self, view_id, view_type, model, properties):
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        color_dict = {key: value for key, value in properties.get('colors', [])}
        view_arch = f'''
                                <xpath expr="//templates" position="before">
                                    <progressbar field="{properties['field']}" 
                                    sum_field="{properties.get('sum_field', '')}" 
                                    help="{escape(str(properties.get('help', '')))}"
                                    colors='{json.dumps(color_dict)}' />
                                </xpath>'''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/update/progressbar', type="json", auth="user",
           csrf=False)
    def update_kanban_progressbar(self, view_id, view_type, model, properties):
        """
        Update attributes of an existing progress bar in a Kanban view.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            properties (dict): Attributes to update on the progress bar, including:
                - field (str): Field associated with progress.
                - sum_field (str, optional): Field used for sum calculation.
                - help (str): Help text.
                - colors (dict/list): Color mapping for progress ranges.
        Returns:
            None: Updates the view directly.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = '''
                           <xpath expr="//progressbar" position="attributes">
                           '''
        for key, value in properties.items():
            view_arch += f"<attribute name='{key}'>{json.dumps(value) if key == 'colors' else escape(value)}</attribute>"
        view_arch += "</xpath>"

        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/kanban/remove/progressbar', type="json", auth="user",
           csrf=False)
    def remove_kanban_progressbar(self, view_id, view_type, model):
        """
        Remove a progress bar from a Kanban view.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.

        Returns:
            None: Updates the view directly.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = '''
                           <xpath expr="//progressbar" position="replace"/>
                       '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/edit/kanban_view', type="json", auth="user",
           csrf=False)
    def edit_kanbanview(self, view_id, view_type, model, name, value=""):
        """
        Edit a top-level attribute of the Kanban view.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            name (str): Name of the attribute to update.
            value (str, optional): New value for the attribute.

        Returns:
            str: XML snippet representing the attribute update.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        arch_base = f'''                       
                        <xpath expr="//kanban" position="attributes">
                            <attribute name="{name}">{value}</attribute>
                        </xpath>
                        '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(arch_base))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return arch_base

    @route('/cyllo_studio/kanban/remove', type="json", auth="user",
           csrf=False)
    def remove_kanban_element(self, view_id, view_type, model, path,
                              field_name):
        """
        Remove a specific element from a Kanban view and optionally remove associated field from templates.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            path (str): XPath to the element to remove.
            field_name (str): Name of the associated field in templates to remove.

        Returns:
            str: XML representing the removed element and field.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_node = etree.fromstring(view_rec.arch_base)

        view_arch = f'''
                          <xpath expr="/{path}" position="replace"/>
                        '''
        view_node.append(etree.fromstring(view_arch))

        view_arch_2 = ""

        if field_name:
            view_arch_2 = f'''
                                  <xpath expr="//templates" position="before">
                                       <field name="{field_name}"/>
                                  </xpath>
                              '''
            view_node.append(etree.fromstring(view_arch_2))

        arch = view_arch + view_arch_2
        view_rec.arch_base = etree.tostring(view_node, pretty_print=True,
                                            encoding='unicode')
        return arch

    @route('/cyllo_studio/kanban/move', type="json", auth="user",
           csrf=False)
    def move_kanban_element(self, view_id, view_type, model, path, position, sibling_path):
        """
        Move an element within a Kanban view relative to a sibling element.

        Parameters:
            view_id (int): ID of the Kanban view.
            view_type (str): Type of view ('kanban').
            model (str): Model name.
            path (str): XPath to the element to move.
            position (str): Relative position ('before', 'after', 'inside').
            sibling_path (str): XPath of the sibling element for reference.

        Returns:
            str: XML snippet representing the move operation.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        view_arch = f'''
                          <xpath expr="/{sibling_path}" position="{position}">
                              <xpath expr="/{path}" position="move"/>
                          </xpath>'''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    @route('/cyllo_studio/form/remove/text_element', type="json", auth="user",
           csrf=False)
    def remove_form_text_element(self, view_id, view_type, model, path):
        self.is_studio_user()
        arch_base = f'<xpath expr="/{path}" position="replace"/>'
        view_rec = self.get_studio_view(view_id, model, view_type)
        node = etree.fromstring(view_rec.arch_base)
        node.append(etree.fromstring(arch_base))
        view_rec.arch_base = etree.tostring(node, pretty_print=True, encoding='unicode')
        return arch_base

    @route('/cyllo_studio/form/add/kanban_view', type="json", auth="user", csrf=False)
    def add_kanban_view(self, arch, model):
        """
        Add a new Kanban view for a model, removing custom Studio attributes before creation.

        Parameters:
            arch (str): XML architecture of the Kanban view.
            model (str): Model name.

        Returns:
            None: Creates the Kanban view and updates XML IDs in `ir.model.data`.
        """
        self.is_studio_user()
        model_id = request.env['ir.model']._get_id(model)
        kanban = etree.fromstring(arch)

        def remove_custom_attributes(element):
            """
            Recursively removes specific custom attributes from an XML element and its children.

            This function is used to clean up the XML by removing temporary attributes that are not needed for the final view definition.

            Parameters:
                element (etree.Element): The root XML element to process.

            Returns:
                None: The function modifies the XML element tree in place.
            """
            # List of attributes to remove
            attributes_to_remove = ['cy-xpath']
            # Iterate through the attributes and remove if present
            for attr in attributes_to_remove:
                if attr in element.attrib:
                    del element.attrib[attr]
                # Recursively call the function for each child element
                for child in element:
                    remove_custom_attributes(child)

        remove_custom_attributes(kanban)
        arch = etree.tostring(kanban, pretty_print=True).decode('utf-8')
        kanban_view = request.env['ir.ui.view'].sudo().create({
            'name': f"Cy_Studio_kanban_{model.replace('.', '_')}_{str(uuid.uuid4())[:8]}",
            'type': 'kanban',
            'model': model,
            'model_id': model_id,
            'arch': arch,
        })
        request.env['ir.model.data']._update_xmlids([{
            'xml_id': f"cy_studio.{model.replace('.', '_')}_kanban_view_{str(uuid.uuid4())[:8]}",
            'record': kanban_view,
        }])

    ##-------------------------------------------------------------------------------------------

    # list functionalities

    @route('/cyllo_studio/move/tree', auth="user", csrf=False, type='json')
    def move_tree(self, args, kwargs, model, view_id, view_type):
        """
            Move a field in a tree view to a new position.

            Parameters:
                args (list): Additional arguments (unused in current implementation).
                kwargs (dict): Dictionary containing:
                    - path (str): XPath of the field to move.
                    - position (str): Position relative to target XPath ('before', 'after', 'inside').
                    - fieldPath (str): XPath of the field to move.
                    - view_id (int, optional): ID of the view.
                    - viewType (str): Type of view.
                model (str): Model name.
                view_id (int): ID of the tree view.
                view_type (str): Type of view ('tree').

            Returns:
                str: XML snippet representing the move operation.
            """
        self.is_studio_user()
        if not kwargs['path']:
            kwargs['path'] = '/tree'
        tree_arch_base = f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}">' \
                         f'<xpath expr="/{kwargs["fieldPath"]}" position="move"/>' \
                         '</xpath>'
        view = request.env['ir.ui.view'].sudo()

        if not kwargs['view_id']:
            kwargs['view_id'] = view.default_view(kwargs['model'],
                                                  kwargs['viewType'])
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(tree_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')

        return tree_arch_base

    @http.route('/cyllo_studio/reset_view', type='json', auth='user')
    def reset_view(self, model, view_type, view_id):
        self.is_studio_user()

        base_view = request.env['ir.ui.view'].browse(int(view_id))

        studio_view = request.env['ir.ui.view'].search([
            ('inherit_id', '=', base_view.id),
            ('name', 'ilike', 'Cyllo Studio')
        ])

        if studio_view:
            # studio_view.unlink()
            studio_view.write({'active': False})

        return True

    @http.route('/cyllo_studio/get_deactivated_views', type='json', auth='user')
    def get_deactivated_views(self, view_id):
        self.is_studio_user()
        base_view = request.env['ir.ui.view'].browse(int(view_id))
        studio_views = request.env['ir.ui.view'].with_context(active_test=False).search([
            ('inherit_id', '=', base_view.id),
            ('name', 'ilike', 'Cyllo Studio'),
            ('active', '=', False),
        ])
        return [
            {'id': v.id, 'name': v.name, 'write_date': v.write_date.strftime('%Y-%m-%d %H:%M') if v.write_date else '',
             'create_date': v.create_date.strftime('%Y-%m-%d %H:%M') if v.create_date else ''} for v in studio_views]

    @http.route('/cyllo_studio/activate_single_view', type='json', auth='user')
    def activate_single_view(self, view_id, base_view_id):
        self.is_studio_user()
        # First, deactivate ALL currently active studio views for this base view
        base_view = request.env['ir.ui.view'].browse(int(base_view_id))

        active_studio_views = request.env['ir.ui.view'].search([
            ('inherit_id', '=', base_view.id),
            ('name', 'ilike', 'Cyllo Studio'),
            ('active', '=', True),
        ])
        if active_studio_views:
            active_studio_views.write({'active': False})

        # Now activate only the selected one
        target_view = request.env['ir.ui.view'].with_context(active_test=False).browse(int(view_id))
        if target_view:
            target_view.write({'active': True})
            request.env['ir.ui.view'].clear_caches()

        return True

    @http.route('/cyllo_studio/preview_view', type='json', auth='user')
    def preview_view(self, view_id, base_view_id):
        """Temporarily swap active studio view for preview - stores previous state in session"""
        self.is_studio_user()
        base_view = request.env['ir.ui.view'].browse(int(base_view_id))

        # Store currently active studio view IDs in session for revert
        active_studio_views = request.env['ir.ui.view'].search([
            ('inherit_id', '=', base_view.id),
            ('name', 'ilike', 'Cyllo Studio'),
            ('active', '=', True),
        ])
        request.session['cy_preview_previous_active'] = active_studio_views.ids
        request.session['cy_preview_base_view_id'] = int(base_view_id)

        # Deactivate all active studio views
        if active_studio_views:
            active_studio_views.write({'active': False})

        # Activate only the selected preview view
        target_view = request.env['ir.ui.view'].with_context(active_test=False).browse(int(view_id))
        if target_view:
            target_view.write({'active': True})
            request.env['ir.ui.view'].clear_caches()

        return {'success': True, 'previewing_id': int(view_id)}

    @http.route('/cyllo_studio/cancel_preview', type='json', auth='user')
    def cancel_preview(self):
        """Revert to previously active studio views before preview"""
        self.is_studio_user()
        previous_ids = request.session.get('cy_preview_previous_active', [])
        base_view_id = request.session.get('cy_preview_base_view_id')

        if base_view_id:
            base_view = request.env['ir.ui.view'].browse(base_view_id)

            # Deactivate current preview view
            current_active = request.env['ir.ui.view'].search([
                ('inherit_id', '=', base_view.id),
                ('name', 'ilike', 'Cyllo Studio'),
                ('active', '=', True),
            ])
            if current_active:
                current_active.write({'active': False})

            # Restore previous active views
            if previous_ids:
                prev_views = request.env['ir.ui.view'].with_context(active_test=False).browse(previous_ids)
                prev_views.write({'active': True})

            request.env['ir.ui.view'].clear_caches()

        # Clear session
        request.session.pop('cy_preview_previous_active', None)
        request.session.pop('cy_preview_base_view_id', None)

        return True

    @http.route('/cyllo_studio/reactivate_view', type='json', auth='user')
    def reactivate_view(self, view_id):
        self.is_studio_user()

        base_view = request.env['ir.ui.view'].browse(int(view_id))

        studio_views = request.env['ir.ui.view'].search([
            ('inherit_id', '=', base_view.id),
            ('name', 'ilike', 'Cyllo Studio'),
            ('active', '=', False),
        ])

        if studio_views:
            studio_views.write({'active': True})
            request.env['ir.ui.view'].clear_caches()

        return True

    @http.route('/cyllo_studio/check_view_customized', type='json', auth='user')
    def check_view_customized(self, view_id):
        self.is_studio_user()
        studio_view = request.env['ir.ui.view'].search([
            ('inherit_id', '=', int(view_id)),
            ('name', 'ilike', 'Cyllo Studio')
        ], limit=1)

        return bool(studio_view)

    @route('/cyllo_studio/create/new_fields', type="json", auth="user",
           csrf=False)
    def create_new_fields(self, args, view_id, model, view_type):
        """
        Create or edit new fields in a form or tree view, including relational and normal fields.

        Parameters:
            args (list): List of dictionaries describing the field(s) to create or update.
            view_id (int): ID of the view to modify.
            model (str): Model name.
            view_type (str): Type of view ('form', 'tree').

        Returns:
            str: XML snippet representing the new or updated field(s).
        """
        self.is_studio_admin()
        keys_to_escape = {'placeholder', 'help', 'invisible', 'readonly', 'required'}
        xpath_blocks = []

        model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
        if not model_rec:
            raise UserError(f"Model {model} not found")
        if args[0].get('edit'):
            attributes = ""
            optional_fields = args[0].get("optional_fields", {})
            if optional_fields:
                attributes += f'''<attribute name="options">{escape(str(optional_fields))}</attribute>'''
                options_dict = {}

                if optional_fields.get("minimal_precision"):
                    options_dict["datepicker"] = options_dict.get("datepicker", {})
                    options_dict["datepicker"]["minDate"] = optional_fields["minimal_precision"]

                if optional_fields.get("maximal_precision"):
                    options_dict["datepicker"] = options_dict.get("datepicker", {})
                    options_dict["datepicker"]["maxDate"] = optional_fields["maximal_precision"]

                # Add options attribute if we have precision settings
                if options_dict:
                    # Escape and add to attributes
                    attributes += f'''<attribute name="options">{escape(str(options_dict))}</attribute>'''

                # Also add the original options handling
                if optional_fields and not any(
                        k in optional_fields for k in ["minimal_precision", "maximal_precision"]):
                    attributes += f'''<attribute name="options">{escape(str(optional_fields))}</attribute>'''

                if optional_fields.get("statusbar_visible"):
                    visible = optional_fields["statusbar_visible"]
                    if isinstance(visible, (list, tuple)):
                        visible = ",".join(map(str, visible))
                    else:
                        visible = re.sub(r",\s+", ",", str(visible))
                    attributes += f'''<attribute name="statusbar_visible">{escape(visible)}</attribute>'''

            if args[0].get("value", {}).get("sql_constraints") is not None:
                sql_constraints = args[0]["value"]["sql_constraints"]
                field_name = args[0].get("field_name")
                # Only allow constraint changes on custom (manual) fields
                _field_rec_check = request.env['ir.model.fields'].search([
                    ('model_id', '=', model_rec.id),
                    ('name', '=', field_name),
                ], limit=1)
                _is_manual_field = _field_rec_check and _field_rec_check.state == 'manual'
                if _is_manual_field:
                    if len(sql_constraints) > 0:
                        _logger.info(f"Saving {len(sql_constraints)} SQL constraints for field: {field_name}")
                        self._save_sql_constraints(model_rec, sql_constraints)
                        attributes += '<attribute name="constrains">true</attribute>'
                    else:
                        if field_name:
                            self._remove_sql_constraints(model_rec, field_name)
                        attributes += '<attribute name="constrains">false</attribute>'
                else:
                    _logger.info(f"Skipping SQL constraint change for base field: {field_name}")

            field_name = args[0].get("field_name")
            if args[0].get("value", {}).get("python_constraint") is not None:
                python_constraint = args[0]["value"]["python_constraint"]
                if python_constraint:
                    deps = python_constraint.get("deps", "").strip()
                    code = python_constraint.get("code", "").strip()
                    if deps and code:
                        _py_model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
                        if _py_model_rec:
                            field_rec = request.env['ir.model.fields'].search([
                                ('model_id', '=', _py_model_rec.id),
                                ('name', '=', field_name),
                            ], limit=1)
                            # Only write Python constraints to custom (manual) fields
                            if field_rec and field_rec.state == 'manual':
                                field_rec.write({
                                    'constraint_code': code,
                                    'constraint_fields': deps,
                                })
                                _logger.info(
                                    f"✓ Saved Python constraint for field {field_name}: "
                                    f"deps={deps}, code_length={len(code)}"
                                )
                            elif field_rec:
                                _logger.info(f"Skipping Python constraint write for base field: {field_name}")
            if args[0].get("value", {}).get("python_constraint") is None:
                _clear_model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
                if _clear_model_rec and field_name:
                    field_rec = request.env['ir.model.fields'].search([
                        ('model_id', '=', _clear_model_rec.id),
                        ('name', '=', field_name),
                    ], limit=1)
                    # Only clear Python constraints from custom (manual) fields
                    if field_rec and field_rec.state == 'manual':
                        field_rec.write({
                            'constraint_code': False,
                            'constraint_fields': False,
                        })
                        _logger.info(f"✓ Removed Python constraint from field {field_name}")
                    elif field_rec:
                        _logger.info(f"Skipping Python constraint clear for base field: {field_name}")

            dynamic_placeholder_field = args[0].get("value", {}).get("dynamic_placeholder")
            if dynamic_placeholder_field:
                try:
                    related_model_name = args[0].get("model") or model
                    model_rec_obj = request.env[related_model_name]

                    if hasattr(model_rec_obj, dynamic_placeholder_field):
                        field_obj = model_rec_obj._fields.get(dynamic_placeholder_field)
                        if field_obj:
                            placeholder_text = getattr(field_obj, 'string', dynamic_placeholder_field)
                        else:
                            placeholder_text = dynamic_placeholder_field
                    else:
                        placeholder_text = dynamic_placeholder_field

                    attributes += f'''<attribute name="placeholder">{escape(str(placeholder_text))}</attribute>'''
                except Exception as e:
                    attributes += f'''<attribute name="placeholder">{escape(str(dynamic_placeholder_field))}</attribute>'''

            elif 'placeholder' in args[0].get('value', {}):
                placeholder_value = args[0]['value']['placeholder']
                attributes += f'''<attribute name="placeholder">{escape(str(placeholder_value))}</attribute>'''

            if args[0].get("value", {}).get("is_computed"):
                compute_code = (args[0]["value"].get("compute") or "").strip()
                deps_raw = (args[0]["value"].get("depends") or "").strip()

                depends_csv = ",".join(
                    dep.strip() for dep in deps_raw.split(",") if dep.strip()
                )

                if not compute_code:
                    raise UserError("Compute code cannot be empty.")

                if not depends_csv:
                    raise UserError("Please specify at least one dependency.")

                model_name = args[0].get("model")
                field_name = args[0].get("field_name")
                model_rec = request.env["ir.model"].search([("model", "=", model_name)], limit=1)

                if not model_rec:
                    raise UserError("Model not found.")

                field_rec = request.env["ir.model.fields"].search([
                    ("model_id", "=", model_rec.id),
                    ("name", "=", field_name),
                ], limit=1)

                if not field_rec:
                    raise UserError("Unable to locate field to update.")

                if field_rec.state == 'manual':
                    field_rec.write({
                        "compute": compute_code,
                        "depends": depends_csv,
                        "store": True,
                        "related": False,
                        "readonly": False,
                    })

            if args[0].get("value", {}).get("is_computed") == False:
                model_name = args[0].get("model")
                field_name = args[0].get("field_name")

                model_rec = request.env["ir.model"].search([("model", "=", model_name)], limit=1)

                if model_rec:
                    field_rec = request.env["ir.model.fields"].search([
                        ("model_id", "=", model_rec.id),
                        ("name", "=", field_name),
                    ], limit=1)

                    if field_rec and field_rec.state == 'manual':
                        # Clear compute fields
                        field_rec.write({
                            "compute": False,
                            "depends": False,
                            "related": False,
                            "store": field_rec.store,
                            "readonly": False,
                        })

            for key, value in args[0]['value'].items():
                if key and value is not None:
                    if key in ('domain', 'context', 'invisible', 'readonly', 'required', 'column_invisible',
                               'dynamic_placeholder'):
                        attributes += f'''<attribute name="{key}">{escape(str(value))}</attribute>'''
                    # elif key == 'field_info':
                    elif key in ('field_info', 'compute_dependencies', 'is_computed', 'compute', 'depends',
                                 'compute_code', 'default_value', 'sql_constraints'):
                        continue
                    else:
                        attributes += f'''<attribute name="{key}">{escape(str(value))}</attribute>'''
            xpath_blocks.append(f'''
                        <xpath expr="/{args[0]["field_path"]}" position="attributes">
                            {attributes}
                        </xpath>
                    ''')
            # Label update
            if args[0]['label_path']:
                if 'string' in args[0]['value']:
                    label_block = f'''
                            <xpath expr="/{args[0]['label_path']}" position="attributes">
                                <attribute name="string">{escape(str(args[0]['value']['string']))}</attribute>
                            </xpath>
                        '''
                    xpath_blocks.append(label_block)
        if not args[0].get('edit') and args[0].get('technical_name'):
            related_model = args[0].get('related_model')
            values = {
                'name': args[0]['technical_name'] + str(uuid.uuid4())[:5],
                'field_description': args[0]['label'],
                'ttype': args[0]['field_type'],
                'is_studio': True,
                'model_id': request.env['ir.model'].search(
                    [('model', '=', model)]).id,
            }

            if args[0].get("attrs", {}).get("related"):
                related_path = args[0]["attrs"]["related"]
                parts = related_path.split(".")
                current_model = request.env[model]
                for field_name in parts[:-1]:
                    field = current_model._fields.get(field_name)
                    if not field:
                        raise UserError(
                            f"Invalid related path: field '{field_name}' not found in model {current_model._name}"
                        )
                    if not getattr(field, "comodel_name", False):
                        raise UserError(
                            f"Field '{field_name}' in model {current_model._name} is not a relational field"
                        )
                    current_model = request.env[field.comodel_name]
                final_field = parts[-1]
                target_field = current_model._fields.get(final_field)
                if not target_field:
                    raise UserError(
                        f"Final field '{final_field}' does not exist in model {current_model._name}"
                    )
                values["ttype"] = target_field.type
                values["related"] = related_path
                values["store"] = True
                values["readonly"] = True
                if target_field.relational:
                    values["relation"] = getattr(target_field, "comodel_name", False)
                if target_field.type == "selection":
                    values["selection"] = getattr(target_field, "selection", [])

            if args[0]['field_type'] in ['many2one', 'many2many']:
                values['relation'] = related_model
            if args[0]['field_type'] == 'one2many':
                related_field = args[0].get('related_model_field')
                if not related_field or not related_field.get('model_id'):
                    raise UserError("A One2many field requires a valid Many2one inverse field.")

                related_model_id = request.env['ir.model'].browse(related_field['model_id'][0])
                values.update({
                    'relation': related_model_id.model,
                    'relation_field': related_field['name']
                })
            if values['ttype'] == 'selection':
                values.update({
                    'selection_ids': [
                        Command.create(
                            {'value': element.lower(), 'name': element,
                             'sequence': idx})
                        for idx, element in
                        enumerate(args[0]['selectionValues'])
                    ]
                })

            new_field = request.env['ir.model.fields'].create(values)
            field_name_for_default = new_field.name

            if args[0]['sibling']:
                if args[0]['item_type'] == "normal":
                    existing_field_name = args[0]['field_info']['name']
                    element_arch = f"""<field name='{new_field.name}' """
                    for key, value in args[0]['attrs'].items():
                        if key and value:
                            if key in keys_to_escape:
                                element_arch += f'''{key}="{escape(str(value))}" '''
                            else:
                                element_arch += f'''{key}="{value}" '''
                    element_arch += "/>"

                    xpath_blocks.append(f'''
                            <xpath expr="/{args[0]["cy_path"]}" position="replace">
                                <label for="{existing_field_name}"/>
                                <div class="o_row">
                                    <field name="{existing_field_name}"/>
                                    {element_arch}
                                </div>
                            </xpath>
                        ''')

                else:
                    inside_field = f"""<field name="{new_field.name}" """
                    for key, value in args[0]['attrs'].items():
                        if key and value:
                            if key == 'some_other_key_to_skip':  # Placeholder if needed, otherwise just remove the skip
                                continue
                            if key in keys_to_escape:
                                inside_field += f'''{key}="{escape(str(value))}" '''
                            else:
                                inside_field += f'''{key}="{value}" '''
                    if args[0]["optional_fields"]:
                        inside_field += f'options="{escape(str(args[0]["optional_fields"]))}"'
                    inside_field += "/>"

                    xpath_blocks.append(f'''
                            <xpath expr="/{args[0]["cy_path"]}" position="inside">
                                {inside_field}
                            </xpath>
                        ''')
            else:
                new_field_tag = f"""<field name='{new_field.name}' """
                for key, value in args[0]['attrs'].items():
                    if key and value is not None:
                        # Skip dynamic_placeholder and placeholder in attrs, handle separately
                        if key == 'some_other_key_to_skip':  # Placeholder if needed
                            continue
                        if key == 'placeholder':
                            continue
                        if key in ('domain', 'context'):
                            new_field_tag += f'''{key}="{escape(str(value))}" '''
                        elif key in keys_to_escape:
                            new_field_tag += f'''{key}="{escape(str(value))}" '''
                        else:
                            new_field_tag += f'''{key}="{escape(str(value))}" '''

                if args[0]['attrs'].get('placeholder'):
                    placeholder_value = args[0]['attrs']['placeholder']
                    new_field_tag += f'''placeholder="{escape(str(placeholder_value))}" '''
                if args[0]["optional_fields"]:
                    new_field_tag += f'''options="{escape(str(args[0]["optional_fields"]))}"'''
                new_field_tag += "/>"

                xpath_blocks.append(f"""
                        <xpath expr='/{args[0]['field_path']}' position='{args[0]["position"]}'>
                            {new_field_tag}
                        </xpath>
                    """)

                default_value = None
                if args[0].get('attrs') and args[0]['attrs'].get('default_value'):
                    default_value = args[0]['attrs']['default_value']

                if args[0].get('edit') and args[0].get('value'):
                    if 'default_value' in args[0]['value']:
                        default_value = args[0]['value']['default_value']

                if default_value is not None and default_value != '' and field_name_for_default:
                    request.env['ir.default'].set(
                        model_name=model,
                        field_name=field_name_for_default,
                        value=default_value,
                        user_id=False,
                        company_id=False,
                        condition=False
                    )

                elif args[0].get('edit') and 'default_value' in args[0].get('value', {}):
                    if args[0]['value']['default_value'] == '' and field_name_for_default:
                        field = request.env['ir.model.fields']._get(model, field_name_for_default)
                        defaults = request.env['ir.default'].search([
                            ('field_id', '=', field.id),
                            ('user_id', '=', False),
                            ('company_id', '=', False),
                            ('condition', '=', False),
                        ])
                        if defaults:
                            defaults.unlink()

        form_arch_base = "".join(xpath_blocks)
        view_rec = self.get_studio_view(view_id, model, view_type)

        form_node = etree.fromstring(view_rec.arch_base)
        created_field_arch = ''
        not_present_fields = self.create_invisible(args)
        if not_present_fields:
            if args[0].get('edit') and args[0].get('field_path'):
                field_path = args[0]["field_path"].lstrip('/')
                created_field_arch = f'''<xpath expr="//{field_path.split('/')[0]}" position="inside">
                                {not_present_fields}
                                </xpath>
                           '''
                form_node.append(etree.fromstring(created_field_arch))
            # For creating new fields
            elif args[0].get('cy_path'):
                cy_path = args[0]["cy_path"].lstrip('/')
                created_field_arch = f'''<xpath expr="//{cy_path.split('/')[0]}" position="inside">
                                {not_present_fields}
                                </xpath>
                           '''
                form_node.append(etree.fromstring(created_field_arch))
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base + created_field_arch

    ##-------------------------------------------------------------------------------------------

    # Delete Functionality

    @route('/cyllo_studio/delete/existing_fields', type="json", auth="user",
           csrf=False)
    def delete_existing_fields(self, args, kwargs, model, view_id, view_type):
        """
        Delete existing fields from a form or tree view, optionally removing labels as well.

        Parameters:
            args (list): List of dictionaries specifying fields and paths to remove.
            kwargs (dict): Additional parameters including:
                - view_id (int, optional): ID of the view.
                - view_type (str): Type of view ('form', 'list').
            model (str): Model name.
            view_id (int): ID of the view.
            view_type (str): Type of view ('form', 'tree').

        Returns:
            str: XML snippet representing the removed fields.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        name1 = str(args[0]['model']) + ".form." + "edit.field." + args[0][
            'fieldName']
        name2 = str(args[0]['model']) + ".form." + "add.field." + args[0][
            'fieldName']
        view = request.env['ir.ui.view'].sudo()
        if not kwargs['view_id']:
            kwargs['view_id'] = view.default_view(args[0]['model'], "form")
        view_type = kwargs['view_type']
        if kwargs['view_type'] == "list":
            view_type = "tree"
        if isinstance(args[0]['label_path'], dict) and args[0]['label_path'].get('first_path'):
            form_arch_1 = f'''<xpath expr="/{args[0]['label_path']['first_path']}" position="replace"/>'''
            form_arch_2 = f'''<xpath expr="/{args[0]['label_path']['second_path']}" position="replace"/>'''
            form_node.append(etree.fromstring(form_arch_1))
            form_node.append(etree.fromstring(form_arch_2))
            form_arch_base = form_arch_1 + form_arch_2
        else:
            form_arch_base = f'''<xpath expr="/{args[0]['path']}" position="replace"/>'''
            form_node.append(etree.fromstring(form_arch_base))

        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    # form functionality

    @route('/cyllo_studio/add/component', type="json", auth="user",
           csrf=False)
    def add_component(self, args):
        """
        Add a custom component to a form view at a specified XPath.

        Parameters:
            args (list): List of dictionaries containing:
                - view_id (int): ID of the form view.
                - model (str): Model name.
                - view_type (str): Type of view ('form').
                - path (str): XPath to the location where the component should be added.
                - position (str): Position relative to the XPath ('before', 'after', 'inside').
                - item (str): XML string representing the component to add.

        Returns:
            str: XML snippet representing the added component.
        """
        self.is_studio_user()
        form_arch_base = f'<xpath expr="/{args[0]["path"]}" position="{args[0]["position"]}">' \
                         f'{args[0]["item"]}' \
                         '</xpath>'
        view_rec = self.get_studio_view(args[0]["view_id"], args[0]["model"], args[0]["view_type"])
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/add/form_tree', type="json", auth="user",
           csrf=False)
    def add_form_tree(self, kwargs):
        """
        Add a new one2many/many2many tree field to a form view with specified child fields.

        Parameters:
            kwargs (dict): Dictionary containing:
                - technical_name (str): Field name to create.
                - label (str): Field label.
                - selected_value (str): Field type ('one2many', 'many2many', etc.).
                - resModel (str): Parent model name.
                - related_model_id (int, optional): ID of related model for relational fields.
                - related_model_field (dict, optional): Information about related model field.
                - field_ids (list): List of child field IDs to include in tree.
                - path (str): XPath in form view to insert the field.
                - position (str): Position relative to XPath ('before', 'after', 'inside').
                - view_id (int): ID of the form view.
                - model (str): Model name.
                - view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the added tree field.
        """
        self.is_studio_user()
        values = {
            'name': kwargs['technical_name'],
            'field_description': kwargs['label'],
            'ttype': kwargs['selected_value'],
            'is_studio': True,
            'model_id': request.env['ir.model'].search(
                [('model', '=', kwargs['model'])]).id
        }
        if values['ttype'] == 'many2many':
            values.update({
                'relation': request.env['ir.model'].browse(int(kwargs['related_model_id'])).model
            })
        else:
            values.update({
                'relation': request.env['ir.model'].browse(
                    kwargs['related_model_field']['model_id'][0]).model,
                'relation_field': kwargs['related_model_field']['name']
            })

        new_field = request.env['ir.model.fields'].create(values)

        self.ensure_unique_relation_table(new_field)

        # form_arch_base = f'<xpath expr="/{kwargs["position"]}" position="{kwargs["position"]}">' \
        #                  f'<field name="{kwargs["technical_name"]}"><tree>'

        field_ids = list(map(int, kwargs['field_ids']))

        tree_fields = request.env['ir.model.fields'].browse(field_ids)
        has_one_currency = False
        if kwargs["view_type"] == "kanban":
            form_arch_base = (
                # f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}">'
                f'<xpath expr="{kwargs["path"]}" position="{kwargs["position"]}">'
                f'<field name="{kwargs["technical_name"]}">'
                f'<kanban>'
                f'<templates><t t-name="kanban-box">'
                # f'<div class="oe_kanban_global">'
                f'<div class="oe_kanban_card oe_kanban_global_click">'
            )
        else:
            form_arch_base = (
                f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}">'
                f'<field name="{kwargs["technical_name"]}"><tree>'
            )

        for field in tree_fields:
            if field.ttype == "monetary" and not has_one_currency:
                related_model_id = kwargs.get('related_model_id')
                currency_field_name = self.get_currency_field(related_model_id, field.name)
                if currency_field_name:
                    form_arch_base += f"<field name='{currency_field_name}' column_invisible='1'/>"
                has_one_currency = True

            if kwargs["view_type"] == "kanban":
                # form_arch_base += (
                #     f'<div><strong>{field.field_description}:</strong> '
                #     f'<field name="{field.name}"/></div>'
                # )
                form_arch_base += (
                    f'<div class="oe_kanban_details"><strong>{field.field_description}:</strong> '
                    f'<field name="{field.name}"/></div>'
                )
            else:
                form_arch_base += f'<field name="{field.name}"/>'

            # form_arch_base += f'<field name="{field.name}"/>'
        # form_arch_base += '</tree></field></xpath>'

        if kwargs["view_type"] == "kanban":
            form_arch_base += "</div></t></templates></kanban></field></xpath>"
        else:
            form_arch_base += "</tree></field></xpath>"

        view_rec = self.get_studio_view(kwargs['view_id'], kwargs['model'], kwargs['view_type'])
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/form/create/new_fields', type="json", auth="user",
           csrf=False)
    def form_create_new_fields(self, args, view_id, model, view_type):
        """
        Update attributes of existing fields in a form view, such as string, widget, help, placeholder, and visibility.

        Parameters:
            args (list): List of dictionaries containing field update information:
                - edit (bool): Whether this is an edit of an existing field.
                - cy_path (str): XPath to the field in the form view.
                - label (str): Field label.
                - widget (str): Widget type.
                - help (str): Help text.
                - placeholder (str): Placeholder text.
                - invisible (bool/str): Field visibility.
                - readonly (bool/str): Field readonly status.
                - required (bool/str): Field required status.

            view_id (int): ID of the form view.
            model (str): Model name.
            view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the field attribute updates.
        """
        self.is_studio_admin()
        if args[0]['edit']:
            form_arch_combined = f"""
                   <xpath expr='/{args[0]["cy_path"]}' position='attributes'>
                       <attribute name='string'>{escape(args[0]["label"])}</attribute>
                       <attribute name='widget'>{escape(args[0]["widget"])}</attribute>
                       <attribute name='help'>{escape(args[0]["help"])}</attribute>
                       <attribute name='placeholder'>{escape(args[0]["placeholder"])}</attribute>
                       <attribute name='invisible'>{args[0]["invisible"]}</attribute>
                       <attribute name='readonly'>{args[0]["readonly"]}</attribute>
                       <attribute name='required'>{args[0]["required"]}</attribute>

                       """
            form_arch_combined += f"""</xpath>
                                                 """
            view_rec = self.get_studio_view(view_id, model, view_type)
            form_node = etree.fromstring(view_rec.arch_base)
            form_node.append(etree.fromstring(form_arch_combined))
            view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
            return form_arch_combined

    @route('/cyllo_studio/add/page', type="json", auth="user",
           csrf=False)
    def add_page(self, args, kwargs, model, view_id, view_type):
        """
        Add a new page to a form view.

        Parameters:
            args (list): Unused in current implementation.
            kwargs (dict): Dictionary containing:
                - path (str): XPath to the location to insert the new page.
                - view_id (int, optional): ID of the form view.
                - viewType (str): Type of view ('form').
            model (str): Model name.
            view_id (int): ID of the form view.
            view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the new page.
        """
        self.is_studio_user()
        view = request.env['ir.ui.view'].sudo()
        if not kwargs['view_id']:
            kwargs['view_id'] = view.default_view(kwargs['model'],
                                                  kwargs['viewType'])

        form_arch_base = f'<xpath expr="/{kwargs["path"]}" position="inside">' \
                         f'<page string="New Page"></page>' \
                         '</xpath>'

        view_type = kwargs.get("view_type", "form")
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/update/page', type="json", auth="user",
           csrf=False)
    def update_page(self, args, kwargs, model, view_id, view_type):
        """
        Update attributes of a page in a form view, including title, autofocus, and visibility.

        Parameters:
            args (list): Unused in current implementation.
            kwargs (dict): Dictionary containing:
                - path (str): XPath to the page to update.
                - string (str): New page title.
                - autofocus (bool): Whether page should be focused automatically.
                - invisible (str/bool): Page visibility.
            model (str): Model name.
            view_id (int): ID of the form view.
            view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the page update.
        """
        self.is_studio_user()
        View = request.env['ir.ui.view'].sudo()
        groups_attr = ''
        if kwargs.get('group_ids'):
            group_ids = list(map(int, kwargs['group_ids']))
            groups_attr = ','.join(
                request.env['res.groups'].browse(group_ids).get_external_id().values()
            )
        form_arch_base = f'<xpath expr="/{kwargs["path"]}" position="attributes">' \
                         f'<attribute name="string">{kwargs["string"]}</attribute>' \
                         f'<attribute name="autofocus">{"autofocus" if kwargs["autofocus"] else ""}</attribute>' \
                         f'<attribute name="invisible">{unescape(escape(kwargs["invisible"]))}</attribute>' \
                         f'<attribute name="groups">{groups_attr}</attribute>' \
                         '</xpath>'
        val = self.create_invisible([kwargs])
        not_present_field = ''
        if kwargs.get('not_present_path') and val:
            if kwargs.get('has_sheet_group'):
                not_present_field = f'''<xpath expr="/{kwargs.get('path')}" position="inside">
                {val}
        </xpath>
        '''
        else:
            not_present_field = f'''<xpath expr="/{kwargs.get('path')}" position="inside">
                <group>
                {val}
                </group>
                </xpath>
                '''
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_arch_base = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', form_arch_base)
        form_arch_base = re.sub(r'>([^<]*?)\s+</', lambda match: f'>{match.group(1).strip()}<', form_arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        if not_present_field:
            form_node.append(etree.fromstring(not_present_field))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/move/page', type="json", auth="user",
           csrf=False)
    def move_page(self, args, kwargs, model, view_id, view_type="form"):
        """
        Move a page within a form view relative to another page.

        Parameters:
            args (list): Unused in current implementation.
            kwargs (dict): Dictionary containing:
                - path (str): XPath to the page to move.
                - position (str): Relative position ('before', 'after', 'inside').
                - pagePath (str): XPath of the reference page.
                - view_id (int, optional): ID of the form view.
                - model (str): Model name.
            view_id (int): ID of the form view.
            view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the page move.
        """
        self.is_studio_user()
        view = request.env['ir.ui.view'].sudo()
        if not kwargs['view_id']:
            kwargs['view_id'] = view.default_view(kwargs['model'],
                                                  "form")
        form_arch_base = f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}">' \
                         f'<xpath expr="/{kwargs["pagePath"]}" position="move"/>' \
                         '</xpath>'

        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/delete/existing_page', auth="user", csrf=False,
           type='json')
    def delete_existing_page(self, args, kwargs, model, view_id, view_type):
        """
        Delete an existing page from a form view.

        Parameters:
            args (list): List of dictionaries containing:
                - path (str): XPath to the page to delete.
            kwargs (dict): Additional parameters including view_id and view_type.
            model (str): Model name.
            view_id (int): ID of the form view.
            view_type (str): Type of view ('form').

        Returns:
            str: XML snippet representing the deleted page.
        """
        self.is_studio_user()
        view = request.env['ir.ui.view'].sudo()

        form_arch_base = f'''<xpath expr="{args[0]['path']}" position="replace"/>'''
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True,
                                            encoding='unicode')
        return form_arch_base

    # --------------------------Smart Button functionality ----------------------------------------------------

    @route('/cyllo_studio/add/smart_button', type="json", auth="user",
           csrf=False)
    def add_smart_button(self, kwargs):
        """
        Add a smart button to a form view with an optional action and count field.

        Parameters:
            kwargs (dict): Dictionary containing:
                - view_id (int): ID of the form view.
                - model (str): Model name.
                - label (str): Button label.
                - field (str): Field name used for counting records.
                - field_model (str): Model for the button's action.
                - domain (str): Domain filter for the button action.
                - addButtonBox (bool): Whether to wrap the button in a button box.
                - invisible (bool/str): Visibility of the button.
                - icon (str): Icon for the button.
                - groups (list, optional): Groups allowed to see the button.
                - path (str): XPath for inserting the button.

        Returns:
            str: XML snippet representing the smart button.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(kwargs['view_id'], kwargs['model'], 'form')
        model_id = request.env['ir.model'].search(
            [('model', '=', kwargs['model'])])
        vals = {
            'name': f'x_cy_{kwargs["label"].replace(" ", "_").lower()}_count{str(uuid.uuid4())[:4]}',
            'field_description': f'{kwargs["label"].title()} Count',
            'model_id': model_id.id,
            'ttype': 'char',
            'store': False,
            'depends': kwargs['field'],
        }
        compute_field = request.env['ir.model.fields'].create(vals)
        if kwargs['domain'] != '[]':
            domain = kwargs['domain'][:-1] + f",('id', 'in', record.{kwargs['field'].strip()}.ids)]"
            compute = f"""for record in self:
        record['{compute_field.name}'] = len(record.{kwargs['field'].strip()}.search({domain}))
                    """
            kwargs['domain'] = kwargs['domain'][:-1] + ',]'
        else:
            compute = f"""for record in self:
        record['{compute_field.name}'] = len(record.{kwargs['field'].strip()})
                                """
        compute_field.compute = compute
        action_id = request.env['ir.actions.act_window'].create({
            'name': kwargs["label"].title(),
            'res_model': kwargs['field_model'],
            'view_mode': 'tree,form',
            'domain': kwargs['domain']
        })
        form_arch_base = ''
        if kwargs['addButtonBox']:
            form_arch_base += f'''<xpath expr="//form/sheet/*[1]" position="before">
                                              <div class="oe_button_box" name="button_box" cy-xpath="//form/sheet/div[@class='oe_button_box']">
                                             <button type="action" name="{action_id.id}" invisible='{kwargs["invisible"]}' class="oe_stat_button" icon="{kwargs["icon"]}" '''
            if kwargs['groups']:
                group_ids = list(map(int, kwargs['groups']))
                groups = ','.join(request.env['res.groups'].browse(
                    group_ids).get_external_id().values())
                form_arch_base += f'groups="{groups}"'

            form_arch_base += f'><field name="{compute_field.name}" widget="statinfo" '
            if kwargs['label']:
                form_arch_base += f'string="{kwargs["label"].title()}"'
            form_arch_base += '/></button></div>'
        else:
            form_arch_base += f'''<xpath expr="{kwargs['path']}" position="inside">
                                <button type="action" name="{action_id.id}" invisible='{kwargs["invisible"]}' class="oe_stat_button" icon="{kwargs["icon"]}" '''
            if kwargs['groups']:
                group_ids = list(map(int, kwargs['groups']))
                groups = ','.join(request.env['res.groups'].browse(
                    group_ids).get_external_id().values())
                form_arch_base += f'groups="{groups}"'

            form_arch_base += f'><field name="{compute_field.name}" widget="statinfo" '
            if kwargs['label']:
                form_arch_base += f'string="{kwargs["label"].title()}"'
            form_arch_base += '/></button>'

        form_arch_base += '</xpath>'
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/update/smart_button', type="json", auth="user",
           csrf=False)
    def update_smart_button(self, kwargs):
        """
        Update properties of an existing smart button, such as label, icon, visibility, and groups.

        Parameters:
            kwargs (dict): Dictionary containing:
                - view_id (int): ID of the form or Kanban view.
                - model (str): Model name.
                - button_name (str): Name of the button to update.
                - label (str, optional): New label for the button.
                - icon (str, optional): New icon for the button.
                - invisible (bool/str, optional): Updated visibility.
                - groups (list, optional): Updated groups allowed to see the button.

        Returns:
            str: XML snippet representing the updated smart button.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(kwargs['view_id'], kwargs['model'], 'form')
        group_ids = list(map(int, kwargs['groups']))
        groups = ','.join(request.env['res.groups'].browse(group_ids).get_external_id().values())
        form_arch = f'''<xpath expr="/{kwargs['path']}" position="attributes">
                            <attribute name="string">{escape(kwargs['label'])}</attribute>
                            <attribute name="icon">{kwargs['icon']}</attribute>
                            <attribute name="groups">{groups}</attribute>
                            <attribute name="invisible">{kwargs['invisible']}</attribute>
                        </xpath>'''
        form_arch_2 = ''
        if kwargs["string_path"]:
            if "span" in kwargs["string_path"]:
                form_arch_2 = f"""<xpath expr="/{kwargs['string_path']}" position="replace">
                            <span class="o_stat_text">{escape(kwargs['label'])}</span>
                        </xpath>"""
            elif "field" in kwargs["string_path"]:
                form_arch_2 = f"""<xpath expr="/{kwargs['string_path']}" position="attributes">
                                    <attribute name="string">{escape(kwargs['label'])}</attribute>
                                    <attribute name="icon">{kwargs['icon']}</attribute>
                                </xpath>"""
            else:
                form_arch_2 = f"""<xpath expr="/{kwargs['string_path']}/field" position="attributes">
                    <attribute name="string">{escape(kwargs['label'])}</attribute>
                    <attribute name="icon">{kwargs['icon']}</attribute>
                </xpath>"""
        form_node = etree.fromstring(view_rec.arch_base)

        form_node.append(etree.fromstring(form_arch))
        form_node.append(etree.fromstring(form_arch_2))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        combined_arch = form_arch + form_arch_2
        return combined_arch

    @route('/cyllo_studio/remove/smart_button', type="json", auth="user",
           csrf=False)
    def remove_smart_button(self, kwargs):
        """
        Remove a smart button from a form or Kanban view, including associated count field and action.

        Parameters:
            kwargs (dict): Dictionary containing:
                - view_id (int): ID of the form or Kanban view.
                - model (str): Model name.
                - button_name (str): Name of the button to remove.

        Returns:
            str: XML snippet representing the removed button and any associated fields.
        """
        self.is_studio_user()
        form_arch = f'''<xpath expr="{kwargs['path']}" position="replace"/>'''
        view_rec = self.get_studio_view(kwargs['view_id'], kwargs['model'], 'form')
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch

    @route('/cyllo_studio/move/smart_button', type="json", auth="user",
           csrf=False)
    def move_smart_button(self, kwargs):
        """
            Moves a smart button from one location to another within a form view.

            Parameters:
                kwargs (dict): A dictionary containing:
                    - view_id (int): The ID of the view being modified.
                    - model (str): The name of the model associated with the view.
                    - viewType (str): The type of the view (e.g., 'form').
                    - sourcePath (str): The XPath of the target container where the button will be moved.
                    - position (str): The position within the source path (e.g., 'inside', 'before', 'after').
                    - smartButtonPath (str): The XPath of the smart button to be moved.

            Returns:
                str: The XML patch string used to move the smart button.
            """
        self.is_studio_user()
        view = request.env['ir.ui.view'].sudo()
        if not kwargs['view_id']:
            kwargs['view_id'] = view.default_view(kwargs['model'],
                                                  kwargs['viewType'])
        form_arch_base = f'<xpath expr="/{kwargs["sourcePath"]}" position="{kwargs["position"]}">' \
                         f'<xpath expr="/{kwargs["smartButtonPath"]}" position="move"/>' \
                         '</xpath>'

        view_rec = self.get_studio_view(kwargs["view_id"], kwargs["model"], kwargs['viewType'])
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    ##-------------------------------------------------------------------------------------------

    # --------------------------Button functionality ----------------------------------------------------

    @route('/cyllo_studio/add/button_item', type='json', auth="user", csrf=False)
    def add_button_item(self, kwargs, button_properties):
        """
            Adds a new button to an Odoo view, either as a sibling to an existing element or in a new location.

            Parameters:
                kwargs (dict): A dictionary containing:
                    - viewId (int): The ID of the view being modified.
                    - model (str): The model name.
                    - viewType (str): The view type (e.g., 'form').
                    - sibling (bool): True if the button should be a sibling to an existing element.
                    - item_type (str, optional): The type of the item ('normal' or other).
                    - field_info (dict, optional): Information about the existing field for sibling placement.
                    - path (str): The XPath to the target element or container.
                    - position (str, optional): The position relative to the path.
                    - newHeader (str, optional): A path to a new header element to be created.
                    - groupIds (list, optional): A list of group IDs to restrict button visibility.
                button_properties (dict): A dictionary of button attributes (e.g., 'string', 'class', 'type').

            Returns:
                str: The XML patch string used to add the button.
            """
        self.is_studio_user()
        self.check_arch_path(kwargs['viewId'], kwargs.get('path'))
        view_rec = self.get_studio_view(kwargs['viewId'], kwargs['model'],
                                        kwargs['viewType'])
        group_ids = list(map(int, kwargs.pop('groupIds')))
        view_type = kwargs['viewType']
        if group_ids:
            button_properties['groups'] = ','.join(
                request.env['res.groups'].browse(
                    group_ids).get_external_id().values())

        if button_properties.get('type') == 'workflow' and not button_properties.get('name'):
            button_string = button_properties.get('string', 'button')
            button_properties['name'] = f"studio_wf_{button_string.lower().replace(' ', '_')}"

        button_string = button_properties.get('string', '')
        if view_type == 'tree' or view_type == 'list':
            # For tree views, buttons are added directly to <tree>
            form_arch = f'<xpath expr="/tree" position="{kwargs["position"]}"><button'
            for key, value in button_properties.items():
                if value:
                    form_arch += f" {key}='{value}'"
            form_arch += '/></xpath>'
        if kwargs.get("sibling"):
            if kwargs.get("item_type") == "normal":
                existing_field_name = kwargs['field_info']['name']
                button_xml = f"<button"
                for key, value in button_properties.items():
                    if value:
                        button_xml += f" {key}='{value}'"

                # Add the span element inside the button
                button_xml += f" colspan='2'><span cy-xpath='{kwargs.get('path')}/span'>{button_string}</span></button>"

                form_arch = f'''
                    <xpath expr="/{kwargs["path"]}" position="replace">
                        <label for="{existing_field_name}"/>
                        <div class="o_row">
                            <field name="{existing_field_name}"/>
                            {button_xml}
                        </div>
                    </xpath>
                '''
            else:
                button_xml = f"<button"
                for key, value in button_properties.items():
                    if value:
                        button_xml += f" {key}='{value}'"

                # Add the span element inside the button
                button_xml += f" colspan='2'><span cy-xpath='{kwargs.get('path')}/span'>{button_string}</span></button>"

                form_arch = f'''
                    <xpath expr="/{kwargs["path"]}" position="inside">
                        {button_xml}
                    </xpath>
                '''
        else:
            # Non-sibling case
            form_arch = f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}"><button'
            for key, value in button_properties.items():
                if value:
                    form_arch += f" {key}='{value}'"
            form_arch += " colspan='2'/> </xpath>"
        form_node = etree.fromstring(view_rec.arch_base)
        new_button = kwargs.get('newHeader')
        if new_button:
            if new_button == "/form/":
                new_button = "/form"
                position = "inside"
            else:
                position = "before"
            header_arch = f'<xpath expr="/{new_button}" position="{position}"><header/></xpath> '
            form_node.append(etree.fromstring(header_arch))
        form_node.append(etree.fromstring(form_arch))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True,
                                            encoding='unicode')
        return form_arch

    @route('/cyllo_studio/update/button_item', type='json', auth="user", csrf=False)
    def update_button_item(self, kwargs, button_properties):
        """
            Updates the properties of an existing button in an Odoo view.

            Parameters:
                kwargs (dict): A dictionary containing:
                    - path (str): The XPath to the button element.
                    - viewId (int): The ID of the view.
                    - model (str): The model name.
                    - viewType (str): The view type.
                    - spanxpath (str, optional): The XPath to the button's inner span element.
                    - groupIds (list, optional): A list of group IDs to update.
                button_properties (dict): A dictionary of new attribute values for the button.

            Returns:
                str: The combined XML patch string used for the update.
            """
        self.is_studio_user()
        original_path = kwargs['path']

        normalized_path = original_path

        if original_path.endswith('/i'):
            normalized_path = original_path.rsplit('/span/i', 1)[0]

        if kwargs['viewType'] == 'list':
            kwargs['viewType'] = 'tree'

        group_ids = list(map(int, kwargs.pop('groupIds')))
        if group_ids:
            button_properties['groups'] = ','.join(
                request.env['res.groups'].browse(group_ids).get_external_id().values()
            )
        else:
            button_properties['groups'] = ""

        if button_properties.get('type') == 'workflow' and not button_properties.get('name'):
            button_string = button_properties.get('string', 'button')
            button_properties['name'] = f"studio_wf_{button_string.lower().replace(' ', '_')}"

        xpath_patches = []

        attr_patch = f"""<xpath expr="/{normalized_path}" position="attributes">"""

        for key, value in button_properties.items():
            if key in {'invisible', 'string'} and key not in {'name', 'type'}:
                attr_patch += f"<attribute name='{key}'>{escape(value)}</attribute>"
            else:
                attr_patch += f"<attribute name='{key}'>{value}</attribute>"
        attr_patch += "</xpath>"
        xpath_patches.append(attr_patch)

        # --- Special case for span text update
        if kwargs['spanxpath'] and 'string' in button_properties:
            span_text_patch = f"""
                <xpath expr="/{kwargs['spanxpath']}" position="replace">
                    <span cy-xpath="/{kwargs['spanxpath']}">{escape(button_properties['string'])}</span>
                </xpath>
            """
            xpath_patches.append(span_text_patch)

        # --- Combine and wrap with <data>
        final_patch_xml = f"<data>{''.join(xpath_patches)}</data>"

        # Apply patches to view arch
        view_rec = self.get_studio_view(kwargs['viewId'], kwargs['model'], kwargs['viewType'])
        form_node = etree.fromstring(view_rec.arch_base)

        patch_node = etree.fromstring(final_patch_xml)
        for child in patch_node:
            form_node.append(child)

        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return ''.join(xpath_patches)

    # ----------------------------------Newly added function----------------------

    @route('/cyllo_studio/delete/component', type="json", auth="user", csrf=False)
    def delete_component(self, kwargs):
        """
            Deletes a component from an Odoo view by replacing it with an empty string.

            Parameters:
                kwargs (dict): A dictionary containing:
                    - view_id (int): The ID of the view.
                    - model (str): The model name.
                    - viewType (str): The view type.
                    - path (str): The XPath to the component to be deleted.

            Returns:
                str: The XML patch string used for deletion.
            """
        self.is_studio_user()
        view_id = kwargs.get('view_id')
        model = kwargs.get('model')
        view_type = kwargs.get('viewType')
        path = kwargs.get('path')
        view = request.env["ir.ui.view"].sudo()
        if not kwargs["view_id"]:
            kwargs["view_id"] = view.default_view(kwargs['model'], "form")
        form_arch_base = f'''<xpath expr="{kwargs['path']}" position="attributes">
                <attribute name="invisible">1</attribute>
                <attribute name="class" add="cy-studio-hidden" separator=" "/>
            </xpath>'''
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/delete/button', auth="user", csrf=False, type='json')
    def delete_button(self, kwargs):
        """
            Deletes a button from an Odoo view.

            Parameters:
                kwargs (dict): A dictionary containing:
                    - view_id (int): The ID of the view.
                    - model (str): The model name.
                    - viewType (str): The view type.
                    - path (str): The XPath to the button to be deleted.

            Returns:
                str: The XML patch string used for deletion.
        """
        self.is_studio_user()
        view_arch = f'''<xpath expr="/{kwargs['path']}" position="replace"/>'''
        view_rec = self.get_studio_view(kwargs['view_id'], kwargs['model'], kwargs['viewType'])
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return view_arch

    @route('/cyllo_studio/move/button', type="json", auth="user",
           csrf=False)
    def move_button(self, kwargs):
        """
        Moves a button within a view by repositioning its XML element.

        Parameters:
            kwargs (dict): A dictionary containing:
                - view_id (int): The ID of the view.
                - model (str): The model name.
                - view_type (str): The view type.
                - path (str): The XPath of the target container where the button will be moved.
                - position (str): The position within the target path (e.g., 'inside', 'before', 'after').
                - buttonPath (str): The XPath of the button to be moved.

        Returns:
            str: The XML patch string used to move the button.
        """
        self.is_studio_user()
        form_arch_base = f'<xpath expr="/{kwargs["path"]}" position="{kwargs["position"]}">' \
                         f'<xpath expr="/{kwargs["buttonPath"]}" position="move"/>' \
                         '</xpath>'
        view_rec = self.get_studio_view(kwargs["view_id"], kwargs["model"], kwargs["view_type"])
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    ##-------------------------------------------------------------------------------------------

    # --------------------------StatusBar functionality ----------------------------------------------------

    @route('/cyllo_studio/add/statusbar', type="json", auth="user",
           csrf=False)
    def add_statusbar(self, args, kwargs):
        """
        Adds a new status bar to a form view.

        Parameters:
            args (dict): A dictionary containing:
                - is_new (bool): True if a new selection field needs to be created.
                - model (str): The model name.
                - field (str): The name of the field to be created or used.
                - label (str): The label for the new field.
                - path (str): The XPath of the target element.
                - view_id (int): The ID of the view.
                - view_type (str): The view type.
                - header (str, optional): The path to a new header element.
            kwargs (dict): A dictionary of status bar properties:
                - values (list): A list of selection values.
                - clickable (bool): True to make the status bar clickable.
                - foldField (str): The field name for folding the status bar.
                - statusbarVisible (str): Comma-separated list of visible status values.
                - invisible (str): An invisible expression.
                - group_ids (list): A list of group IDs.
                - defaultValue (str): The default value for the field.

        Returns:
            str: The XML patch string used to add the status bar.
        """
        self.is_studio_user()
        if args['is_new']:
            model_id = request.env['ir.model']._get_id(args['model'])
            request.env['ir.model.fields'].create({
                'name': args['field'],
                'field_description': args['label'],
                'ttype': 'selection',
                'selection_ids': [
                    Command.create({
                        'value': str(element).lower().strip(),
                        'name': str(element).strip(),
                        'sequence': idx
                    })
                    for idx, element in enumerate(kwargs.get('values', []))
                ],
                'model_id': model_id,
            })
        form_arch_base = f'''<xpath expr="/{args['path']}" position="inside">
                               <field name="{args['field']}" widget="statusbar" '''
        options = {}
        if kwargs['clickable']:
            options['clickable'] = kwargs['clickable']
        if kwargs['foldField']:
            options['fold_field'] = kwargs['foldField']
        if options:
            form_arch_base += f'options="{options}" '

        if kwargs['statusbarVisible']:
            form_arch_base += 'statusbar_visible="{}" '.format(re.sub(r",\s+", ",", kwargs["statusbarVisible"]))

        if kwargs['invisible']:
            form_arch_base += f"invisible='{kwargs['invisible']}' "

        if kwargs['group_ids']:
            group_ids = list(map(int, kwargs['group_ids']))
            groups = ','.join(request.env['res.groups'].browse(group_ids).get_external_id().values())
            form_arch_base += f'groups="{groups}" '

        if kwargs['defaultValue']:
            field_id = request.env['ir.model.fields'].search(
                [('name', '=', args['field']), ('model', '=', args['model'])], limit=1)
            request.env['ir.default'].sudo().create(
                {'field_id': field_id.id, 'json_value': f'"{kwargs["defaultValue"]}"'})

        form_arch_base += '/></xpath>'
        view_rec = self.get_studio_view(args['view_id'], args['model'], args['view_type'])
        form_node = etree.fromstring(view_rec.arch_base)
        header_arch = self.create_header(args.get('header', None))
        if header_arch:
            form_node.append(etree.fromstring(header_arch))
        form_node.append(etree.fromstring(form_arch_base))

        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')

        return form_arch_base

    ##-------------------------------------------------------------------------------------------

    @route('/cyllo_studio/add/avatar', type="json", auth="user",
           csrf=False)
    def add_avatar(self, path, is_new, field, model, view_id, view_type):
        """
            Adds an avatar field (image widget with 'oe_avatar' class) to a form view.

            Parameters:
                path (str): The XPath to the target element where the avatar will be added.
                is_new (bool): True to create a new binary field; False to use an existing one.
                field (dict): A dictionary containing 'name' and 'label' of the field.
                model (str): The model name.
                view_id (int): The ID of the view.
                view_type (str): The view type (e.g., 'form').

            Returns:
                str: The XML patch string used to add the avatar field.
        """
        self.is_studio_user()
        if is_new:
            model_id = request.env['ir.model']._get_id(model)

            field = request.env['ir.model.fields'].create({
                'name': field['name'],
                'field_description': field['label'],
                'ttype': 'binary',
                'model_id': model_id,
            })
            form_arch_base = f'''<xpath expr="{path}" position="before">
                                             <field name="{field['name']}" widget="image" class="oe_avatar"/>
                                             </xpath>'''
        else:
            form_arch_base = f'''<xpath expr="{path}" position="before">
                                 <field name="{field['name']}" widget="image" class="oe_avatar"/>
                                 </xpath>'''

        view_rec = self.get_studio_view(view_id, model, view_type)

        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/FieldPositionMove', auth="user", csrf=False,
           type='json')
    def field_position_move(self, args):
        """
        Moves one or more fields to a new position within a form view.

        Parameters:
            args (dict): A dictionary containing:
                - view_id (int): The ID of the view.
                - model (str): The model name.
                - path (str): The XPath of the target container.
                - position (str): The position within the target container.
                - has_multipath (bool): True if multiple fields need to be moved together.
                - item_path (dict/str): The XPath(s) of the field(s) to be moved.
                - direction (str, optional): The direction of the move ('up' or 'down').
                - inSource (bool, optional): Indicates if the move is within the same source.

        Returns:
            dict: A dictionary containing the updated view information, including the number of items and the XML patches.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(args['view_id'], args['model'], 'form')
        form_arch_base = f'<xpath expr="/{args["path"]}" position="{args["position"]}">'
        if args['has_multipath']:
            first_path = args['item_path']["first_path"]
            second_path = args['item_path']["second_path"]

            if (args["direction"] == "down" or not args["inSource"]) and self.get_last_element_from_path(
                    first_path) == self.get_last_element_from_path(second_path):
                form_arch_base += f'<xpath expr="/{first_path}" position="move"/>' * 2
            else:
                form_arch_base += f'<xpath expr="/{first_path}" position="move"/>'
                form_arch_base += f'<xpath expr="/{second_path}" position="move"/>'
        else:
            form_arch_base += f'<xpath expr="/{args["item_path"]}" position="move"/>'

        form_arch_base += '</xpath>'
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        root = ET.fromstring(view_rec.arch_base)
        item_count = len(root.findall('.//xpath'))
        return {
            'ItemCount': item_count,
            'viewId': view_rec.id,
            'FormArch': form_arch_base,
            'ViewArch': view_rec.arch_base,
        }

    @route('/cyllo_studio/find/groups', type="json", auth="user",
           csrf=False)
    def find_group_ids(self, groups):
        """
        Finds the database IDs for a comma-separated string of Odoo group external IDs.

        Parameters:
            groups (str): A comma-separated string of Odoo group external IDs.

        Returns:
            list: A list of integer IDs for the specified groups.
        """
        self.is_studio_user()
        groups = groups.split(',')
        groups = [item.strip() for item in groups]
        return [request.env.ref(i).id for i in groups]

    # -------------------------Filter functionality---------------------------------------------------

    @route('/cyllo_studio/search/add/filter', type="json", auth="user",
           csrf=False)
    def add_filter(self, sibling_path, properties, view_id, model):
        """
        Adds a new filter to a search view.

        Parameters:
            sibling_path (str): The XPath of the sibling element to add the filter after.
            properties (dict): A dictionary of filter properties (e.g., 'string', 'domain', 'groupIds').
            view_id (int): The ID of the search view.
            model (str): The model name.

        Returns:
            str: The XML patch string used to add the filter.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        properties['name'] = properties['string'].lower().replace(' ', '_') + str(uuid.uuid4())[:4]

        if properties['groupIds']:
            group_ids = list(map(int, properties.pop('groupIds')))
            groups = ','.join(request.env['res.groups'].browse(
                group_ids).get_external_id().values())
            properties['groups'] = groups
        if 'groupIds' in properties:
            properties.pop('groupIds')

        position = "inside" if sibling_path == "/search" else "after"
        search_arch = f'''
            <xpath expr="/{sibling_path}" position="{position}">
                <filter '''
        for key, value in properties.items():
            if key in ['domain', 'name', 'string']:
                value = escape(value)
            search_arch += f"{key}='{value}' "
        search_arch += '''/> 
            </xpath>'''
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))

        view_rec.arch_base = etree.tostring(search_node, pretty_print=True, encoding='unicode')
        return search_arch

    # --------------------------search functionality--------------------------------------------------

    @route('/cyllo_studio/add/search_field', type="json", auth="user",
           csrf=False)
    def add_search_field(self, path, view_id, model, properties):
        """
        Adds a new field to a search view.

        Parameters:
            path (str): The XPath of the sibling element to add the field after.
            view_id (int): The ID of the search view.
            model (str): The model name.
            properties (dict): A dictionary of field properties (e.g., 'field', 'string', 'invisible', 'groupIds').

        Returns:
            str: The XML patch string used to add the search field.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        position = "inside" if path == "/search" else "after"

        search_arch = f'''
            <xpath expr="/{path}" position="{position}">
                <field name="{properties["field"]}" 
                invisible="{properties['invisible']}"'''
        if properties['string']:
            search_arch += f' string="{escape(properties["string"])}" '
        if properties['groupIds']:
            group_ids = list(map(int, properties['groupIds']))
            groups = ','.join(request.env['res.groups'].browse(
                group_ids).get_external_id().values())
            search_arch += f' groups="{groups}" '
        else:
            search_arch += ' groups=""'
        search_arch += ' /> </xpath>'
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = etree.tostring(search_node, pretty_print=True, encoding='unicode')
        return search_arch

    # -----------------------Add separator--------------------------------------------------------

    @route('/cyllo_studio/search/add/separator', type="json", auth="user",
           csrf=False)
    def add_separator(self, sibling_path, view_id, model):
        """
        Adds a <separator> element to a search view.

        Parameters:
            sibling_path (str): The XPath of the sibling element to add the separator after.
            view_id (int): The ID of the search view.
            model (str): The model name.

        Returns:
            str: The XML patch string used to add the separator.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        search_arch = f'''<xpath expr="{sibling_path}" position="after">
                <separator/>
            </xpath>'''
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = etree.tostring(search_node, pretty_print=True, encoding='unicode')
        return search_arch

    # -------------------------Groupby functionality--------------------------------------------------

    @route('/cyllo_studio/add/group_by', type="json", auth="user",
           csrf=False)
    def add_group_by(self, path, view_id, model, properties):
        """
        Adds a new 'group by' filter to a search view.

        Parameters:
            path (str): The XPath of the sibling element or parent container.
            view_id (int): The ID of the search view.
            model (str): The model name.
            properties (dict): A dictionary of properties for the group-by filter (e.g., 'field', 'string', 'invisible', 'groupIds').

        Returns:
            str: The XML patch string used to add the group-by filter.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        name = properties['field'].lower().replace(' ', '_') + str(uuid.uuid4())[:4]
        context = {
            'group_by': properties['field'], }
        position = "inside" if path == "/search" else "after"
        search_arch = f'''
            <xpath expr="/{path}" position="{position}">
                <filter name="{name}" context="{context}" 
                invisible="{properties['invisible']}"'''
        if properties['string']:
            search_arch += f' string="{escape(properties["string"])}" '
        if properties['groupIds']:
            group_ids = list(map(int, properties['groupIds']))
            groups = ','.join(request.env['res.groups'].browse(
                group_ids).get_external_id().values())
            search_arch += f' groups="{groups}" '
        else:
            search_arch += ' groups=""'
        search_arch += ' /> </xpath>'
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = etree.tostring(search_node, pretty_print=True, encoding='unicode')
        return search_arch

    # --------------------------pivot functionality ----------------------------------------------------

    @route('/cyllo_studio/pivot/remove_element', type="json", auth="user",
           csrf=False)
    def remove_pivot_element(self, view_id, view_type, model, path):
        """
        Removes an element from a pivot view.

        Parameters:
            view_id (int): The ID of the pivot view.
            view_type (str): The view type (e.g., 'pivot').
            model (str): The model name.
            path (str): The XPath of the element to be removed.

        Returns:
            str: The XML patch string used for deletion.
        """
        self.is_studio_user()
        pivot_arch_base = f'<xpath expr="/{path}" position="replace"/>'
        view_rec = self.get_studio_view(view_id, model, view_type)
        pivot_node = etree.fromstring(view_rec.arch_base)
        pivot_node.append(etree.fromstring(pivot_arch_base))
        view_rec.arch_base = etree.tostring(pivot_node, pretty_print=True, encoding='unicode')
        return pivot_arch_base

    ##-------------------------------------------------------------------------------------------

    @route('/cyllo_studio/graph/edit_element', type="json", auth="user", csrf=False)
    def edit_graph_element(self, view_id, view_type, model, position, name, item_type, interval, **kw):
        """
        Edits an element (field or attribute) in a graph view.

        Parameters:
            view_id (int): The ID of the graph view.
            view_type (str): The view type (e.g., 'graph').
            model (str): The model name.
            position (str): The position for the new element, either 'inside' for fields or 'attributes' for graph attributes.
            name (str): The name of the field or attribute.
            item_type (str): The type of the graph item ('measure', 'row', 'col') or the attribute value.
            interval (str): The interval for the field (e.g., 'day', 'month').
            **kw: Additional keyword arguments.

        Returns:
            str: The XML patch string used to edit the element.
        """
        self.is_studio_user()
        graph_arch_base = f'''<xpath expr="//graph" position="{position}">'''
        if position == 'inside':
            graph_arch_base += f'''<field name="{name}" '''
            if item_type:
                graph_arch_base += f'''type="{item_type}"'''
            if interval:
                graph_arch_base += f'''interval="{interval}"'''
            graph_arch_base += '/></xpath>'
        else:
            graph_arch_base += f'''<attribute name="{name}">{item_type}</attribute></xpath>'''

        view_rec = self.get_studio_view(view_id, model, view_type)
        graph_node = etree.fromstring(view_rec.arch_base)

        existing_element = graph_node.xpath(
            f"//field[@type='{item_type}']" if position == 'inside' else f"//attribute[@name='{name}']"
        )

        if existing_element:

            parent_node = existing_element[0].getparent()

            parent_node.remove(existing_element[0])

            # Remove the parent xpath node if it becomes empty
            if len(parent_node) == 0:
                grandparent_node = parent_node.getparent()
                if grandparent_node is not None:
                    grandparent_node.remove(parent_node)

        graph_node.append(etree.fromstring(graph_arch_base))
        view_rec.arch_base = etree.tostring(graph_node, pretty_print=True, encoding='unicode')
        return graph_arch_base

    @route('/cyllo_studio/graph/remove_element', type="json", auth="user",
           csrf=False)
    def remove_graph_element(self, view_id, view_type, model, field, **kwargs):
        """
            Removes a field element from a graph view.

            Parameters:
                view_id (int): The ID of the graph view.
                view_type (str): The view type (e.g., 'graph').
                model (str): The model name.
                field (str): The name of the field to be removed, potentially with an interval.
                **kwargs: Additional keyword arguments.

            Returns:
                str: The XML patch string used for deletion.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        graph_node = etree.fromstring(view_rec.arch_base)

        if ':' in field:
            key, value = field.split(':', 1)
            # Use the key for further processing
            field_to_use = key
        else:
            field_to_use = field

        existing_element = f'''<xpath expr="field[@name='{field_to_use}']" position="replace"/>'''
        graph_node.append(etree.fromstring(existing_element))
        view_rec.arch_base = etree.tostring(graph_node, pretty_print=True, encoding='unicode')
        return existing_element

    @route('/cyllo_studio/graph/add_view', type="json", auth="user", csrf=False)
    def add_graph_view(self, arch, model):
        """
            Creates and saves a new graph view.

            Parameters:
                arch (str): The XML string of the graph view.
                model (str): The model name for the new view.

            Returns:
                int: The ID of the newly created graph view record.
            """
        self.is_studio_user()
        model_id = request.env['ir.model']._get_id(model)
        tree = etree.fromstring(arch)

        # Function to recursively remove 'cy-xpath' attributes
        def remove_cy_xpath_attributes(element):
            if 'cy-xpath' in element.attrib:
                del element.attrib['cy-xpath']
            for child in element:
                remove_cy_xpath_attributes(child)

        remove_cy_xpath_attributes(tree)
        arch = etree.tostring(tree, pretty_print=True).decode('utf-8')
        graph_view = request.env['ir.ui.view'].sudo().create({
            'name': f"Cy_Studio_Graph_{model.replace('.', '_')}_{str(uuid.uuid4())[:8]}",
            'type': 'graph',
            'model': model,
            'model_id': model_id,
            'arch': arch,
        })
        request.env['ir.model.data']._update_xmlids([{
            'xml_id': f"cy_studio.{model.replace('.', '_')}_graph_view_{str(uuid.uuid4())[:8]}",
            'record': graph_view,
        }])
        return graph_view.id

    # --------------------------------calendar view------------------------------------------------------

    @route('/cyllo_studio/calendar/remove/item', type="json", auth="user",
           csrf=False)
    def remove_calendar_item(self, view_id, model, path):
        """
            Removes a field from a calendar view.

            Parameters:
                view_id (int): The ID of the calendar view.
                model (str): The model name.
                path (str): The XPath of the element to be removed.

            Returns:
                str: The XML patch string used for deletion.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'calendar')
        calendar_arch = f'''
                   <xpath expr="/{path}" position="replace"/>
                   '''
        calendar_node = etree.fromstring(view_rec.arch_base)
        calendar_node.append(etree.fromstring(calendar_arch))
        view_rec.arch_base = (etree.tostring(calendar_node, pretty_print=True, encoding='unicode'))
        return calendar_arch

    @route('/cyllo_studio/calendar/save/item', type="json", auth="user",
           csrf=False)
    def save_calendar_item(self, view_id, model, path, position, properties,
                           extra_data):
        """
            Adds a new field element to a calendar view.

            Parameters:
                view_id (int): The ID of the calendar view.
                model (str): The model name.
                path (str): The XPath of the parent container.
                position (str): The position within the parent container.
                properties (dict): A dictionary of properties for the new field.
                extra_data (dict): A dictionary of additional data for creating invisible fields.

            Returns:
                str: The XML patch string used to add the field.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'calendar')
        not_present_fields = self.create_invisible(
            [{**properties, **extra_data}])
        calendar_arch = f'''
          <xpath expr="/{path}" position="{position}">
                <field '''
        for name, value in properties.items():
            if name == 'invisible':
                calendar_arch += f"{name}='{escape(value)}' "
            else:
                calendar_arch += f"{name}='{value}' "
        calendar_arch += f'''/>{not_present_fields}</xpath>'''
        calendar_node = etree.fromstring(view_rec.arch_base)
        calendar_node.append(etree.fromstring(calendar_arch))
        view_rec.arch_base = (etree.tostring(calendar_node, pretty_print=True,
                                             encoding='unicode'))
        return calendar_arch

    @route('/cyllo_studio/calendar/move/item', type="json", auth="user",
           csrf=False)
    def move_calendar_item(self, view_id, model, path, position, sibling_path):
        """
            Moves an item within a calendar view.

            Parameters:
                view_id (int): The ID of the calendar view.
                model (str): The model name.
                path (str): The XPath of the item to be moved.
                position (str): The position relative to the sibling path.
                sibling_path (str): The XPath of the sibling element.

            Returns:
                str: The XML patch string used to move the item.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'calendar')
        calendar_arch = f'''
               <xpath expr="/{sibling_path}" position="{position}">
                   <xpath expr="/{path}" position="move"/>
               </xpath>'''
        calendar_node = etree.fromstring(view_rec.arch_base)
        calendar_node.append(etree.fromstring(calendar_arch))
        view_rec.arch_base = (etree.tostring(calendar_node, pretty_print=True,
                                             encoding='unicode'))
        return calendar_arch

    @route('/cyllo_studio/calendar/update/attributes', type='json', auth="user", csrf=False)
    def update_calendar_attributes(self, name, value, view_id, model):
        """
            Updates the attributes of a calendar view.

            Parameters:
                name (str): The name of the attribute to update.
                value (str): The new value for the attribute.
                view_id (int): The ID of the calendar view.
                model (str): The model name.

            Returns:
                str: The XML patch string used to update the attributes.
            """
        self.is_studio_user()
        if name == 'quick_create_view_id':
            calendar_arch = f'''
                        <xpath expr="//calendar" position="attributes">
                            <attribute name='quick_create'>true</attribute>
                            <attribute name='{name}'>{value}</attribute>
                        </xpath>
                        '''
        else:
            calendar_arch = f'''
                <xpath expr="//calendar" position="attributes">
                    <attribute name='{name}'>{value}</attribute>
                </xpath>
                '''
        view_rec = self.get_studio_view(view_id, model, 'calendar')
        calendar_node = etree.fromstring(view_rec.arch_base)
        calendar_node.append(etree.fromstring(calendar_arch))
        view_rec.arch_base = etree.tostring(calendar_node, pretty_print=True, encoding='unicode')
        return calendar_arch

    # -----------------------------------------Activity View----------------------------------------------------

    @route('/cyllo_studio/add/activity/field', type="json", auth="user",
           csrf=False)
    def add_activity_field(self, view_id, view_type, model, path, name):
        """
            Adds a field to an activity view.

            Parameters:
                view_id (int): The ID of the activity view.
                view_type (str): The view type (e.g., 'activity').
                model (str): The model name.
                path (str): The XPath to the container element.
                name (str): The name of the field to add.

            Returns:
                str: The combined XML patch string used to add the field and update the class.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, view_type)
        activity_node = etree.fromstring(view_rec.arch_base)
        activity_arch = f'''
            <xpath expr="{path}" position="inside">
                <field name="{name}" display="full"/>
            </xpath>'''
        activity_node.append(etree.fromstring(activity_arch))
        activity_arch_class = f'''
             <xpath expr="//div[@t-name='activity-box']" position="attributes">
                <attribute name="class">d-block</attribute>
            </xpath>'''
        activity_node.append(etree.fromstring(activity_arch_class))
        view_rec.arch_base = etree.tostring(activity_node, pretty_print=True, encoding='unicode')
        activity_arch += activity_arch_class
        return activity_arch

    @route('/cyllo_studio/form/add/activity_view', type="json", auth="user", csrf=False)
    def add_activity_view(self, arch, model):
        """
            Creates and saves a new activity view.

            Parameters:
                arch (str): The XML string of the activity view.
                model (str): The model name for the new view.
            """
        self.is_studio_user()
        model_id = request.env['ir.model']._get_id(model)
        activity = etree.fromstring(arch)

        def remove_custom_attributes(element):
            # List of attributes to remove
            attributes_to_remove = ['cy-xpath']

            # Iterate through the attributes and remove if present
            for attr in attributes_to_remove:
                if attr in element.attrib:
                    del element.attrib[attr]

            # Recursively call the function for each child element
            for child in element:
                remove_custom_attributes(child)

        remove_custom_attributes(activity)

        arch = etree.tostring(activity, pretty_print=True).decode('utf-8')
        activity_view = request.env['ir.ui.view'].sudo().create({
            'name': f"Cy_Studio_activity_{model.replace('.', '_')}_{str(uuid.uuid4())[:8]}",
            'type': 'activity',
            'model': model,
            'model_id': model_id,
            'arch': arch,
        })

        request.env['ir.model.data']._update_xmlids([{
            'xml_id': f"cy_studio.{model.replace('.', '_')}_activity_view_{str(uuid.uuid4())[:8]}",
            'record': activity_view,
        }])

    @route('/cyllo_studio/activity/move/field', type="json", auth="user",
           csrf=False)
    def move_activity_field(self, view_id, model, path, position, sibling_path, parent):
        """
            Moves a field within an activity view.

            Parameters:
                view_id (int): The ID of the activity view.
                model (str): The model name.
                path (str): The XPath of the field to be moved.
                position (str): The position relative to the sibling or parent.
                sibling_path (str): The XPath of the sibling element.
                parent (str): The XPath of the parent container if there is no sibling.

            Returns:
                str: The XML patch string used to move the field.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'activity')
        activity_arch = ''
        if sibling_path:
            activity_arch += f'''
                   <xpath expr="/{sibling_path}" position="{position}">
                           <xpath expr="/{path}" position="move"/>
                       </xpath>'''
        else:
            activity_arch += f'''
                                   <xpath expr="/{parent}" position="inside">
                       <xpath expr="/{path}" position="move"/>
                   </xpath>'''
        activity_node = etree.fromstring(view_rec.arch_base)
        activity_node.append(etree.fromstring(activity_arch))
        view_rec.arch_base = (etree.tostring(activity_node, pretty_print=True, encoding='unicode'))
        return activity_arch

    @route('/cyllo_studio/activity/save/field', type="json", auth="user",
           csrf=False)
    def save_activity_field(self, view_id, model, path, fieldDisplay, fieldBold, fieldMuted):
        """
            Updates the attributes and style of an existing field in an activity view.

            Parameters:
                view_id (int): The ID of the activity view.
                model (str): The model name.
                path (str): The XPath of the field to be updated.
                fieldDisplay (str): The display type for the field (e.g., 'full').
                fieldBold (bool): True to make the field text bold.
                fieldMuted (bool): True to mute the field text.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'activity')
        view_arch = f'''
                           <xpath expr="/{path}" position="attributes">
                                <attribute name="display">{fieldDisplay}</attribute>
                                <attribute name="style">{'font-weight:bold !important;' if fieldBold else ''}</attribute>
                                <attribute name="bold">{'True' if fieldBold else 'False'}</attribute>
                                <attribute name="muted">{fieldMuted}</attribute>
                           </xpath>
                       '''
        view_node = etree.fromstring(view_rec.arch_base)
        view_node.append(etree.fromstring(view_arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))
        return view_arch

    @route('/cyllo_studio/check/chatter', type="json", auth="user", csrf=False)
    def check_chatter(self, model):
        """
            Checks if a model has chatter functionality enabled.

            Parameters:
                model (str): The name of the model to check.

            Returns:
                bool: True if the model has mail thread or activity functionality, False otherwise.
            """
        self.is_studio_user()
        model_id = request.env['ir.model']._get_id(model)
        model_rec = request.env['ir.model'].browse(model_id)
        if model_rec.state == 'manual':
            model_rec.is_mail_thread = True
            model_rec.is_mail_activity = True
            return True
        else:
            if model_rec.is_mail_thread:
                return True
            return False

    @route('/cyllo_studio/add_remove/chatter', type="json", auth="user",
           csrf=False)
    def add_remove_chatter(self, model, view_id, path, view_type, position):
        """
            Adds a chatter component to a form view.

            Parameters:
                model (str): The name of the model.
                view_id (int): The ID of the form view.
                path (str): The XPath where the chatter should be added.
                view_type (str): The type of the view (e.g., 'form').
                position (str): The position within the path (e.g., 'inside').

            Returns:
                str: The XML patch used to add the chatter.
            """
        self.is_studio_user()
        form_arch_base = f'<xpath expr="/{path}" position="{position}">'
        if position == 'inside':
            model_id = request.env['ir.model']._get_id(model)
            model_rec = request.env['ir.model'].browse(model_id)

            # Enable mail thread and activity on the model so the backend supports the chatter
            if not model_rec.is_mail_thread:
                model_rec.write({'is_mail_thread': True})
            if not model_rec.is_mail_activity:
                model_rec.write({'is_mail_activity': True})

            form_arch_base += '<div class="oe_chatter">'
            if model_rec.is_mail_thread:
                form_arch_base += '''
                                           <field name="message_follower_ids"/>
                                           <field name="message_ids"/>'''
            if model_rec.is_mail_activity:
                form_arch_base += '<field name="activity_ids"/>'
            form_arch_base += "</div>"
        form_arch_base += '</xpath>'
        view_rec = self.get_studio_view(view_id, model, view_type)
        form_node = etree.fromstring(view_rec.arch_base)
        form_node.append(etree.fromstring(form_arch_base))
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return form_arch_base

    @route('/cyllo_studio/activity/remove/field', type="json", auth="user",
           csrf=False)
    def remove_activity_field(self, view_id, model, path, field_name):
        """
            Removes a field from an activity view.

            Parameters:
                view_id (int): The ID of the activity view.
                model (str): The model name.
                path (str): The XPath to the field to be removed.
                field_name (str): The name of the field.

            Returns:
                str: The XML patch used for deletion.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'activity')
        activity_node = etree.fromstring(view_rec.arch_base)

        activity_arch = f'''
                       <xpath expr="/{path}" position="replace"/>
                       '''
        activity_node.append(etree.fromstring(activity_arch))
        activity_arch_2 = ''
        if field_name:
            activity_arch_2 = f'''
                                      <xpath expr="//templates" position="before">
                                           <field name="{field_name}"/>
                                      </xpath>
                                      '''
            activity_node.append(etree.fromstring(activity_arch_2))
        combined_arch = activity_arch + activity_arch_2
        view_rec.arch_base = (etree.tostring(activity_node, pretty_print=True, encoding='unicode'))
        return combined_arch

    # -----------------------------------------Undo Redo----------------------------------------------------

    @route('/cyllo_studio/redo_action', type="json", auth="user", csrf=False)
    def redo_action(self, model, view_id, view_type, arch):
        """
            Applies an action by appending its XML fragment to the view's architecture.

            Parameters:
                model (str): The model name.
                view_id (int): The ID of the view.
                view_type (str): The view type (e.g., 'form').
                arch (str): The XML fragment representing the action to be redone.

            Returns:
                None: The function modifies the view directly.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(int(view_id), model, view_type)
        xpath_count = arch.count("<xpath")
        xpath_close_count = arch.count('</xpath>') or arch.count("/>")
        view_node = etree.fromstring(view_rec.arch_base)
        if '//form' not in arch and (arch.count('</xpath>') == 2 or arch.count('/>') == 2):

            split_string = arch.split("<xpath")
            xpath1 = "<xpath " + split_string[1].strip()
            xpath2 = "<xpath " + split_string[2].strip()
            view_node.append(etree.fromstring(xpath1))
            view_node.append(etree.fromstring(xpath2))
        else:
            view_node.append(etree.fromstring(arch))
        view_rec.arch_base = (etree.tostring(view_node, pretty_print=True, encoding='unicode'))

    @route('/cyllo_studio/undo_action', type="json", auth="user", csrf=False)
    def undo_action(self, model, view_id, view_type, xPaths):
        """
            Reverts the last action by removing the most recent XPath from the view's XML.

            Parameters:
                model (str): The model name.
                view_id (int): The ID of the view.
                view_type (str): The view type.
                xPaths (bool): True if the last action involved multiple xpaths to be removed.

            Returns:
                None: The function modifies the view directly.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(int(view_id), model, view_type)
        root = etree.fromstring(view_rec.arch)
        xpath_elements = root.findall(".//xpath")
        if xpath_elements:
            element_to_remove = xpath_elements[-1]
            if xPaths:
                element_to_remove_second = xpath_elements[-2]
                parent = element_to_remove_second.getparent()
                if parent is not None:
                    if element_to_remove in parent:
                        parent.remove(element_to_remove)
                    if element_to_remove_second in parent:
                        parent.remove(element_to_remove_second)
                    element = etree.tostring(parent, pretty_print=True).decode("utf-8")
                    if not element.startswith("<data>"):
                        grandparent = parent.getparent()
                        if grandparent is not None:
                            grandparent.remove(parent)
            else:
                parent = element_to_remove.getparent()
                if parent is not None:
                    parent.remove(element_to_remove)
                    element = etree.tostring(parent, pretty_print=True).decode("utf-8")
                    if not element.startswith("<data>"):
                        grandparent = parent.getparent()
                        if grandparent is not None:
                            grandparent.remove(parent)
            view_rec.arch_base = (etree.tostring(root, pretty_print=True, encoding='unicode'))
        #     ------------------------ menu bar --------------------------

    @route('/cyllo_studio/move/menuitem', auth="user", csrf=False, type='json')
    def move_menu(self, args, kwargs):
        """
            Updates the sequence of top-level menu items.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): Dictionary containing 'MenuPosition' with key-value pairs of sequence and menu ID.

            Returns:
                dict: A status report of the operation.
            """
        self.is_studio_user()
        for key, value in kwargs['MenuPosition'].items():
            if isinstance(value, list):
                if not value or value[0] is None:
                    continue
                value = value[0]
            menu_value = request.env['ir.ui.menu'].browse(int(value))
            menu_value.sequence = int(key)
            menu_item_data = request.env['ir.model.data'].sudo().search([
                ('res_id', 'in', menu_value.ids),
                ('model', '=', 'ir.ui.menu')
            ])
            menu_item_data.noupdate = True
        return {
            "status": "success",
            "updated": True,
            "moved_menus": list(kwargs['MenuPosition'].values()),
        }

    @route('/cyllo_studio/move/childmenuitem', auth="user", csrf=False, type='json')
    def move_child_menu(self, args, kwargs):
        """
            Updates the properties and position of a child menu item.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing menu details like 'MenuName', 'ParentMenu', 'groups', 'ActionType', 'ActionModel', 'ActiveMenu', and 'MenuPosition'.

            Returns:
                None: The function modifies the menu directly.
            """
        self.is_studio_user()
        menu = request.env['ir.ui.menu'].browse(int(kwargs['Menu']['id']))
        menu.name = kwargs['MenuName']
        if kwargs['ParentMenu']['id'] and kwargs.get('isCreate'):
            menu.parent_id = int(kwargs['ParentMenu']['id'])
        if kwargs['groups'] or kwargs['groups'] == []:
            menu = request.env['ir.ui.menu'].browse(int(kwargs['Menu']['id']))
            if kwargs['groups'] == []:
                menu.groups_id = [Command.clear()]
            else:
                menu.groups_id = kwargs['groups']
        action_type = kwargs.get('ActionType')
        action_model = kwargs.get('ActionModel')
        if kwargs['ActionType']:
            menu = request.env['ir.ui.menu'].browse(int(kwargs['Menu']['id']))
            menu.action = f'{kwargs["ActionType"]},%d' % kwargs['ActionModel']
        elif action_type and action_type != 'false' and action_type != '':
            # Set the action
            if action_model and action_model != 'false':
                menu.action = f'{action_type},{action_model}'
            else:
                menu.action = False
        else:
            # Explicitly clear the action when ActionType is empty/false
            menu.action = False

        menu = request.env['ir.ui.menu'].browse(int(kwargs['Menu']['id']))
        menu.active = kwargs['ActiveMenu']

        for key, value in kwargs['MenuPosition'].items():
            menu_value = request.env['ir.ui.menu'].browse(int(value))
            menu_value.sequence = int(key)
            menu_item_data = request.env['ir.model.data'].sudo().search([
                ('res_id', 'in', menu_value.ids),
                ('model', '=', 'ir.ui.menu')
            ])
            menu_item_data.noupdate = True

    @route('/cyllo_studio/menuitem/confirm', auth="user", csrf=False, type='json')
    def menu_confirm(self, args, kwargs):
        """
            Creates a new menu item and its associated action, model, and views based on user input.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing details for creating the menu, action, and model.

            Returns:
                None: The function creates records directly.
            """
        # self.is_studio_admin()
        self.is_studio_user()
        if kwargs['resId']:
            model = request.env['ir.model'].browse(kwargs['resId'])
            model_action = request.env['ir.actions.act_window'].create({
                'name': kwargs['menuName'],
                'res_model': model.model,
                'view_mode': 'kanban,tree,form',
                'target': 'current'
            })
            menu_item = request.env['ir.ui.menu'].create({
                'name': kwargs['menuName'],
                'action': f"{model_action.type}, {model_action.id}",
                'parent_id': kwargs['ParentMenu'],
                'groups_id': kwargs['groups'] if kwargs['groups'] else None,
                'sequence': 110,
            })
        elif kwargs['model_name'] or kwargs['description']:
            ir_model = request.env['ir.model'].create({
                'name': kwargs['model_name'],
                'model': 'x_cyllo_' + '_'.join(kwargs['model_name'].lower().split(' ')),
                'field_id': [
                    Command.create({'name': 'x_cyllo_name', 'ttype': 'char',
                                    'field_description': kwargs['description']}),
                ]
            })
            model_action = request.env['ir.actions.act_window'].create({
                'name': kwargs['menuName'],
                'res_model': ir_model.model,
                'view_mode': 'kanban,tree,form',
                'target': 'current'
            })
            ir_model_access_user = request.env['ir.model.access'].create({
                'name': "user_access_" + '_'.join(kwargs['menuName'].lower().split(' ')),
                'model_id': ir_model.id,
                'group_id': request.env.ref('base.group_user').id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': False,
            })
            ir_model_access_administrator = request.env['ir.model.access'].create({
                'name': "admin_access_" + '_'.join(kwargs['menuName'].lower().split(' ')),
                'model_id': ir_model.id,
                'group_id': request.env.ref('base.group_system').id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': True,
            })
            form_view = request.env['ir.ui.view'].sudo().create({
                'name': 'Default_Form_' + '_'.join(kwargs['menuName'].lower().split(' ')),
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
            list_view = request.env['ir.ui.view'].sudo().create({
                'name': 'Default_List_' + '_'.join(kwargs['menuName'].lower().split(' ')),
                'type': 'tree',
                'model': ir_model.model,
                'model_id': ir_model.id,
                'arch': """
                                <tree>
                                    <field name="x_cyllo_name"/>
                                </tree>
                            """
            })
            search_view = request.env['ir.ui.view'].sudo().create({
                'name': 'Default_Search_' + '_'.join(kwargs['menuName'].lower().split(' ')),
                'type': 'search',
                'model': ir_model.model,
                'model_id': ir_model.id,
                'arch': """
                                <search>
                                    <field name="x_cyllo_name"/>
                                </search>
                            """
            })
            menu_item = request.env['ir.ui.menu'].create({
                'name': kwargs['menuName'],
                'action': f"{model_action.type}, {model_action.id}",
                'parent_id': kwargs['ParentMenu'],
                'groups_id': kwargs['groups'] if kwargs['groups'] else None,
                'sequence': 110,
                'web_icon': "",
                'web_icon_data': "",
            })
            if kwargs['IconImage'].startswith('ri'):
                menu_item.web_icon = kwargs['IconImage']
            elif kwargs['IconImage']:
                menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]
        elif kwargs['isParent']:
            menu_item = request.env['ir.ui.menu'].create({
                'name': kwargs['menuName'],
                'action': 'ir.actions.client,%d' % 148,
                'parent_id': kwargs['ParentMenu'],
                'groups_id': kwargs['groups'] if kwargs['groups'] else None,
                'sequence': 110,
                'is_studio': True,
                'web_icon': "",
                'web_icon_data': "",
            })
            if kwargs['IconImage'].startswith('ri'):
                menu_item.web_icon = kwargs['IconImage']
            elif kwargs['IconImage']:
                menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]
        else:
            menu_item = request.env['ir.ui.menu'].create({
                'name': kwargs['menuName'] if kwargs['menuName'] else None,
                'active': kwargs['ActiveMenu'],
                'action': f'{kwargs["ActionType"]},%d' % kwargs['ActionModel'] if kwargs['ActionType'] else None,
                'parent_id': kwargs['ParentMenu'] if kwargs['ParentMenu'] else None,
                'groups_id': kwargs['groups'] if kwargs['groups'] else None,
                'sequence': 999,
                'is_studio': True,
                'web_icon': "",
                'web_icon_data': "",
            })
            if kwargs['IconImage'].startswith('ri'):
                menu_item.web_icon = kwargs['IconImage']
            elif kwargs['IconImage']:
                menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]
        request.env['ir.model.data'].create({
            'name': f"menus_{kwargs['menuName'].replace(' ', '_')}_{str(uuid.uuid4())[:8]}",
            'model': 'ir.ui.menu',
            'module': 'base',
            'noupdate': 'True',
            'res_id': menu_item.id,
        })

    @route('/cyllo_studio/menuitem/delete', type='json', auth='user', csrf=False)
    def delete_menu(self, menuId):
        """
        Deletes a specific menu item by its ID, including its child menus if present.

        Parameters:
            menuId (int): The ID of the menu item to delete.

        Returns:
            dict: Result message indicating success or failure.
        """
        self.is_studio_admin()
        try:
            # Ensure valid menuId
            if not menuId:
                return {"success": False, "message": "No menu ID provided"}

            # Fetch the menu record
            menu_rec = request.env['ir.ui.menu'].sudo().browse(menuId)

            if not menu_rec.exists():
                return {"success": False, "message": f"Menu with ID {menuId} not found"}

            # Recursively unlink all child menus if any
            child_menus = request.env['ir.ui.menu'].sudo().search([('parent_id', '=', menuId)])
            if child_menus:
                child_menus.unlink()

            # Delete the menu itself
            menu_rec.unlink()

            return {"success": True, "message": f"Menu (ID: {menuId}) deleted successfully"}

        except Exception as e:
            return {"success": False, "message": f"Error deleting menu: {str(e)}"}

    # -----------------------------------------New App----------------------------------------------------
    @route('/cyllo_studio/app/update', auth="user", csrf=False,
           type='json')
    def app_update(self, args, kwargs):
        """
            Updates an existing application menu item and its associated views and action.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing 'appname', 'IconImage', view preferences, and record IDs.

            Returns:
                tuple: A tuple of updated record IDs and information.
            """
        self.is_studio_admin()
        module_id = kwargs['state'].get('module_id')
        position = kwargs['state'].get('position')

        sequence = self.set_app_sequence(module_id, position)

        menu_item = request.env['ir.ui.menu'].browse(kwargs['menu_id'])
        menu_item.write({
            'name': kwargs['appname'],
            'web_icon_data': "",
            'web_icon': "",
            'groups_id': kwargs['state']['group_ids'],
            'sequence': sequence,
            'is_studio': True,
        })

        if kwargs['IconImage'].startswith('ri'):
            menu_item.web_icon = kwargs['IconImage']
        elif kwargs['IconImage']:
            menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]

        views = []
        view_types = [kwargs['set_default_view']]
        editable = False
        for view_type in kwargs['default_view'].values():
            if view_type not in view_types:
                view_types.append(view_type)

        if 'kanban' in view_types and len(view_types) == 1:
            view_types.append('form')

        if (len(view_types) == 1 and view_types[0] == 'tree') \
                or (
                len(view_types) == 2 and 'tree' in view_types and 'kanban' in view_types):
            editable = True

        model_id = request.env['ir.model'].browse(kwargs['model_id'])
        menu_action = request.env['ir.actions.act_window'].browse(
            kwargs['menu_action_id'])
        view_ids = menu_action.mapped('view_ids.view_id')
        menu_action.view_ids = [Command.delete(view_id) for view_id in
                                menu_action.view_ids.ids]
        view_ids.unlink()

        for view_mode in view_types:
            view_arch = self.get_default_view_template(view_mode, editable)
            new_view = request.env['ir.ui.view'].sudo().create({
                'name': f'{view_mode}_' + '_'.join(
                    model_id.name.lower().split(' ')),
                'type': view_mode,
                'model': model_id.model,
                'model_id': model_id.id,
                'arch': view_arch,
                'priority': 999
            })
            views.append({'id': new_view.id, 'view_mode': new_view.type})

        menu_action.write({
            'view_mode': ','.join(view_types),
            'view_ids': [Command.create(
                {'view_id': view['id'], 'view_mode': view['view_mode']})
                for view in views]
        })

        return (
            menu_action.id, model_id.model, model_id.id, menu_action,
            menu_item.read(['id', 'name', 'action']),
            menu_item.id, model_id.name, menu_action.id)

    @route('/cyllo_studio/create_app/existing_model', type="json", auth="user",
           csrf=False)
    def create_app_existing_model(self, args, kwargs):
        """
            Creates a new app menu item for an existing model.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing 'appname', 'IconImage', model details, and view preferences.

            Returns:
                tuple: A tuple of created record IDs and information.
            """
        self.is_studio_user()
        # self.is_studio_admin()
        module_id = kwargs['state'].get('module_id')
        position = kwargs['state'].get('position')

        sequence = self.set_app_sequence(module_id, position)

        model = request.env['ir.model'].browse(kwargs['model_id'])
        view = request.env['ir.ui.view'].sudo()
        views = []
        view_types = [kwargs['set_default_view']]
        editable = False
        for view_type in kwargs['default_views'].values():
            if view_type not in view_types:
                view_types.append(view_type)

        if 'kanban' in view_types and len(view_types) == 1:
            view_types.append('form')

        if (len(view_types) == 1 and view_types[0] == 'tree') \
                or (len(view_types) == 2 and 'tree' in view_types and 'kanban' in view_types):
            editable = True

        for view_mode in view_types:
            view_arch = view.search([('model', '=', model.model), ('type', '=', view_mode), ('inherit_id', '=', False)],
                                    order="id", limit=1)['arch']
            if view_arch:
                if view_mode == 'tree':
                    view_node = etree.fromstring(view_arch)
                    view_editable = view_node.get('editable')
                    if editable and view_editable not in ['top', 'bottom']:
                        view_node.set('editable', 'top')
                    elif view_editable in ['top', 'bottom']:
                        del view_node.attrib['editable']
                    view_arch = etree.tostring(view_node, pretty_print=True, encoding='unicode')

                new_view = request.env['ir.ui.view'].sudo().create({
                    'name': f'{view_mode}_' + '_'.join(model.name.lower().split(' ')),
                    'type': view_mode,
                    'model': model.model,
                    'model_id': model.id,
                    'arch': view_arch,
                    'priority': 999
                })
                views.append({'id': new_view.id, 'view_mode': new_view.type})

        menu_action = request.env['ir.actions.act_window'].create({
            'name': model.name,
            'res_model': model.model,
            'view_mode': ','.join(view_types),
            'view_ids': [Command.create({'view_id': view['id'], 'view_mode': view['view_mode']})
                         for view in views]
        })

        menu_item = request.env['ir.ui.menu'].create({
            'name': kwargs['appname'],
            'action': 'ir.actions.act_window,%d' % menu_action.id,
            'web_icon_data': "",
            'web_icon': "",
            'sequence': sequence,
            'is_studio': True,
        })
        if kwargs['state']['group_ids']:
            menu_item.groups_id = kwargs['state']['group_ids']
        if kwargs['IconImage'].startswith('ri'):
            menu_item.web_icon = kwargs['IconImage']
        elif kwargs['IconImage']:
            menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]

        return menu_action.id, menu_item.id, model.model, views, model.id, model.name

    @route('/cyllo_studio/create_app/new_model', auth="user", csrf=False, type='json')
    def create_app_new_model(self, args, kwargs):
        """
            Creates a new application menu item, a new model, and its associated views and access rights.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing the new app's name, model details, icon, and view preferences.

            Returns:
                tuple: A tuple of the created record IDs and information.
            """
        self.is_studio_user()
        module_id = kwargs['state'].get('module_id')
        position = kwargs['state'].get('position')

        sequence = self.set_app_sequence(module_id, position)

        model_id = request.env['ir.model'].create({
            'name': kwargs['description'],
            'model': 'x_cyllo_' + '_'.join(kwargs['model'].lower().split(' ')),
        })
        View = request.env['ir.ui.view'].sudo()
        views = []
        view_types = [kwargs['set_default_view']]
        editable = False
        for view_type in kwargs['default_view'].values():
            if view_type not in view_types:
                view_types.append(view_type)

        if 'kanban' in view_types and len(view_types) == 1:
            view_types.append('form')

        if (len(view_types) == 1 and view_types[0] == 'tree') \
                or (len(view_types) == 2 and 'tree' in view_types and 'kanban' in view_types):
            editable = True

        for view_mode in view_types:
            view_arch = self.get_default_view_template(view_mode, editable)
            new_view = request.env['ir.ui.view'].sudo().create({
                'name': f'{view_mode}_' + '_'.join(model_id.name.lower().split(' ')),
                'type': view_mode,
                'model': model_id.model,
                'model_id': model_id.id,
                'arch': view_arch,
                'priority': 999
            })
            views.append({'id': new_view.id, 'view_mode': new_view.type})

        menu_action = request.env['ir.actions.act_window'].create({
            'name': model_id.name,
            'res_model': model_id.model,
            'view_mode': ','.join(view_types),
            'view_ids': [Command.create({'view_id': view['id'], 'view_mode': view['view_mode']})
                         for view in views]
        })

        menu_item = request.env['ir.ui.menu'].create({
            'name': kwargs['appname'],
            'web_icon_data': "",
            'web_icon': "",
            'sequence': sequence,
            'is_studio': True,
        })

        child_menu_item = request.env['ir.ui.menu'].create({
            'name': kwargs['appname'],
            'parent_id': menu_item.id,
            'action': 'ir.actions.act_window,%d' % menu_action.id,
            'web_icon_data': "",
            'web_icon': "",
            'sequence': sequence,
            'is_studio': True,
        })

        if kwargs['GroupId']:
            menu_item.groups_id = kwargs['GroupId']
        if kwargs['IconImage'].startswith('ri'):
            menu_item.web_icon = kwargs['IconImage']
        elif kwargs['IconImage']:
            menu_item.web_icon_data = kwargs['IconImage'].split(',')[1]

        request.env['ir.model.access'].create({
            'name': "user_access_" + '_'.join(model_id.model.lower().split(' ')),
            'model_id': model_id.id,
            'group_id': request.env.ref('base.group_user').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })

        request.env['ir.model.access'].create({
            'name': "admin_access_" + '_'.join(model_id.model.lower().split(' ')),
            'model_id': model_id.id,
            'group_id': request.env.ref('base.group_system').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })

        active_field = request.env['ir.model.fields'].create({
            'name': "x_active",
            'field_description': "Active Field",
            'ttype': 'boolean',
            'model_id': model_id.id,
        })

        request.env['ir.default'].sudo().create({
            'field_id': active_field.id,
            'json_value': json.dumps(True)
        })
        return (
            menu_action.id, model_id.model, model_id.id, menu_action, menu_item.read(['id', 'name', 'action']),
            menu_item.id, model_id.name, menu_action.id)

    @route('/cyllo_studio/parentmenuitem', auth="user", csrf=False, type='json')
    def parent_menu(self, args, kwargs):
        """
            Updates the properties of a parent menu item.

            Parameters:
                args (dict): Unused arguments.
                kwargs (dict): A dictionary containing parent menu details like 'MenuName', 'groups', 'IconImage', and 'ActiveMenu'.

            Returns:
                None: The function modifies the menu directly.
            """
        self.is_studio_user()
        parentmenu = request.env['ir.ui.menu'].browse(int(kwargs['ParentMenu']['id']))
        parentmenu.is_studio = True
        parentmenu.name = kwargs['MenuName']
        if kwargs['groups'] or kwargs['groups'] == []:
            if kwargs['groups'] == []:
                parentmenu.groups_id = [Command.clear()]
            else:
                parentmenu.groups_id = kwargs['groups']
        if kwargs.get('IconImage') and kwargs['IconImage'].startswith('ri'):
            parentmenu.web_icon = kwargs['IconImage']
            parentmenu.web_icon_data = ''
        elif kwargs.get('IconImage'):
            parentmenu.web_icon = ''
            parentmenu.web_icon_data = kwargs['IconImage'].split(',')[1] if ',' in kwargs['IconImage'] else kwargs[
                'IconImage']
        parentmenu.active = kwargs['ActiveMenu']

    # # ----------------------------------------search view -------------------------------------------------------4
    #
    @route('/cyllo_studio/search/add/search_view', type="json", auth="user",
           csrf=False)
    def add_search_view(self, arch, model):
        """
            Creates a new search view record in the database.

            Parameters:
                arch (str): The XML string of the search view.
                model (str): The model name for the new view.

            Returns:
                int: The ID of the newly created search view record.
            """
        self.is_studio_user()
        arch_element = etree.fromstring(arch)
        model_id = request.env['ir.model']._get_id(model)

        def remove_element(element):
            if 'cy-xpath' in element.attrib:
                del element.attrib['cy-xpath']
                for child in element:
                    if child.tag == 'studio':
                        element.remove(child)
                    else:
                        remove_element(child)

        remove_element(arch_element)
        main_arch = etree.tostring(arch_element, pretty_print=True).decode('utf-8')
        search_rec = request.env['ir.ui.view'].sudo().create({
            'name': f"Cy_Studio_Search_{model.replace('.', '_')}_{str(uuid.uuid4())[:8]}",
            'type': 'search',
            'model': model,
            'model_id': model_id,
            'arch': main_arch,
        })
        return search_rec.id

    @route('/cyllo_studio/update/search_field', type="json", auth="user",
           csrf=False)
    def update_search_field(self, path, view_id, model, properties):
        """
            Updates the attributes of a field within a search view.

            Parameters:
                path (str): The XPath to the field to be updated.
                view_id (int): The ID of the search view.
                model (str): The model name.
                properties (dict): A dictionary of properties to update.

            Returns:
                str: The XML patch used for the update.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        if properties.get('groupIds'):
            properties['groups'] = ','.join(
                request.env['res.groups'].browse(properties.get('groupIds')).get_external_id().values())
        elif 'groupIds' in properties:
            properties['groups'] = ''
        properties.pop('groupIds')
        search_arch = f"<xpath expr = '{path}' position='attributes'>"
        for key, value in properties.items():
            search_arch += f"<attribute name = '{key}'>{value}</attribute>"

        search_arch += "</xpath>"

        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return search_arch

    @route('/cyllo_studio/remove/form_element', type="json", auth="user",
           csrf=False)
    def remove_form_element(self, item_path, has_multipath, view_id, model):
        """
            Removes an element or a pair of elements from a form view.
            Parameters:
                item_path (dict or str): The XPath(s) to the element(s) to be removed.
                has_multipath (bool): True if multiple elements should be removed.
                view_id (int): The ID of the view.
                model (str): The model name.

            Returns:
                str: The combined XML patch used for deletion.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'form')
        form_node = etree.fromstring(view_rec.arch_base)
        form_arch = ''
        form_arch_2 = ''
        if has_multipath:
            form_arch += f'<xpath expr="{item_path["first_path"]}" position="replace"/>'
            form_arch_2 = ""
            if item_path.get('second_path'):
                form_arch_2 += f'<xpath expr="{item_path["second_path"]}" position="replace"/>'
        else:
            form_arch += f'<xpath expr="{item_path}" position="replace"/>'

        form_node.append(etree.fromstring(form_arch))
        if form_arch_2:
            form_node.append(etree.fromstring(form_arch_2))
        combined_arch = form_arch + form_arch_2
        view_rec.arch_base = etree.tostring(form_node, pretty_print=True, encoding='unicode')
        return combined_arch

    @route('/cyllo_studio/search/remove/item', type="json", auth="user",
           csrf=False)
    def search_remove(self, path, view_id, model):
        """
            Removes an item (filter or field) from a search view.

            Parameters:
                path (str): The XPath to the item to be removed.
                view_id (int): The ID of the search view.
                model (str): The model name.

            Returns:
                str: The XML patch used for deletion.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        remove_arch = f"<xpath expr = '{path}' position='replace'/>"

        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(remove_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return remove_arch

    @route('/cyllo_studio/search/move/item', type="json", auth="user",
           csrf=False)
    def search_move_item(self, view_id, model, path, position, sibling_path, previous_path, perv_path, next_path,
                         first_el_xpath):
        """
            Moves an item within a search view.

            Parameters:
                view_id (int): The ID of the search view.
                model (str): The model name.
                path (str): The XPath of the item to be moved.
                position (str): The position relative to the sibling path.
                sibling_path (str): The XPath of the sibling element.
                previous_path (str): The XPath of the previous sibling.
                perv_path (str): The XPath of the previous sibling.
                next_path (str): The XPath of the next sibling.
                first_el_xpath (str): The XPath of the first element in the search view.

            Returns:
                str: The XML patch used to move the item.
            """
        self.is_studio_user()
        if ("separator" in (perv_path or "")) and ("separator" in (next_path or "")):
            return
        if "separator" in path:
            if ("separator" in (sibling_path or "")) or ("separator" in (previous_path or "")) or not previous_path:
                return
        elif "separator" in first_el_xpath:
            return
        view_rec = self.get_studio_view(view_id, model, 'search')
        search_arch = f"""
            <xpath expr = '{sibling_path if sibling_path else previous_path}' position='{position}'>
                <xpath expr = '{path}' position='move'/>
            </xpath>
        """

        search_node = etree.fromstring(view_rec.arch_base)

        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))
        return search_arch

    @route('/cyllo_studio/search/update/filter', type="json", auth="user",
           csrf=False)
    def update_search_filter(self, path, properties, view_id, model):
        """
            Updates the attributes of a filter in a search view.

            Parameters:
                path (str): The XPath to the filter to be updated.
                properties (dict): A dictionary of properties to update.
                view_id (int): The ID of the search view.
                model (str): The model name.

            Returns:
                str: The XML patch used for the update.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')

        if properties.get('groupIds'):
            properties['groups'] = ','.join(
                request.env['res.groups'].browse(properties.get('groupIds')).get_external_id().values())
        elif 'groupIds' in properties:
            properties['groups'] = ''
        properties.pop('groupIds')
        search_arch = f"<xpath expr = '{path}' position='attributes'>"
        for key, value in properties.items():
            search_arch += f"<attribute name = '{key}'>{escape(value) if value else ''}</attribute>"
        search_arch += "</xpath>"
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))
        return search_arch

    @route('/cyllo_studio/update/group_by', type="json", auth="user",
           csrf=False)
    def update_group_by(self, path, view_id, model, properties):
        """
            Updates the attributes of a 'group by' filter in a search view.

            Parameters:
                path (str): The XPath to the group-by filter to be updated.
                view_id (int): The ID of the search view.
                model (str): The model name.
                properties (dict): A dictionary of properties to update.

            Returns:
                str: The XML patch used for the update.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')

        if properties.get('groupIds'):
            properties['groups'] = ','.join(
                request.env['res.groups'].browse(properties.get('groupIds')).get_external_id().values())
        elif 'groupIds' in properties:
            properties['groups'] = ''
        properties.pop('groupIds')
        search_arch = f"<xpath expr = '{path}' position='attributes'>"
        for key, value in properties.items():
            search_arch += f"<attribute name = '{key}'>{value}</attribute>"
        search_arch += "</xpath>"

        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return search_arch

    @route('/cyllo_studio/search/add/search_panel', type="json", auth="user",
           csrf=False)
    def add_search_panel(self, view_id, model):
        """
            Adds a search panel to a search view.

            Parameters:
                view_id (int): The ID of the search view.
                model (str): The model name.

            Returns:
                str: The XML patch used to add the search panel.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        search_arch = f'''<xpath expr="//search" position="inside">
                <searchpanel/>
            </xpath>'''
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))
        return search_arch

    @route('/cyllo_studio/search/update/search_panel', type="json", auth="user",
           csrf=False)
    def update_search_panel(self, path, view_id, model, properties):
        """
            Updates the attributes of a search panel.

            Parameters:
                path (str): The XPath to the search panel to be updated.
                view_id (int): The ID of the search view.
                model (str): The model name.
                properties (dict): A dictionary of properties to update.

            Returns:
                str: The XML patch used for the update.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')

        if properties.get('groupIds'):
            properties['groups'] = ','.join(
                request.env['res.groups'].browse(properties.get('groupIds')).get_external_id().values())
        elif 'groupIds' in properties:
            properties['groups'] = ''
            properties.pop('groupIds')
        if 'view_types' in properties:
            properties['view_types'] = ','.join(properties.pop('view_types'))
        search_arch = f"<xpath expr = '{path}' position='attributes'>"
        for key, value in properties.items():
            search_arch += f"<attribute name = '{key}'>{value}</attribute>"
        search_arch += "</xpath>"

        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return search_arch

    @route('/cyllo_studio/search/add/search_panel_value', type="json", auth="user",
           csrf=False)
    def add_search_panel_value(self, path, view_id, model, properties):
        """
            Adds a new field to a search panel.

            Parameters:
                path (str): The XPath to the search panel where the field will be added.
                view_id (int): The ID of the search view.
                model (str): The model name.
                properties (dict): A dictionary of properties for the new field.

            Returns:
                str: The XML patch used to add the field.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        search_arch = f"""<xpath expr = '{path}' position='inside'>
                <field name='{properties['field']}'"""
        properties.pop('field')
        if properties.get('groupIds'):
            group_ids = list(map(int, properties.pop("groupIds")))
            groups = ','.join(
                request.env['res.groups'].browse(group_ids).get_external_id().values())
            search_arch += f" groups='{groups}'"
        elif 'groupIds' in properties:
            properties.pop('groupIds')
        for key, value in properties.items():
            if value != "":
                if key in ['string']:
                    search_arch += f' {key}="{escape(value)}"'
                else:
                    search_arch += f' {key}="{value}"'
        search_arch += "/></xpath>"
        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return search_arch

    @route('/cyllo_studio/search/update/search_panel_value', type="json", auth="user",
           csrf=False)
    def update_search_panel_value(self, path, view_id, model, properties):
        """
            Updates the attributes of a field within a search panel.

            Parameters:
                path (str): The XPath to the field element to be updated.
                view_id (int): The ID of the search view.
                model (str): The model name.
                properties (dict): A dictionary of properties to update.

            Returns:
                str: The XML patch used for the update.
            """
        self.is_studio_user()
        view_rec = self.get_studio_view(view_id, model, 'search')
        if properties.get('groupIds'):
            properties['groups'] = ','.join(
                request.env['res.groups'].browse(properties.get('groupIds')).get_external_id().values())
            properties.pop('groupIds')
        elif 'groupIds' in properties:
            properties['groups'] = ''
            properties.pop('groupIds')
        search_arch = f"<xpath expr = '{path}' position='attributes'>"
        for key, value in properties.items():
            search_arch += f"<attribute name = '{key}'>{value}</attribute>"
        search_arch += "</xpath>"

        search_node = etree.fromstring(view_rec.arch_base)
        search_node.append(etree.fromstring(search_arch))
        view_rec.arch_base = (etree.tostring(search_node, pretty_print=True, encoding='unicode'))

        return search_arch

    @route('/cyllo_studio/set/session', type="json", auth="user",
           csrf=False)
    def set_section(self, key, value):
        """
            Sets a key-value pair in the user's session.

            Parameters:
                key (str): The key to be set in the session.
                value (any): The value to be stored for the given key.

            Returns:
                None: The function modifies the session directly.
            """
        self.is_studio_user()
        request.session[key] = value
        # # ----------------------------------------------------------------------------------------------------

    @http.route("/cyllo_studio/_auto_models/actions", type="json", auth="user")
    def get_non_auto_abstract_models_and_actions(self, menuActionId):
        """
            Retrieves information about a model associated with a given menu action.

            Parameters:
                menuActionId (int): The ID of the menu action.

            Returns:
                tuple: A tuple containing the model name, and boolean flags for whether the model is auto, abstract,and
                        transient. Returns None if the action is not found.
            """
        self.is_studio_user()
        action = request.env["ir.actions.act_window"].browse(menuActionId)
        if not action:
            return None
        is_auto = request.env[action.res_model]._auto
        is_abstract = request.env[action.res_model]._abstract
        is_transient = request.env[action.res_model]._transient
        return action.res_model, is_auto, is_abstract, is_transient

    @http.route('/cyllo_studio/get_model_fields', type='json', auth='user')
    def get_model_fields(self, model):
        """
           Retrieves all fields for a given model to populate display name selection

           Parameters:
               model (str): The technical model name whose fields should be listed

           Returns:
               list: A list of dictionaries containing:
                   - name (str): Technical field name.
                   - label (str): Display label of the field.
           """
        self.is_studio_user()
        if not model:
            return []
        fields = request.env[model].fields_get()
        result = []
        for technical_name, attrs in fields.items():
            label = attrs.get('string') or technical_name
            result.append({
                "name": technical_name,
                "label": label,
            })
        return result

    @http.route('/cyllo_studio/set_display_name', type='json', auth='user')
    def set_display_name(self, model, field):
        """
            Updates the model's display name field configuration and refreshes the UI.

            Parameters:
                model (str): The technical model name where display name is being updated.
                field (str): The field name to be used as display_name.

            Returns:
                dict | None: An action to reload the client UI if successful, otherwise None.
        """
        self.is_studio_user()
        if not model or not field:
            return None
        model_rec = request.env['ir.model'].sudo().search([('model', '=', model)], limit=1)
        if not model_rec:
            return None
        model_rec.write({'cy_display_field': field})
        records = request.env[model].sudo().search([])
        _ = records.mapped('display_name')
        request.env['ir.ui.view'].clear_caches()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @http.route('/cyllo_studio/get_m2o_fields', type='json', auth='user')
    def get_m2o_fields(self, model):
        """
        Returns all many2one fields of the given model.
        """
        self.is_studio_user()
        fields = request.env[model].fields_get()
        result = []
        for name, attrs in fields.items():
            if attrs.get('type') == 'many2one':
                result.append({
                    "name": name,
                    "label": attrs.get('string'),
                    "comodel": attrs.get('relation'),
                })
        return result

    @http.route('/cyllo_studio/get_field_compute_info', type='json', auth='user')
    def get_field_compute_info(self, model, field_name):
        """Get compute and dependencies information for a specific field."""
        self.is_studio_user()
        try:
            model_rec = request.env["ir.model"].search([("model", "=", model)], limit=1)
            if not model_rec:
                return {"compute": "", "depends": "", "is_computed": False}

            field_rec = request.env["ir.model.fields"].search([
                ("model_id", "=", model_rec.id),
                ("name", "=", field_name),
            ], limit=1)

            if not field_rec:
                return {"compute": "", "depends": "", "is_computed": False}

            has_compute = bool(field_rec.compute and field_rec.compute.strip())
            has_depends = bool(field_rec.depends and field_rec.depends.strip())

            return {
                "compute": field_rec.compute or "",
                "depends": field_rec.depends or "",
                "is_computed": has_compute or has_depends
            }
        except Exception as e:
            _logger.error(f"Error getting compute info: {e}")
            return {"compute": "", "depends": "", "is_computed": False}

    @route('/cyllo_studio/get_default', type='json', auth='user')
    def get_default(self, model=None, field_name=None):
        """
         Retrieve the stored default value for a specific field.

         Parameters:
             model (str): The technical model name from which the field belongs.
             field_name (str): The technical name of the field whose default value is requested.

         Returns:
             any: The resolved default value for the field.
                  - Parsed JSON value if available.
                  - None if no default is defined.
        """
        self.is_studio_user()
        # New columns / buttons have no field name yet — JSON-RPC drops the
        # undefined key, so guard against missing args instead of crashing.
        if not model or not field_name:
            return None
        field = request.env['ir.model.fields']._get(model, field_name)

        default = request.env['ir.default'].sudo().search([
            ('field_id', '=', field.id),
            ('user_id', '=', False),
            ('company_id', '=', False),
            ('condition', '=', False),
        ], limit=1)

        if not default:
            return None
        value = json.loads(default.json_value)
        return value

    @route('/cyllo_studio/set_default', type='json', auth='user', csrf=False)
    def set_default_value(self, model, field_name, value):
        """
        Create, update, or remove the default value for a specific field.

        Parameters:
            model (str): The technical model name where the field resides.
            field_name (str): The technical name of the field for which the default value is being set.
            value (any): The default value to store.
                         - If empty or null-like values are provided, the existing default is removed.
                         - String values are evaluated when possible.

        Returns:
            dict: A result dictionary containing:
                  - {"success": True} when default is created or updated.
                  - {"success": True} when default is removed.
                  - {"error": "field_not_found"} if the field does not exist.
        """
        self.is_studio_user()
        field = request.env['ir.model.fields']._get(model, field_name)
        if not field:
            return {"error": "field_not_found"}
        if value in (None, "", "null", "undefined"):
            request.env['ir.default'].sudo().search([
                ('field_id', '=', field.id),
                ('user_id', '=', False),
                ('company_id', '=', False),
                ('condition', '=', False),
            ]).unlink()

            return {"success": True}
        if isinstance(value, str):
            raw = value.strip()
            try:
                value = ast.literal_eval(raw)
            except Exception:
                pass

        request.env['ir.default'].sudo().set(
            model_name=model,
            field_name=field_name,
            value=value,
            user_id=False,
            company_id=False,
            condition=False,
        )

        return {"success": True}

    @route('/cyllo_studio/form/add/ribbon', type="json", auth="user", csrf=False)
    def add_form_ribbon(self, viewId, viewType, model, path, position, properties, active_fields=None):
        """
        Add a ribbon element to a form view with proper styling for clickability.

        Parameters:
            view_id (int): ID of the form view.
            view_type (str): Type of view ('form').
            model (str): Model name.
            path (str): XPath to the target element.
            position (str): Position ('before', 'after', 'inside').
            properties (dict): Ribbon properties (string, color, invisible).
            active_fields (dict): Active fields information.

        Returns:
            str: XML string representing the added ribbon.
        """
        self.is_studio_user()
        view_rec = self.get_studio_view(viewId, model, viewType)
        # arch = f"""
        #     <xpath expr="/{path}" position="{position}">
        #         <div class="ribbon ribbon-top-right"
        #              invisible="{properties['invisible']}" style="position: absolute !important; top: 0 !important; right: 0 !important; z-index: 5 !important; margin: 0 !important; padding: 8px 12px !important; pointer-events: auto !important; cursor: pointer !important; overflow: visible !important;">
        #             <span class="{properties['color']}" style="cursor: pointer; pointer-events: auto;">{escape(properties['string'])}</span>
        #         </div>
        #     </xpath>
        # """
        arch = f"""
            <xpath expr="/{path}" position="{position}">
                <div class="ribbon ribbon-top-right"
                     invisible="{properties['invisible']}"
                     style="position: absolute !important; top: 0 !important; right: 0 !important; z-index: 5 !important; margin: 0 !important; padding: 8px 12px !important; pointer-events: auto !important; cursor: pointer !important;">
                    <span class="{properties['color']}" style="pointer-events: auto !important; cursor: pointer !important;">{escape(properties['string'])}</span>
                </div>
            </xpath>
        """

        xml = etree.fromstring(view_rec.arch_base)
        xml.append(etree.fromstring(arch))
        # Handle invisible fields if needed
        not_present_field = self.create_invisible([{
            'invisible': properties['invisible'],
            'active_fields': active_fields or {},
            'model': model,
            'viewType': viewId,
            'path': path,
            'position': position
        }])

        if not_present_field:
            not_present_field_arch = f"""<xpath expr="//form" position="inside">
                {not_present_field}
            </xpath>"""
            xml.append(etree.fromstring(not_present_field_arch))

        view_rec.arch_base = etree.tostring(xml, pretty_print=True, encoding='unicode')
        return arch

    @route('/cyllo_studio/form/update/ribbons', type="json", auth="user", csrf=False)
    def update_form_ribbon(self, **kwargs):
        """
        Update ribbon elements inside FORM view.
        Handles both editing and deletion of ribbons while preserving invisible expressions.
        """
        self.is_studio_user()
        view_id = kwargs.get("viewId")
        view_type = kwargs.get("viewType")
        model = kwargs.get("model")
        ribbons = kwargs.get("ribbons")
        active_fields = kwargs.get("active_fields")

        view_rec = self.get_studio_view(view_id, model, view_type)
        view_node = etree.fromstring(view_rec.arch_base)

        base_view = request.env['ir.ui.view'].browse(view_id)
        base_arch = etree.fromstring(base_view.arch_base)
        base_ribbons = base_arch.xpath('//div[@class="ribbon ribbon-top-right" or contains(@class, "ribbon")]')

        # Separate deleted and edited ribbons
        deleted_ribbons = [r for r in ribbons if r.get("hasDelete")]
        edited_ribbons = [r for r in ribbons if not r.get("hasDelete") and r.get("hasEdit")]
        selected_ribbon_path = None
        for ribbon in ribbons:
            if ribbon.get("selected"):
                selected_ribbon_path = ribbon.get("path")
                break
        # Process edited ribbons first
        for ribbon in edited_ribbons:
            xpath_expr = ribbon["path"]

            # Ensure invisible expression is properly formatted
            invisible_expr = ribbon.get("invisible", "False")
            if not invisible_expr or invisible_expr in ["", "null", "undefined"]:
                invisible_expr = "False"

            # Replace the ribbon with updated content
            # view_arch = f"""
            #     <xpath expr="{xpath_expr}" position="replace">
            #         <div class="ribbon ribbon-top-right" invisible="{escape(invisible_expr)}">
            #             <span class="{ribbon['color']}">{escape(ribbon['firstElementContent'])}</span>
            #         </div>
            #     </xpath>
            # """
            view_arch = f"""
                   <xpath expr="{xpath_expr}" position="replace">
                       <div class="ribbon ribbon-top-right" 
                            invisible="{escape(invisible_expr)}"
                            style="position: absolute !important; top: 0 !important; right: 0 !important; z-index: 5 !important; margin: 0 !important; padding: 8px 12px !important; pointer-events: auto !important; cursor: pointer !important;">
                           <span class="{ribbon['color']}" style="pointer-events: auto !important; cursor: pointer !important;">{escape(ribbon['firstElementContent'])}</span>
                       </div>
                   </xpath>
               """
            view_node.append(etree.fromstring(view_arch))

            # Add invisible placeholder fields for domain-based conditions
            not_present_field = self.create_invisible([{
                "invisible": invisible_expr,
                "active_fields": active_fields or {},
                "model": model,
                "viewType": view_type,
                "path": "form",  # Changed to "form" for form views
                "position": "inside"
            }])

            if not_present_field:
                # Add to form root
                not_present_field_arch = f"""
                    <xpath expr="//form" position="inside">
                        {not_present_field}
                    </xpath>
                """
                view_node.append(etree.fromstring(not_present_field_arch))

        # Process deleted ribbons (sorted by index to avoid conflicts)
        deleted_ribbons_sorted = sorted(
            deleted_ribbons,
            key=lambda ribbon: self.extract_index(ribbon.get('path', '')),
            reverse=True
        )

        for ribbon in deleted_ribbons_sorted:
            xpath_expr = ribbon.get("path")
            if xpath_expr:
                view_arch = f"""<xpath expr="{xpath_expr}" position="replace"/>"""
                view_node.append(etree.fromstring(view_arch))

        # Save the updated architecture
        view_rec.arch_base = etree.tostring(view_node, pretty_print=True, encoding="unicode")
        return view_rec.arch_base

    def _save_sql_constraints(self, model_rec, constraints):
        """
        Save SQL constraints and apply them to the database.
        Registers them in env.registry._sql_constraints so Odoo can find custom messages.
        """
        try:
            table_name = model_rec.model.replace('.', '_')
            module_name = model_rec.modules.split(',')[0] if model_rec.modules else 'base'
            module = request.env['ir.module.module'].search([('name', '=', module_name)], limit=1)
            if not module:
                module = request.env['ir.module.module'].search([('name', '=', 'base')], limit=1)
            cr = request.env.cr
            for constraint_data in constraints:
                if isinstance(constraint_data, (list, tuple)) and len(constraint_data) >= 3:
                    key, definition, message = constraint_data[0], constraint_data[1], constraint_data[2]
                    if key.startswith(f"{table_name}_"):
                        base_name = key[len(f"{table_name}_"):]
                    else:
                        base_name = key
                    constraint_name = f"{table_name}_{base_name}"
                    constraint_db_name = constraint_name

                    try:
                        current_definition = tools.constraint_definition(cr, table_name, constraint_name)
                        if current_definition == definition:
                            pass
                        else:
                            if current_definition:
                                try:
                                    tools.drop_constraint(cr, table_name, constraint_name)
                                except Exception as e:
                                    _logger.warning(f"Failed to drop constraint {constraint_name}: {e}")
                            tools.add_constraint(cr, table_name, constraint_name, definition)
                    except Exception as db_error:
                        error_msg = str(db_error)

                        if "violates" in error_msg.lower() or "duplicate" in error_msg.lower():
                            cr.rollback()
                            raise UserError(
                                f"Cannot apply constraint '{constraint_name}': \n"
                                f"Existing data violates this constraint.\n\n"
                                f"Please clean up your data and try again."
                            )
                        else:
                            cr.rollback()
                            raise UserError(f"Failed to create constraint '{constraint_name}': {error_msg}")

                    msg_str = message if isinstance(message, str) else (
                        message.get('en_US', list(message.values())[0]) if isinstance(message, dict) else str(message)
                    )
                    existing = request.env['ir.model.constraint'].search([
                        ('model', '=', model_rec.id),
                        ('name', '=', constraint_name),
                    ], limit=1)
                    constraint_vals = {
                        'name': constraint_name,
                        'definition': definition,
                        'message': msg_str,
                        'model': model_rec.id,
                        'module': module.id,
                        'type': 'u',
                    }
                    if existing:
                        existing.write(constraint_vals)
                    else:
                        request.env['ir.model.constraint'].create(constraint_vals)

                    cr.commit()

                    try:
                        if constraint_db_name not in request.env.registry._sql_constraints:
                            request.env.registry._sql_constraints.add(constraint_db_name)
                            cr.commit()
                        else:
                            _logger.info(f"Constraint already in registry: {constraint_db_name}")
                    except Exception as e:
                        _logger.warning(f"Could not add to registry: {e}")

                    try:
                        ModelClass = type(request.env[model_rec.model])
                        sql_constraints = list(getattr(ModelClass, '_sql_constraints', []))
                        sql_constraints = [constraint_tuple for constraint_tuple in sql_constraints if
                                           constraint_tuple[0] != base_name]
                        sql_constraints.append((base_name, definition, msg_str))
                        ModelClass._sql_constraints = sql_constraints

                    except Exception as e:
                        _logger.warning(f"Could not update model class: {e}")

            cr.commit()
        except UserError:
            raise
        except Exception as e:
            request.env.cr.rollback()
            raise UserError(f"Failed to save SQL constraints: {str(e)}")

    def _remove_sql_constraints(self, model_rec, field_name):
        """
        Remove all SQL constraints for a specific field from DB, ir.model.constraint, registry, and model class.
        """
        table_name = model_rec.model.replace('.', '_')
        cr = request.env.cr
        constraints = request.env['ir.model.constraint'].search([
            ('model', '=', model_rec.id),
            ('type', '=', 'u'),
            '|',
            ('definition', 'ilike', field_name),
            ('name', 'ilike', field_name),
        ])

        for constraint in constraints:
            constraint_name = constraint.name
            name_variations = set([
                constraint_name,
                f"{table_name}_{constraint_name}",
                constraint_name.replace(f"{table_name}_", ""),
            ])
            for name in name_variations:
                cr.execute(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{name}"')
            constraint.unlink()
            for name in name_variations:
                request.env.registry._sql_constraints.discard(name)
        ModelClass = type(request.env[model_rec.model])
        ModelClass._sql_constraints = [
            constraint_tuple for constraint_tuple in getattr(ModelClass, '_sql_constraints', [])
            if field_name.lower() not in constraint_tuple[0].lower()
               and field_name.lower() not in constraint_tuple[1].lower()
        ]
        cr.commit()

    @route('/cyllo_studio/get_sql_constraints', type="json", auth="user", csrf=False)
    def get_sql_constraints(self, model, field_name):
        """
        Get SQL constraints for a specific field
        """
        self.is_studio_user()
        try:
            result = []
            table_name = model.replace('.', '_')
            model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
            if model_rec:
                constraints = request.env['ir.model.constraint'].search([
                    ('model', '=', model_rec.id),
                    ('type', '=', 'u'),
                ])
                for constraint in constraints:
                    if field_name.lower() in constraint.definition.lower():
                        key = constraint.name
                        if key.startswith(f"{table_name}_"):
                            key = key[len(table_name) + 1:]

                        result.append({
                            'key': key,
                            'definition': constraint.definition,
                            'message': constraint.message,
                        })
            return result
        except Exception as e:
            _logger.error(f"Error fetching constraints: {e}", exc_info=True)
            return []

    @route('/cyllo_studio/get_python_constraint', type="json", auth="user", csrf=False)
    def get_python_constraint(self, model, field_name):
        """
        Get Python constraint for a specific field
        """
        self.is_studio_user()
        try:
            model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
            if not model_rec:
                return None
            field_rec = request.env['ir.model.fields'].search([
                ('model_id', '=', model_rec.id),
                ('name', '=', field_name),
            ], limit=1)

            if not field_rec:
                return None
            if field_rec.constraint_code and field_rec.constraint_fields:
                return {
                    'deps': field_rec.constraint_fields,
                    'code': field_rec.constraint_code,
                }
            return None
        except Exception as e:
            return None

    @route('/cyllo_studio/check_field_data', type="json", auth="user", csrf=False)
    def check_field_data(self, model, field_name):
        """
        Check for NULL and empty values in a field
        Returns count of NULL values, empty values, and total records
        """
        self.is_studio_user()
        try:
            _logger.info(f"Checking data for {model}.{field_name}")
            model_rec = request.env[model]
            total_records = model_rec.search_count([])
            null_count = model_rec.search_count([
                (field_name, '=', False)
            ])
            empty_count = model_rec.search_count([
                (field_name, '=', '')
            ])
            _logger.info(
                f"Field: {field_name} | "
                f"Total: {total_records} | "
                f"NULL: {null_count} | "
                f"Empty: {empty_count}"
            )
            return {
                'null_count': null_count,
                'empty_count': empty_count,
                'total_records': total_records,
                'has_issues': (null_count + empty_count) > 0,
            }
        except Exception as e:
            return {
                'null_count': 0,
                'empty_count': 0,
                'total_records': 0,
                'has_issues': False,
                'error': str(e),
            }

    @route('/cyllo_studio/remove_single_constraint', type='json', auth='user', csrf=False)
    def remove_single_constraint(self, model, field_name, constraint_key):
        """
        Remove a single SQL constraint by key from DB, ir.model.constraint, registry, and model class.
        """
        self.is_studio_user()
        model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
        if not model_rec:
            return {'success': False, 'error': 'Model not found'}

        table_name = model.replace('.', '_')
        cr = request.env.cr
        base_key = constraint_key.replace(f"{table_name}_", "")
        name_variations = set([
            constraint_key,
            f"{table_name}_{base_key}",
            base_key,
        ])
        constraint = request.env['ir.model.constraint'].search([
            ('model', '=', model_rec.id),
            ('type', '=', 'u'),
            '|',
            ('name', 'in', list(name_variations)),
            ('definition', 'ilike', field_name),
        ], limit=1)

        if not constraint:
            return {'success': False, 'error': 'Constraint not found'}
        for name in name_variations:
            cr.execute(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{name}"')
        constraint.unlink()

        for name in name_variations:
            request.env.registry._sql_constraints.discard(name)
        ModelClass = type(request.env[model])
        ModelClass._sql_constraints = [
            constraint_tuple for constraint_tuple in getattr(ModelClass, '_sql_constraints', [])
            if constraint_tuple[0] not in name_variations
        ]
        cr.commit()
        return {'success': True, 'message': f'Constraint {constraint_key} removed'}

    @http.route('/cyllo_studio/get_button_limit', type='json', auth='user')
    def get_button_limit(self, view_id, model):
        """Get the current button_limit value from header"""
        self.is_studio_user()
        try:
            view = request.env['ir.ui.view'].sudo().browse(view_id)
            if not view or view.type != 'form':
                return {'button_limit': None}

            arch = view.arch
            if not arch:
                return {'button_limit': None}

            try:
                root = ET.fromstring(arch)
                header = root.find('.//header')
                if header is not None:
                    button_limit = header.get('button_limit')
                    if button_limit:
                        return {'button_limit': button_limit}
            except ET.ParseError:
                pass

            return {'button_limit': None}
        except Exception as e:
            return {'error': str(e), 'button_limit': None}

    @http.route('/cyllo_studio/set_button_limit', type='json', auth='user')
    def set_button_limit(self, view_id, model, button_limit):
        """Set or update the button_limit attribute on header"""
        self.is_studio_user()
        try:
            button_limit = int(button_limit)
            if button_limit <= 0:
                return {'success': False, 'message': 'Button limit must be a positive number'}

            view = request.env['ir.ui.view'].sudo().browse(view_id)
            if not view or view.type != 'form':
                return {'success': False, 'message': 'Invalid form view'}

            arch = view.arch
            if not arch:
                return {'success': False, 'message': 'View has no arch'}

            try:
                root = ET.fromstring(arch)
            except ET.ParseError as e:
                return {'success': False, 'message': f'Invalid XML: {str(e)}'}

            header = root.find('.//header')
            if header is None:
                form_elem = root.find('.//form')
                if form_elem is None:
                    return {'success': False, 'message': 'No form element found'}
                header = ET.Element('header')
                form_elem.insert(0, header)

            header.set('button_limit', str(button_limit))
            new_arch = ET.tostring(root, encoding='unicode')
            view.write({'arch': new_arch})

            return {'success': True, 'message': f'Button limit set to {button_limit}'}
        except ValueError:
            return {'success': False, 'message': 'Invalid button limit value. Must be a number.'}
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}

    @http.route('/cyllo_studio/remove_button_limit', type='json', auth='user')
    def remove_button_limit(self, view_id, model):
        """Remove the button_limit attribute from header"""
        self.is_studio_user()
        try:
            view = request.env['ir.ui.view'].sudo().browse(view_id)
            if not view or view.type != 'form':
                return {'success': False, 'message': 'Invalid form view'}

            arch = view.arch
            if not arch:
                return {'success': False, 'message': 'View has no arch'}

            try:
                root = ET.fromstring(arch)
            except ET.ParseError as e:
                return {'success': False, 'message': f'Invalid XML: {str(e)}'}

            header = root.find('.//header')
            if header is not None and 'button_limit' in header.attrib:
                del header.attrib['button_limit']

            new_arch = ET.tostring(root, encoding='unicode')
            view.write({'arch': new_arch})

            return {'success': True, 'message': 'Button limit attribute removed'}
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}


