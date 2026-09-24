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
import base64
import json as _json_lib
import os
import time
import types
import functools
import ast as _ast_lib
import builtins
from collections import defaultdict
import logging
import requests as _requests_lib
from lxml import etree

from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools import file_open
from odoo.tools.safe_eval import _BUILTINS, safe_eval

_logger = logging.getLogger(__name__)


class _UndefinedNameFinder(_ast_lib.NodeVisitor):
    def __init__(self, known_names):
        self.known_names = set(known_names)
        self.undefined_names = set()
        self.local_names = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, _ast_lib.Store):
            self.local_names.add(node.id)
        elif isinstance(node.ctx, _ast_lib.Load):
            if node.id not in self.known_names and node.id not in self.local_names and not hasattr(builtins, node.id):
                self.undefined_names.add(node.id)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.local_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.local_names.add(alias.asname or alias.name)
        self.generic_visit(node)


def _check_code_with_ast(code, known_names):
    """Run AST-based validation for undefined names.

    :param code: str, already-validated (compilable) Python source
    :param known_names: set of str, names available in the workflow execution context
    :return: list of str, human-readable messages (empty if none)
    """
    try:
        tree = _ast_lib.parse(code)
    except Exception:
        return []
    finder = _UndefinedNameFinder(known_names)
    finder.visit(tree)
    return [f"undefined name {repr(name)}" for name in finder.undefined_names]


_RECENT_AUTOMATION_RUNS = {}
_RECENT_AUTOMATION_RUN_TTL = 5  # seconds


def _recently_ran(dedup_key):
    """Return True if `dedup_key` already ran (and COMMITTED) within the TTL window.
    Read-only; recording is done separately by _mark_ran() from a post-commit hook.
    """
    now = time.time()
    # Opportunistically prune old entries so the cache doesn't grow forever.
    stale = [k for k, ts in _RECENT_AUTOMATION_RUNS.items() if now - ts > _RECENT_AUTOMATION_RUN_TTL]
    for k in stale:
        _RECENT_AUTOMATION_RUNS.pop(k, None)
    last_run = _RECENT_AUTOMATION_RUNS.get(dedup_key)
    # Note: the timestamp is NOT refreshed here. Refreshing on a blocked call
    # would keep pushing the window forward, so a client that retries faster
    # than the TTL could stay blocked forever instead of for TTL seconds.
    return last_run is not None and (now - last_run) < _RECENT_AUTOMATION_RUN_TTL


def _mark_ran(dedup_key):
    """Record that `dedup_key` ran. Call only once the transaction has committed."""
    _RECENT_AUTOMATION_RUNS[dedup_key] = time.time()


class WorkFunctionArg(models.Model):
    """
        An argument for a work function, holding a name, type, and a link to its
        parent `work.function` record.
        """
    _name = "work.function.arg"

    name = fields.Char('Arg name', default='arg')
    ttype = fields.Selection(
        [
            ('dict', 'Dictionary'), ('list', 'List'),
            ('tuple', 'Tuple'), ('str', 'String'),
            ('int', 'Integer'), ('float', 'Float'),
            ('None', 'None'), ('set', 'Set'),
            ('bool', 'Boolean'), ('record', 'Record'),
            ('recordset', 'Record set'), ('other', 'Other'),
        ],
        'Arg Type',
        default='str'
    )
    function_id = fields.Many2one('work.function')


class ProcessArg(models.Model):
    """
        An argument for a work process; extends `work.function.arg` with a value and
        flags marking whether it applies before or after the process runs.
        """
    _name = "work.process.arg"
    _inherit = "work.function.arg"

    value = fields.Char('Value')
    is_before = fields.Boolean('Is Before')
    is_after = fields.Boolean('Is After')

    @api.constrains('is_before', 'is_after')
    def check_is_before(self):
        """
            Ensure at least one of `is_before` / `is_after` is set for each record.
            Raises a ValidationError if both are False.
            """
        for rec in self:
            if not rec.is_before and not rec.is_after:
                raise exceptions.ValidationError('Should give at least Is Before or Is After')


class WorkFunction(models.Model):
    """
        A function within a workflow automation, linked to arguments and processes.
        Runs in 'manual' mode (using `make_function`) or 'auto' mode (generated code).
    """
    _name = "work.function"

    name = fields.Char('Name')
    func_name = fields.Char('Function name')
    decorator = fields.Char('decorator name')
    model_id = fields.Many2one('ir.model')
    make_function = fields.Text('Make function')
    arg_ids = fields.One2many('work.function.arg', 'function_id')
    process_ids = fields.One2many('work.process.arg', 'function_id')
    has_return = fields.Boolean('Has return', default=True)
    c_make_function = fields.Text(
        'Make Function',
        compute='compute_c_make_function', store=True
    )
    mode = fields.Selection(
        [('manual', 'Manual'), ('auto', 'Auto')],
        'mode',
        compute='compute_mode'
    )
    trigger_type = fields.Selection(
        [
            ('create', 'On create'),
            ('write', 'On write'),
            ('unlink', 'On delete'),
            ('time', 'At a time'),
            ('new_action', 'New Action'),
            ('field_change', 'On change'),
            ('other', 'Other functions'),
            ('button_click', 'Button Click (Studio)'),
        ],
        default='other'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    icon = fields.Binary()

    @api.model
    def _is_studio_workflow_func_name(self, func_name):
        return bool(func_name and str(func_name).startswith('studio_wf_'))

    @api.model
    def _normalize_button_click_vals(self, vals):
        vals = dict(vals or {})
        if self._is_studio_workflow_func_name(vals.get('func_name')):
            vals['trigger_type'] = 'button_click'
        return vals

    @api.constrains('icon')
    def _check_icon_file_type(self):
        """
            Decode the uploaded icon and raise a ValidationError if it isn't a valid SVG file.
            """
        for record in self:
            if record.icon:
                try:
                    file_content = base64.b64decode(record.icon)
                    if not file_content.startswith(b'<?xml') and not file_content.startswith(b'<svg'):
                        raise exceptions.ValidationError("The uploaded file is not a valid SVG.")
                    if b'<svg' not in file_content[:1000]:
                        raise exceptions.ValidationError("The uploaded file does not appear to be a valid SVG.")
                except:
                    raise exceptions.ValidationError("Unable to verify the file. Please ensure it's a valid SVG.")

    @api.depends('func_name', 'make_function', 'arg_ids', 'process_ids', 'has_return', 'trigger_type')
    def compute_c_make_function(self):
        """
            Generate the executable trigger function code into `c_make_function`, from
            `make_function` if provided, otherwise from the function's args and trigger type.
            """
        for rec in self:
            if rec.make_function:
                rec.c_make_function = rec.make_function
                continue
            args = ','.join(rec.arg_ids.mapped('name')) if rec.arg_ids else ''
            trigger_value = f"'{rec.trigger_type}'" if rec.trigger_type else 'None'
            process_payload = f"{{'records': self, 'trigger_type': {trigger_value}}}"
            process_before = process_after = process_payload
            decorator = f'@api.{rec.decorator}' if rec.decorator else ''
            if rec.trigger_type == 'button_click' or self._is_studio_workflow_func_name(rec.func_name):
                make_function = f'''
                def make_{rec.func_name}():
                    {decorator}
                    def {rec.func_name}(self{',' if args else ''}{args}):
                        guard_key = '_workflow_{rec.func_name}_running_' + self._name
                        if self.env.context.get(guard_key):
                            return False
                        automation_ids = self.env['work.auto']._get_actions(self, '{rec.func_name}')
                        before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                        for automation in before_ids.with_context(old_values=None):
                            automation._process({process_before})
                        after_ids = automation_ids - before_ids
                        for automation in after_ids.with_context(old_values=None):
                            automation._process({process_after})
                        return False
                    return {rec.func_name}
                '''
                rec.c_make_function = make_function.strip()
                continue
            make_function = f'''
            def make_{rec.func_name}():
                {decorator}
                def {rec.func_name}(self{',' if args else ''}{args}):
                    guard_key = '_workflow_{rec.func_name}_running_' + self._name
                    if self.env.context.get(guard_key):
                        return {rec.func_name}.origin(self{',' if args else ''}{args})
                    automation_ids = self.env['work.auto']._get_actions(self, '{rec.func_name}')
                    if not automation_ids:
                        return {rec.func_name}.origin(self{',' if args else ''}{args})
                    before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                    for automation in before_ids.with_context(old_values=None):
                        automation._process({process_before})
                    res = {rec.func_name}.origin(self.with_context(**{{guard_key: True}}).with_env(automation_ids.env){',' if args else ''}{args})
                    after_ids = automation_ids - before_ids
                    for automation in after_ids.with_context(old_values=None):
                        automation._process({process_after})
                    {'return res' if rec.has_return else ''}
                return {rec.func_name}
            '''
            rec.c_make_function = make_function.strip()

    def compute_mode(self):
        for rec in self:
            rec.mode = 'manual' if rec.make_function else 'auto'

    @api.model
    def _ensure_button_trigger(self, model_name, func_name):
        if not model_name or not func_name:
            return self.browse()
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', model_name)], limit=1
        )
        if not model_id:
            return self.browse()
        existing = self.sudo().search([
            ('func_name', '=', func_name),
            ('model_id', '=', model_id.id),
            ('trigger_type', '=', 'button_click'),
        ], limit=1)
        if not existing:
            existing = self.sudo().create({
                'name': func_name.replace('studio_wf_', '').replace('_', ' ').title() or 'Button Click (Studio)',
                'func_name': func_name,
                'model_id': model_id.id,
                'trigger_type': 'button_click',
            })
        if self.env.registry.ready:
            self.env['work.auto']._update_registry()
        return existing

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._normalize_button_click_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        vals = self._normalize_button_click_vals(vals)
        return super().write(vals)


class WorkAuto(models.Model):
    _name = "work.auto"
    _inherit = ['image.mixin']

    name = fields.Char("Name")
    function_id = fields.Many2one('work.function')
    model_id = fields.Many2one('ir.model', ondelete="cascade")
    active = fields.Boolean("Active", default=True)
    code = fields.Text('Code')
    imports = fields.Json("Imports")
    trigger_type = fields.Selection(related='function_id.trigger_type')
    ttype = fields.Selection(
        [('before', 'Before'), ('after', 'After')],
        default="after",
        required=True
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        'On Change Field',
        domain="[('model_id', '=', model_id)]"
    )
    time_trigger_mode = fields.Selection([
        ('hour', 'Every Hour'),
        ('day', 'Every Day'),
        ('week', 'Every Week'),
        ('month', 'Every Month'),
        ('year', 'Every Year')
    ])
    time_trigger_time = fields.Float('Time')
    time_trigger_day = fields.Integer('Day')
    time_trigger_month = fields.Integer('Month')
    time_trigger_weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day of Week', default='0')
    schedule_id = fields.Many2one('ir.cron')
    flow_data = fields.Json(string="Flow data")
    context = fields.Char(string="Context")
    variables = fields.Json(string="Variables")
    trigger_function_ids = fields.Many2many(
        'work.function',
        string="Trigger Functions",
        compute='_compute_trigger_functions',
        store=True,
        copy=False,
    )
    is_reusable = fields.Boolean(string="Reusable", default=False)
    # Reusable automations are always generic: they accept whatever record is
    # passed in by the calling workflow.
    reuse_scope = fields.Selection(
        [('generic', 'Generic (any model)')],
        string='Reuse Scope',
        default='generic',
    )
    is_editable_copy = fields.Boolean(string="Editable Copy", default=False, copy=False)
    node_struct_ids = fields.One2many('node.struct', 'work_auto_id')
    image_1920 = fields.Binary(
        string="Image 1920",
        default=lambda self: self.getDefaultImage1920()
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        default=lambda self: self.env.company
    )
    is_record_saved = fields.Boolean(default=False)

    def _archive_workflows_with_whatsapp_nodes(self):
        """
            Deactivate active workflows that contain a node named 'WhatsApp'.
            Returns the recordset of workflows that were archived.
            """
        workflows = self.sudo().search([
            ('active', '=', True),
            ('node_struct_ids.name', '=', 'WhatsApp'),
        ])
        if workflows:
            workflows.write({'active': False})
        return workflows

    def save_data(self, data, name, ttype, **kwargs):
        """
            Create or update a workflow automation record from the drawflow `data`, linking any
            detached node structures and resolving trigger functions. Returns the workflow's id.
            """
        workflow_auto_id = self or False
        img = kwargs.get('image', False)
        t_ttype = 'before' if ttype else 'after'
        trigger_function_ids = kwargs.get('trigger_function_ids', []) or []

        # ── Link Detached Nodes ───────────────────────────────────────────────
        # When a new automation is created, node.struct records are created first
        # with work_auto_id=False. We must link them now.
        node_ids = []
        if data:
            drawflow = data.get('drawflow', {}) or {}
            home = drawflow.get('Home', {}) or {}
            nodes = home.get('data', {}) or {}
            for node in nodes.values():
                nid = node.get('data', {}).get('nodeId')
                if nid:
                    node_ids.append(nid)

        time_fields = {}
        if kwargs.get('time_trigger_mode'):
            time_fields['time_trigger_mode'] = kwargs['time_trigger_mode']
        if 'time_trigger_time' in kwargs:
            time_fields['time_trigger_time'] = kwargs['time_trigger_time']
        if 'time_trigger_day' in kwargs:
            time_fields['time_trigger_day'] = kwargs['time_trigger_day']
        if 'time_trigger_month' in kwargs:
            time_fields['time_trigger_month'] = kwargs['time_trigger_month']
        if 'time_trigger_weekday' in kwargs:
            time_fields['time_trigger_weekday'] = kwargs['time_trigger_weekday']

        field_change_fields = {}
        if kwargs.get('field_id'):
            field_change_fields['field_id'] = kwargs['field_id']

        if not self:
            values = {
                'name': name,
                'flow_data': data,
                'model_id': kwargs.get('model_id', False),
                'code': kwargs.get('code', False),
                'variables': kwargs.get('variables', []),
                'imports': kwargs.get('imports', []),
                'is_reusable': kwargs.get('is_reusable', False),
                'reuse_scope': kwargs.get('reuse_scope', False),
                'ttype': t_ttype,
                'is_record_saved': True,
                **time_fields,
                **field_change_fields,
            }
            workflow_auto_id = self.create(values)
            if node_ids:
                self.env['node.struct'].sudo().browse(node_ids).write({
                    'work_auto_id': workflow_auto_id.id
                })
        else:
            values = {
                'name': name,
                'flow_data': data,
                'model_id': kwargs.get('model_id', False),
                'code': kwargs.get('code', False),
                'variables': kwargs.get('variables', []),
                'imports': kwargs.get('imports', self.imports),
                'is_reusable': kwargs.get('is_reusable', self.is_reusable),
                'reuse_scope': kwargs.get('reuse_scope', self.reuse_scope),
                'ttype': t_ttype,
                'is_record_saved': True,
                **time_fields,
                **field_change_fields,
            }
            self.write(values)
            if node_ids:
                self.env['node.struct'].sudo().browse(node_ids).write({
                    'work_auto_id': self.id
                })

        # Derive triggers from the saved flow itself. This covers both direct
        # trigger nodes and "Reuse Automation" nodes without relying on the
        # one2many cache being refreshed immediately after linking node.struct
        # rows to a freshly created automation.
        automation = workflow_auto_id or self
        if not trigger_function_ids:
            trigger_function_ids = automation._extract_trigger_function_ids_from_flow(
                data or automation.flow_data
            )

        if trigger_function_ids:
            target_function = trigger_function_ids[0]
            automation.write({
                'trigger_function_ids': [(6, 0, trigger_function_ids)],
                'function_id': target_function,
            })
        else:
            automation.write({
                'trigger_function_ids': [(5, 0, 0)],
                'function_id': False,
            })

        # Ensure cron is created/updated for time-based triggers after all
        # fields (function_id, time_trigger_mode, etc.) are saved.
        automation.create_cron()

        return automation.id

    def clear_all_nodes(self):
        """Delete all `node.struct` records linked to this workflow."""
        self.node_struct_ids.unlink()
        return

    def update_flow_data(self, flow_data):
        """Update the workflow's flow_data with `flow_data` and return the record's id."""
        self.flow_data = flow_data
        return self.id

    def _extract_trigger_function_ids_from_flow(self, flow_data):
        """
            Parse `flow_data` for trigger nodes and reuse-automation nodes, and return the
            unique list of their associated function IDs.
            """
        if not flow_data:
            return []
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        function_ids = []
        seen_trigger_types = set()
        for node in nodes.values():
            data = node.get('data') or {}
            node_type = data.get('type')

            # 1. Direct Trigger Nodes (type='action')
            if node_type == 'action':
                model_info = data.get('model')
                trigger_type = data.get('trigger_type')
                if trigger_type and trigger_type in seen_trigger_types:
                    continue
                if isinstance(model_info, (list, tuple)) and model_info:
                    func_id = model_info[0]
                elif isinstance(model_info, dict):
                    func_id = model_info.get('id')
                else:
                    func_id = False
                if isinstance(func_id, int) and not isinstance(func_id, bool):
                    function_ids.append(func_id)
                    if trigger_type:
                        seen_trigger_types.add(trigger_type)

            # 2. Reuse Automation Nodes (type='action_to_do')
            elif node_type == 'action_to_do' and data.get('name') == 'Reuse Automation':
                node_id = data.get('nodeId')
                if node_id:
                    struct_node = self.env['node.struct'].sudo().browse(node_id)
                    if struct_node.reused_work_auto_id:
                        inherited = struct_node.reused_work_auto_id.trigger_function_ids.ids
                        function_ids.extend(inherited)

        return list(dict.fromkeys(function_ids))

    def _get_test_node_order(self):
        """
            Walk the persisted drawflow graph from its root nodes, in output order, and
            return the resulting node order, with any unreached nodes appended at the end.
        """
        self.ensure_one()
        flow_data = self.flow_data or {}
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        if not nodes:
            return self.env['node.struct']

        node_by_struct_id = {}
        incoming_counts = defaultdict(int)
        adjacency = defaultdict(list)

        def _output_sort_key(item):
            label = item[0] or ''
            if '_' in label:
                try:
                    return int(label.split('_')[-1])
                except ValueError:
                    return label
            return label

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            struct_id = node_data.get('nodeId')
            if struct_id:
                node_by_struct_id[int(struct_id)] = draw_node
            outputs = draw_node.get('outputs', {}) or {}
            for _output_name, output in sorted(outputs.items(), key=_output_sort_key):
                for connection in output.get('connections', []) or []:
                    target_draw_id = str(connection.get('node'))
                    if target_draw_id in nodes:
                        adjacency[str(draw_node_id)].append(target_draw_id)
                        incoming_counts[target_draw_id] += 1

        root_ids = []
        for draw_node_id, draw_node in nodes.items():
            if incoming_counts.get(str(draw_node_id), 0) == 0:
                root_ids.append(str(draw_node_id))
        if not root_ids:
            root_ids = list(nodes.keys())

        ordered_struct_ids = []
        visited_draw_ids = set()

        def _visit(draw_node_id):
            key = str(draw_node_id)
            if key in visited_draw_ids:
                return
            visited_draw_ids.add(key)
            draw_node = nodes.get(key) or {}
            struct_id = (draw_node.get('data') or {}).get('nodeId')
            if struct_id:
                ordered_struct_ids.append(int(struct_id))
            for child_id in adjacency.get(key, []):
                _visit(child_id)

        for root_id in root_ids:
            _visit(root_id)
        for draw_node_id in nodes.keys():
            _visit(draw_node_id)

        if not ordered_struct_ids:
            return self.node_struct_ids.sorted('id')

        node_map = {node.id: node for node in self.node_struct_ids}
        return self.env['node.struct'].browse(
            [node_id for node_id in ordered_struct_ids if node_id in node_map]
        )

    def _get_test_graph_issues(self):
        """Return {node.struct id: error message} for disconnected branches, for test mode."""
        self.ensure_one()
        flow_data = self.flow_data or {}
        drawflow = flow_data.get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        nodes = home.get('data', {}) or {}
        if not nodes:
            return {}

        is_generic_reusable = bool(self.is_reusable and self.reuse_scope == 'generic')
        executable_nodes = {}
        trigger_draw_ids = []
        adjacency = defaultdict(list)
        incoming_counts = defaultdict(int)
        model_reuse_roots = set()

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            if node_data.get('type') == 'model':
                continue
            draw_key = str(draw_node_id)
            executable_nodes[draw_key] = node_data
            adjacency.setdefault(draw_key, [])
            if node_data.get('type') == 'action':
                trigger_draw_ids.append(draw_key)

        if not executable_nodes:
            issues = {}
            for node_data in (draw_node.get('data') or {} for draw_node in nodes.values()):
                struct_id = node_data.get('nodeId')
                if struct_id:
                    issues[int(struct_id)] = _(
                        "Add at least one trigger and connect it to a workflow step before testing."
                    )
            return issues

        for draw_node_id, draw_node in nodes.items():
            node_data = draw_node.get('data') or {}
            if node_data.get('type') == 'model':
                outputs = draw_node.get('outputs', {}) or {}
                for output in outputs.values():
                    for connection in output.get('connections', []) or []:
                        target_id = str(connection.get('node'))
                        target_node = nodes.get(target_id, {}) or {}
                        target_data = target_node.get('data') or {}
                        if (
                            target_data.get('type') == 'action_to_do' and
                            target_data.get('name') == 'Reuse Automation'
                        ):
                            model_reuse_roots.add(target_id)
                continue
            draw_key = str(draw_node_id)
            outputs = draw_node.get('outputs', {}) or {}
            for output in outputs.values():
                for connection in output.get('connections', []) or []:
                    target_id = str(connection.get('node'))
                    target_node = nodes.get(target_id, {}) or {}
                    target_data = target_node.get('data') or {}
                    if target_data.get('type') == 'model' or target_id not in executable_nodes:
                        continue
                    adjacency[draw_key].append(target_id)
                    incoming_counts[target_id] += 1

        issues = {}
        direct_reuse_root_ids = [
            draw_node_id for draw_node_id, node_data in executable_nodes.items()
            if (
                node_data.get('type') == 'action_to_do' and
                node_data.get('name') == 'Reuse Automation' and
                draw_node_id in model_reuse_roots
            )
        ]

        if not trigger_draw_ids and not direct_reuse_root_ids and not is_generic_reusable:
            for node_data in executable_nodes.values():
                struct_id = node_data.get('nodeId')
                if struct_id:
                    issues[int(struct_id)] = _("Add at least one trigger before testing the workflow.")
            return issues

        if is_generic_reusable:
            root_draw_ids = [
                draw_node_id for draw_node_id in executable_nodes
                if incoming_counts.get(draw_node_id, 0) == 0
            ]
            if not root_draw_ids and executable_nodes:
                root_draw_ids = [next(iter(executable_nodes))]
            if len(root_draw_ids) > 1:
                for draw_node_id in root_draw_ids:
                    node_data = executable_nodes[draw_node_id]
                    struct_id = node_data.get('nodeId')
                    label = node_data.get('label') or node_data.get('name') or _("Node")
                    if struct_id:
                        issues[int(struct_id)] = _(
                            "%s is disconnected from the reusable workflow. Connect it before testing."
                        ) % label
                return issues
        else:
            root_draw_ids = list(dict.fromkeys(trigger_draw_ids + direct_reuse_root_ids))

        reachable = set()

        def _visit(draw_node_id):
            draw_key = str(draw_node_id)
            if draw_key in reachable:
                return
            reachable.add(draw_key)
            for child_id in adjacency.get(draw_key, []):
                _visit(child_id)

        for root_draw_id in root_draw_ids:
            _visit(root_draw_id)

        if not is_generic_reusable:
            for trigger_draw_id in trigger_draw_ids:
                if adjacency.get(trigger_draw_id):
                    continue
                struct_id = executable_nodes[trigger_draw_id].get('nodeId')
                label = (
                    executable_nodes[trigger_draw_id].get('label')
                    or executable_nodes[trigger_draw_id].get('name')
                    or _("Trigger")
                )
                if struct_id:
                    issues[int(struct_id)] = _("%s is not connected to any workflow step.") % label

        for draw_node_id, node_data in executable_nodes.items():
            if node_data.get('type') == 'action':
                continue
            if draw_node_id in reachable:
                continue
            struct_id = node_data.get('nodeId')
            label = node_data.get('label') or node_data.get('name') or _("Node")
            if struct_id:
                issues[int(struct_id)] = _(
                    "%s is disconnected from the workflow. Connect it to a trigger path before testing."
                ) % label

        return issues

    def dry_run(self):
        """Validate workflow nodes without executing side effects; return a results summary dict."""
        self.ensure_one()
        is_generic_reusable = bool(self.is_reusable and self.reuse_scope == 'generic')
        if not self.is_record_saved:
            raise exceptions.ValidationError(
                _("Save the workflow before running a test.")
            )
        if not is_generic_reusable and not self.model_id:
            raise exceptions.ValidationError(
                _("Select an object before running a test.")
            )

        results = []
        counts = {
            'success': 0,
            'error': 0,
            'warning': 0,
        }
        flow_nodes = {}
        drawflow = (self.flow_data or {}).get('drawflow', {}) or {}
        home = drawflow.get('Home', {}) or {}
        if not (home.get('data') or {}):
            raise exceptions.ValidationError(
                _("Add at least one trigger and connect it to a workflow step before testing.")
            )
        for draw_node in (home.get('data', {}) or {}).values():
            node_data = draw_node.get('data') or {}
            struct_id = node_data.get('nodeId')
            if struct_id:
                flow_nodes[int(struct_id)] = node_data
        graph_issues = self._get_test_graph_issues()

        external_nodes = {'Mail', 'SMS', 'WhatsApp', 'Window', 'Webhook'}
        trigger_labels = {'On Create', 'On Write', 'On Unlink', 'On Field Change', 'On Time'}

        def _is_empty(value):
            if value in (False, None):
                return True
            if isinstance(value, str):
                return not value.strip()
            if isinstance(value, (list, tuple, dict, set)):
                return len(value) == 0
            return False

        def _has_configured_create_value(entry):
            if not isinstance(entry, dict):
                return not _is_empty(entry)
            value_key = 'field_value' if 'field_value' in entry else 'value'
            if value_key not in entry:
                return False
            value = entry.get(value_key)
            field_type = entry.get('type')
            if field_type == 'boolean':
                return True
            if field_type in ('integer', 'float', 'monetary'):
                return value not in (None, False, '')
            return not _is_empty(value)

        def _get_create_validation(node):
            required_fields = node.create_required_field or []
            provided = node.create_req_fields_values or []
            tree_values = node.create_tree_fields_values or []

            if not node.model_id:
                return 'error', _("Select a model to create records.")

            if not required_fields:
                if provided or tree_values:
                    return 'success', _("Create values configured.")
                return 'error', _("Add at least one field to create.")

            filled_names = set()
            for entry in provided:
                if not isinstance(entry, dict):
                    continue
                field_name = (
                    entry.get('name') or entry.get('field_name') or
                    entry.get('technical_name') or entry.get('value')
                )
                if field_name and _has_configured_create_value(entry):
                    filled_names.add(field_name)

            for field in required_fields:
                if not isinstance(field, dict):
                    continue
                field_name = (
                    field.get('name') or field.get('field_name') or
                    field.get('technical_name')
                )
                if field_name and _has_configured_create_value(field):
                    filled_names.add(field_name)

            missing = []
            for field in required_fields:
                if isinstance(field, dict):
                    field_name = (
                        field.get('name') or field.get('field_name') or
                        field.get('technical_name')
                    )
                else:
                    field_name = field
                if field_name and field_name not in filled_names:
                    missing.append(field_name)
            if not missing:
                return 'success', _("Create values configured.")

            if tree_values:
                return (
                    'warning',
                    _("Required create fields are missing in test input: %s. Node was simulated without creating data.") % ', '.join(missing)
                )

            return (
                'warning',
                _("Mandatory create fields are not mapped for test mode: %s. Add sample values to fully validate this node.") % ', '.join(missing)
            )

        def _validate_node(node):
            label = node.label or node.name or _("Node")
            node_name = node.name or ''
            flow_node = flow_nodes.get(node.id, {})
            flow_node_type = flow_node.get('type')

            if node.id in graph_issues:
                return 'error', graph_issues[node.id]

            if node.type == 'model':
                return 'success', _("Object selected.")
            if node.type in ('action', 'trigger') or flow_node_type == 'action':
                trigger_type = node.trigger_type or flow_node.get('trigger_type')
                trigger_label = node.ttype or flow_node.get('ttype') or node_name
                model_info = flow_node.get('model')
                has_function_link = (
                    isinstance(model_info, (list, tuple)) and bool(model_info and model_info[0])
                ) or (
                    isinstance(model_info, dict) and bool(model_info.get('id'))
                )
                if trigger_type or trigger_label in trigger_labels or has_function_link:
                    return 'success', _("Trigger configured.")
                return 'error', _("Select a trigger type.")
            if node_name == 'Window':
                if node.window_action_id:
                    return 'success', _("Window action configured.")
                return 'error', _("Select a window action to open.")
            if node_name in external_nodes:
                return 'success', _("Validated in test mode. It will execute during real workflow runtime.")
            if node_name == 'Condition':
                if not _is_empty(node.condition_tree_value):
                    return 'success', _("Condition configured.")
                return 'error', _("Add a condition before testing.")
            if node_name == 'Loop':
                if not _is_empty(node.loop_collection):
                    return 'success', _("Loop source configured.")
                return 'error', _("Choose a loop collection.")
            if node_name == 'Create':
                return _get_create_validation(node)
            if node_name == 'Write':
                if node.model_id and not _is_empty(node.write_field_value):
                    return 'success', _("Write target configured.")
                return 'error', _("Select a model and add at least one field to write.")
            if node_name == 'Variable':
                if node.variable_name and not _is_empty(node.variable_value):
                    return 'success', _("Variable configured.")
                return 'error', _("Set both variable name and value.")
            if node_name == 'Activity':
                if not _is_empty(node.activity_type) and not _is_empty(node.activity_user):
                    return 'success', _("Activity configured.")
                return 'error', _("Select an activity type and responsible user.")
            if node_name == 'Warning':
                if node.warning_type and node.warning_text:
                    return 'success', _("Warning configured.")
                return 'error', _("Add a warning type and message.")
            if node_name == 'Search':
                return 'success', _("Search configured.")
            if node_name == 'Code':
                if _is_empty(node.code_code):
                    return 'error', _("Add Python code to validate.")
                code = node.code_code.strip()
                try:
                    compile(code, '<workflow_test>', 'exec')
                except Exception as exc:
                    return 'error', _("Code syntax error: %s") % exc

                known_names = {
                    'current_record', 'current_company', 'current_user',
                    'current_date', 'current_datetime', 'env', 'model',
                    'records', 'record', 'UserError', 'ValidationError',
                    'uid', 'user', 'time', 'datetime', 'dateutil',
                    'relativedelta', 'fields', '_logger', 'requests', 'json', 'action',
                }
                known_names |= {
                    v.get('variable_name') for v in (self.variables or [])
                    if isinstance(v, dict) and v.get('variable_name')
                }

                try:
                    messages = _check_code_with_ast(code, known_names)
                except SyntaxError:
                    messages = []  # already caught by compile() above
                except Exception as exc:
                    _logger.warning("Code node AST check failed to run: %s", exc)
                    messages = []
                if messages:
                    return 'warning', _("Possible issue(s): %s") % '; '.join(messages)

                return 'success', _("Code syntax is valid.")
            if node_name == 'Button Click':
                if not _is_empty(node.function_name):
                    return 'success', _("Function configured.")
                return 'error', _("Select a function to call.")
            if node_name == 'Reuse Automation':
                reused = node.reused_work_auto_id
                if reused and reused.active:
                    return 'success', _("Reusable automation is available.")
                return 'error', _("Select an active reusable automation.")
            if node_name == 'Follower':
                if not _is_empty(node.followers):
                    return 'success', _("Followers configured.")
                return 'error', _("Select at least one follower.")
            if node_name == 'Duplicate':
                if not _is_empty(node.duplicate_record):
                    return 'success', _("Duplicate record configured.")
                return 'error', _("Select a record to duplicate.")
            if node_name == 'Webhook':
                if _is_empty(node.webhook_url):
                    return 'error', _("Webhook URL is required.")
                action_count = len(node.webhook_actions or [])
                if action_count:
                    return 'success', _(
                        "Webhook configured with %d response action(s)."
                    ) % action_count
                return 'success', _("Webhook configured (no response actions).")
            if node_name == 'Try Catch':
                err_var = (node.try_catch_error_variable or '').strip()
                err_types = (node.try_catch_error_types or '').strip()
                if not err_var:
                    return 'error', _("Set an error variable name for the Try/Catch node.")
                if not err_types:
                    return 'error', _("Specify at least one exception type to catch.")
                return 'success', _(
                    "Try/Catch configured — catches %s as '%s'."
                ) % (err_types, err_var)
            if node.code and node.code.strip():
                return 'success', _("%s configured.") % label
            return 'error', _("%s is not configured.") % label

        node_order = self._get_test_node_order()
        record_info = False

        try:
            with self.env.cr.savepoint():
                recordset = self.env[self.model_id.model].search([], limit=1) if self.model_id else self.env['res.partner'].browse()
                if recordset:
                    record_info = {
                        'id': recordset.id,
                        'display_name': recordset.display_name,
                    }

                for node in node_order:
                    start_time = time.perf_counter()
                    status, message = _validate_node(node)
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    counts[status] = counts.get(status, 0) + 1
                    results.append({
                        'node_id': node.id,
                        'name': node.name,
                        'label': node.label or node.name,
                        'status': status,
                        'message': message,
                        'duration_ms': duration_ms,
                    })
                raise exceptions.UserError("__cyllo_test_workflow_rollback__")
        except exceptions.UserError as exc:
            if exc.args and exc.args[0] != "__cyllo_test_workflow_rollback__":
                raise

        return {
            'results': results,
            'summary': {
                'total': len(results),
                'success': counts.get('success', 0),
                'error': counts.get('error', 0),
                'warning': counts.get('warning', 0),
            },
            'record': record_info,
        }

    @api.depends('flow_data')
    def _compute_trigger_functions(self):
        """Set `trigger_function_ids` from the function IDs extracted from `flow_data`."""
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            automation.trigger_function_ids = self.env['work.function'].browse(function_ids)

    @api.constrains('trigger_function_ids')
    def _check_unique_trigger_types(self):
        """
            Raise a ValidationError if two of the workflow's trigger functions
            share the same trigger type.
            """
        for automation in self:
            trigger_types = [
                fn.trigger_type for fn in automation.trigger_function_ids if fn.trigger_type
            ]
            duplicates = [t for t in set(trigger_types) if trigger_types.count(t) > 1]
            if duplicates:
                duplicate_type = duplicates[0]
                trigger = automation.trigger_function_ids.filtered(
                    lambda f: f.trigger_type == duplicate_type
                )
                trigger_name = trigger and trigger[0].name or duplicate_type
                raise exceptions.ValidationError(
                    _("Trigger %s is already part of this automation. "
                      "Each trigger type can only be used once.") % trigger_name
                )

    def initial_model_setup(self):
        """
            Return a list of setup dicts describing this workflow's primary model
            and Search nodes.
            """
        data = []
        for node in self.node_struct_ids:
            if node.name in ['model', 'Search']:
                data.append({
                    'id': int(node.id) if node.name == 'Search' else 0,
                    'model_id': int(node.model_id),
                    'type': 'primary' if node.name == 'model' else 'Search'
                })
        return data

    def getDefaultImage1920(self):
        """Read the module's default SVG image and return it base64-encoded."""
        with file_open(
                'cyllo_workflow_automation/static/src/img/Record/default_record.svg',
                'rb') as svg_file:
            svg_data = svg_file.read()
            return base64.b64encode(svg_data).decode('utf-8')

    def _register_hook(self):
        """
        Register this workflow's automation hooks on its target model: append onchange
        handlers to Model._onchange_methods, and patch create/write/unlink as needed.
        """
        patched_models = defaultdict(set)
        patched_function_ids = set()
        # Accumulates (auto_id, field_name) per model for write()-level field-change hooks.
        # Keyed by model name; populated in the field_change block below, then
        # patched after the main automation loop.
        field_change_write_specs = defaultdict(list)

        def patch(model, name, method):
            """Patch method `name` on `model` unless already patched this run.

            _register_hook() re-runs on every registry rebuild (server
            restart, module upgrade, ...). Without unwinding prior layers,
            `.origin` would point at our own previously-installed wrapper
            instead of the true ORM method, stacking one extra automation
            run per rebuild -- since the generated function body calls
            `.origin(...)` *after* firing `_process()`, each stale layer
            fires the automation again, multiplying every Create/Write
            trigger (e.g. duplicate Mail/WhatsApp sends) by the number of
            rebuilds since the server started.
            """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                current = getattr(ModelClass, name, None)
                while getattr(current, '_is_workflow_patch', False):
                    current = current.origin
                method.origin = current
                method._is_workflow_patch = True
                setattr(ModelClass, name, method)

        def make_button_click_method(function):
            func_name = function.func_name

            def button_click(self, *args, **kwargs):
                guard_key = f'_workflow_{func_name}_running_' + self._name
                if self.env.context.get(guard_key):
                    return False
                automation_ids = self.env['work.auto']._get_actions(self, func_name)
                before_ids = automation_ids.filtered(lambda x: x.ttype == 'before')
                action_result = False
                for automation in before_ids.with_context(old_values=None):
                    res = automation._process({'records': self, 'trigger_type': 'button_click'})
                    if isinstance(res, dict) and 'type' in res:
                        action_result = res
                after_ids = automation_ids - before_ids
                for automation in after_ids.with_context(old_values=None):
                    res = automation._process({'records': self, 'trigger_type': 'button_click'})
                    if isinstance(res, dict) and 'type' in res:
                        action_result = res
                return action_result or False

            button_click.__name__ = func_name
            return button_click

        for auto in self.with_context(active_test=False).search([('active', '=', True)]):
            functions = auto.trigger_function_ids
            if not functions:
                continue
            Model = self.env.get(auto.model_id.model)
            if Model is None:
                _logger.warning(
                    "Automation '%s' (ID %d) depends on model %s which does not exist.",
                    auto.name, auto.id,
                    auto.model_id.model if auto.model_id else 'unknown',
                )
                continue

            # ── On Field Change ───────────────────────────────────────────────
            field_change_functions = functions.filtered(
                lambda f: f.trigger_type == 'field_change'
            )
            if field_change_functions:
                if not auto.field_id:
                    _logger.warning(
                        "Automation '%s' (ID %d) has a field-change trigger but "
                        "no 'field_id' configured — skipping.",
                        auto.name, auto.id,
                    )
                else:
                    field_name = auto.field_id.name

                    def make_onchange_fn(watched_auto, watched_field):
                        def on_change_field(rec):
                            """Only fire for existing saved records: skip when rec._origin
                            has no real DB record, to avoid errors blocking record creation."""
                            origin = getattr(rec, '_origin', None)
                            if not origin or not origin.id:
                                return

                            # Pass origin (the real saved record) so that
                            # current_record in generated code points to the
                            # actual DB record, not the virtual copy.
                            # trigger_type enables the per-branch code guard.
                            auto_live = watched_auto.with_env(rec.env)
                            try:
                                with rec.env.cr.savepoint():
                                    auto_live._process({
                                        'record': origin,
                                        'records': origin,
                                        'trigger_type': 'field_change',
                                    })
                            except (exceptions.ValidationError, exceptions.UserError):
                                raise  # Surface error/warning dialogs to the form
                            except Exception as exc:
                                _logger.error(
                                    "Field-change automation '%s' failed "
                                    "for record %s on field '%s': %s",
                                    watched_auto.name, origin.id, watched_field, exc,
                                )
                        on_change_field._is_workflow_automation = True
                        return on_change_field

                    # Remove stale handlers before re-appending to prevent
                    # accumulation across multiple _update_registry() calls.
                    existing = Model._onchange_methods.get(field_name, [])
                    Model._onchange_methods[field_name] = [
                        fn for fn in existing
                        if not getattr(fn, '_is_workflow_automation', False)
                    ]
                    Model._onchange_methods[field_name].append(
                        make_onchange_fn(auto, field_name)
                    )
                    # Also register a write()-level hook so the automation fires
                    # when the field changes via ORM (e.g. action_confirm sets
                    # state='sale') — not just via UI onchange.
                    field_change_write_specs[auto.model_id.model].append(
                        (auto.id, field_name)
                    )

            # ── Create / Write / Unlink and other ORM triggers ────────────────
            for function in functions.filtered(
                lambda f: f.trigger_type not in ('field_change', 'time')
            ):
                if function.trigger_type == 'button_click' or self.env['work.function']._is_studio_workflow_func_name(function.func_name):
                    func = make_button_click_method(function)
                else:
                    if not function.c_make_function:
                        continue
                    try:
                        code_obj = compile(function.c_make_function, '<string>', 'exec')
                        inner = next(
                            (c for c in code_obj.co_consts if hasattr(c, 'co_code')),
                            None,
                        )
                        if inner is None:
                            _logger.warning(
                                "_register_hook: no code object found in compiled "
                                "c_make_function for '%s' — skipping.",
                                function.func_name,
                            )
                            continue
                        func = types.FunctionType(inner, globals(), function.func_name)()
                    except Exception as e:
                        _logger.error(
                            "_register_hook: failed to compile/build method '%s': %s",
                            function.func_name, e,
                        )
                        continue
                patch(Model, function.func_name, func)
                patched_function_ids.add(function.id)

        for function in self.env['work.function'].with_context(active_test=False).search([]):
            if function.id in patched_function_ids or not function.model_id:
                continue
            if not (
                function.trigger_type == 'button_click'
                or self.env['work.function']._is_studio_workflow_func_name(function.func_name)
            ):
                continue
            Model = self.env.get(function.model_id.model)
            if Model is None:
                continue
            func = make_button_click_method(function)
            patch(Model, function.func_name, func)

        # ── Patch write() for field_change automations ────────────────────────
        # The _onchange_methods hook only fires via the form-view RPC.
        # Fields that change via ORM (e.g. sale order state via action_confirm)
        # require a write() patch to fire the automation.
        def make_field_change_write_fn(all_specs):
            def _field_change_write(self, vals):
                result = _field_change_write.origin(self, vals)
                for auto_id, watched_field in all_specs:
                    if watched_field not in vals:
                        continue
                    automation = self.env['work.auto'].browse(auto_id)
                    if not automation.exists() or not automation.active:
                        continue
                    for rec in self:
                        if not rec.id:
                            continue
                        try:
                            automation._process({
                                'record': rec,
                                'records': rec,
                                'trigger_type': 'field_change',
                            })
                        except (exceptions.ValidationError, exceptions.UserError):
                            raise
                        except Exception as exc:
                            _logger.error(
                                "Field-change (write) automation '%s' failed "
                                "for record %s on field '%s': %s",
                                automation.name, rec.id, watched_field, exc,
                            )
                return result
            _field_change_write._is_workflow_field_change_write = True
            return _field_change_write

        for fc_model_name, specs in field_change_write_specs.items():
            FCModel = self.env.get(fc_model_name)
            if FCModel is None:
                continue
            FCModelClass = type(FCModel)
            # Strip any previously installed field_change write patch so we
            # don't stack patches across _update_registry() calls.
            current_write = getattr(FCModelClass, 'write', None)
            while getattr(current_write, '_is_workflow_field_change_write', False):
                current_write = current_write.origin
            new_write = make_field_change_write_fn(specs)
            new_write.origin = current_write
            setattr(FCModelClass, 'write', new_write)

        return super()._register_hook()

    def get_dependents(self):
        """
        Return [{'id': int, 'name': str}, ...] for all active automations that reference
        this reusable automation via a 'Reuse Automation' node.
        """
        self.ensure_one()
        dependent_nodes = self.env['node.struct'].sudo().search([
            ('reused_work_auto_id', '=', self.id),
        ])
        dependent_autos = dependent_nodes.mapped('work_auto_id').filtered(
            lambda a: a.active and a.id != self.id
        )
        return [{'id': a.id, 'name': a.name} for a in dependent_autos]

    @api.model
    def _get_actions(self, record, func):
        """
           Return the active workflow automations that trigger function `func` on
           `record`'s model.
           """
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', record._name)], limit=1
        )
        function_ids = self.env['work.function'].sudo().search([
            ('model_id', 'in', [model_id.id, False]),
            ('func_name', '=', func),
        ])
        if not model_id or not function_ids:
            return self
        auto_ids = self.sudo().search([
            ('model_id', '=', model_id.id),
            ('active', '=', True),
            ('trigger_function_ids', 'in', function_ids.ids),
        ])
        return auto_ids.with_env(self.env)

    def _process(self, args: dict):
        """
            Execute this workflow's generated code for `args`, guarding against circular
            reuse, duplicate triggers, and missing write access.
            """
        # ── Active guard for reuse calls ──────────────────────────────────────
        # If this automation is invoked as a reusable automation from another
        # workflow, check self.active first. If it has been deactivated, skip
        # silently so the parent workflow continues uninterrupted.
        _pre_stack = args.get('__workflow_stack__', [])
        if _pre_stack and not self.active:
            _logger.warning(
                "Reusable automation '%s' (ID %d) is inactive — skipping reuse call "
                "from stack %s.",
                self.name, self.id, _pre_stack,
            )
            return

        # ── Reuse-guard: block circular automation chains ─────────────────────
        stack = args.get('__workflow_stack__', [])
        if not isinstance(stack, list):
            stack = list(stack)
        if self.id in stack:
            raise exceptions.ValidationError(
                _('Circular automation reuse detected for %s.', self.name)
            )
        stack = [*stack, self.id]
        args = dict(args, __workflow_stack__=stack)

        incoming_trigger = args.get('trigger_type', '')
        records = args.get('records', False)

        # ── Normalise time-trigger args ───────────────────────────────────────
        # Scheduled workflows are attached to a model but don't receive an
        # incoming recordset from ir.cron. Resolve the workflow model records so
        # downstream nodes such as Activity can operate on actual records.
        if incoming_trigger == 'time' and not records and self.model_id:
            model_name = self.model_id.sudo().model
            records = self.env[model_name].search([])
            args = dict(args, records=records, current_record=records)

        # ── Empty recordset safety guard ──────────────────────────────────────
        # Skip execution of triggers if the recordset is empty (no records).
        # This prevents Expected singleton or access errors in downstream nodes
        # when background actions write to empty recordsets.
        if hasattr(records, '_name') and not records:
            _logger.info(
                "Skipping workflow automation '%s' (ID %d) because the target recordset is empty.",
                self.name, self.id
            )
            return

        # ── Transaction-level dedup (create / write / unlink / field_change / time) ──
        # Prevents N duplicate actions when write() is triggered multiple times
        # per single form save (computed fields, chatter, state machine).
        # field_change USED to be excluded here on the assumption that it only
        # ever fires once, from the onchange RPC. That's no longer true: this
        # model also patches write() to fire the same field_change automation
        # when the watched field changes via plain ORM writes (see
        # make_field_change_write_fn below) -- so a normal UI edit-then-save
        # fires it twice (once from onchange while editing, once from write()
        # on save), duplicating any real side effect like a Mail/WhatsApp
        # send. Both calls carry the same (self.id, rec_ids, trigger_type),
        # so including field_change here collapses them to one run.
        # Only dedup top-level automations (direct ORM triggers).
        # Reusable automations called from another automation have a non-empty
        # __workflow_stack__ — skip dedup for them so they always execute.
        #
        # This guard used to require `records` to be truthy, which silently
        # exempted recordless time-triggered automations (a scheduled workflow
        # with no model_id, e.g. "email this report every day") from dedup
        # entirely -- since _run_time_trigger/_process for those never sets
        # `records`. If the cron fired more than once close together (two
        # workers picking up the same overdue job, or a second cron tick
        # landing before a slow report-generating run had committed and
        # recorded itself in _RECENT_AUTOMATION_RUNS), every extra fire sent
        # its own duplicate email with no guard to stop it. Keying on an empty
        # rec_ids tuple when there are no records closes that gap.
        is_reuse_call = len(stack) > 1  # stack has at least [parent_id, self.id]
        if incoming_trigger and not is_reuse_call:
            cr = self.env.cr
            if not hasattr(cr, '_workflow_done'):
                cr._workflow_done = set()
            try:
                rec_ids = tuple(sorted(records._ids)) if records else ()
            except Exception:
                rec_ids = ()
            dedup_key = (self.id, rec_ids, incoming_trigger)
            if dedup_key in cr._workflow_done:
                return
            cr._workflow_done.add(dedup_key)
            # Also guard across separate transactions (see _recently_ran doc).
            if _recently_ran(dedup_key):
                _logger.info(
                    "Skipping duplicate run of workflow automation '%s' (ID %d) "
                    "for record(s) %s — already ran within the last %ds.",
                    self.name, self.id, rec_ids, _RECENT_AUTOMATION_RUN_TTL,
                )
                return
            if incoming_trigger == 'field_change':
                # The onchange RPC call always rolls back its own transaction
                # by design (onchange never persists DB changes), so a
                # cr.postcommit callback registered here would never run --
                # leaving the later write()-on-Save call for the same field
                # change completely undeduped. Mark immediately instead: any
                # real side effect (e.g. the WhatsApp/Mail send further down
                # in this call) is external to the SQL transaction anyway, so
                # it isn't undone by that rollback either.
                _mark_ran(dedup_key)
            else:
                cr.postcommit.add(functools.partial(_mark_ran, dedup_key))

        # ── Access check (skip for field_change and unlink) ───────────────────
        # field_change passes a virtual onchange record — checking write access
        # on a virtual record raises errors. Skip it.
        if records and incoming_trigger not in ('field_change', 'unlink'):
            try:
                records.check_access_rule('write')
            except AccessError:
                _logger.warning(
                    "Forbidden action %r executed while the user %s does not "
                    "have access to %s.",
                    self.name, self.env.user.login, records
                )
                raise

        # ── Normalise field_change args ───────────────────────────────────────
        # on_change_field passes {'record': rec} (singular).
        # Inject 'records' and 'current_record' so the generated code can use
        # either alias.
        single_record = args.get('record', False)
        if single_record and not records:
            args = dict(args)
            args['records'] = single_record
            args['current_record'] = single_record

        # ── Reuse call trigger override ───────────────────────────────────────
        # When this automation is called as a reuse call from another workflow,
        # the frontend sends the REUSED automation's own trigger_type as a
        # literal string (e.g. 'create' for an On-Create automation).
        #
        # Backend safety net: if the incoming trigger is the sentinel value
        # '__reuse__' (used for generic reusable automations that have no
        # trigger), we override it with self.trigger_type so the internal code
        # guard matches correctly. If self.trigger_type is also empty (truly
        # generic), we set it to '__reuse__' which simply won't match any
        # `if trigger_type == 'create':` guard — that is correct because
        # generic reusable code is generated WITHOUT a trigger guard at all.
        #
        # For non-generic reusables where the frontend correctly passes the
        # reused automation's trigger_type (e.g. 'create'), no override is
        # needed — the guard will match as expected.
        if is_reuse_call and incoming_trigger == '__reuse__':
            # Generic reusable: override with the automation's own trigger_type.
            # If self.trigger_type is False/empty, keep '__reuse__' as-is
            # (harmless since generic code has no trigger guard).
            effective_trigger = self.trigger_type or '__reuse__'
            args = dict(args, trigger_type=effective_trigger)
            incoming_trigger = effective_trigger

        # Resolve records now (may have been set by normalise block above)
        resolved_records = args.get('records', False)
        context = self.get_context(records=resolved_records)
        context.update(args)
        context['trigger_type'] = args.get('trigger_type')
        context.update(_BUILTINS)

        def _safe_schedule_activity(rec, **kwargs):
            """Schedule an activity only for real DB records (id > 0)."""
            if not rec:
                return False
            valid = rec.filtered(lambda r: isinstance(r.id, int) and r.id > 0)
            if not valid:
                return False
            return valid.activity_schedule(**kwargs)

        context['_safe_schedule_activity'] = _safe_schedule_activity

        if self.code:
            # Queue mail instead of immediate SMTP send for all workflows
            # (handles legacy code that was generated with force_send=True)
            patched_code = self.code.replace('force_send=True', 'force_send=False')
            try:
                code_obj = compile(patched_code.strip(), "", 'exec')
                local_dict = {}
                eval(code_obj, context, local_dict)
                if 'action' in local_dict:
                    context['action'] = local_dict['action']
            except Exception as e:
                import traceback as _tb
                _logger.error(
                    "Workflow '%s' code execution error:\n%s",
                    getattr(self, 'name', '?'),
                    _tb.format_exc()
                )
                err_str = str(e)
                if 'mail_activity_check_res_id_is_set' in err_str or (
                    'mail_activity' in err_str and 'res_id' in err_str
                ):
                    _logger.warning(
                        "Workflow '%s' tried to schedule an activity with "
                        "res_id=0 — re-save the workflow to fix this.",
                        self.name
                    )
                    return
                if isinstance(
                    e,
                    (
                        exceptions.UserError,
                        exceptions.ValidationError,
                        exceptions.AccessError,
                        exceptions.AccessDenied,
                        exceptions.MissingError,
                    ),
                ):
                    # Re-raise as-is: this is a deliberately-authored message
                    # (e.g. from a Warning Node), so the popup should show
                    # exactly that text under its heading, with no prefix.
                    # Which workflow raised it is already captured above by
                    # _logger.error() for anyone debugging server-side.
                    raise
                raise exceptions.ValidationError(
                    _("%s\n\n(Workflow Automation: %s)") % (e, self.name)
                )
            
            return context.get('action')

    def get_context(self, records=None):
        """
            Build the dict of env, model, record aliases, and safe helpers that generated
            workflow code executes against.
            """
        if self.is_reusable and self.reuse_scope == 'generic' and records:
            model = records
        elif self.model_id:
            model = self.env[self.model_id.sudo().model]
        else:
            model = self.env['res.partner']  # safe fallback
        rec = records if records else model.browse()
        if hasattr(rec, '_name') and len(rec) > 1:
            rec = rec[:1]

        return {
            'env': self.env,
            'model': model,
            'records': records,
            'record': rec,
            'current_record': rec,
            'UserError': exceptions.UserError,
            'ValidationError': exceptions.ValidationError,
            'uid': self._uid,
            'user': self.env.user,
            'current_user': self.env.user,
            'current_company': self.env.company,
            'current_date': fields.Date.today(),
            'current_datetime': fields.Datetime.now(),
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            'relativedelta': relativedelta,
            'fields': fields,
            '_logger': _logger,
            'requests': _requests_lib,
            'json': _json_lib,
        }

    @api.model
    def create(self, vals_list):
        """
            Create the workflow automation record(s), then suffix the name with the id,
            set up its cron job, and refresh the registry.
            """
        res = super().create(vals_list)
        res.name = f"{res.name}-({res.id})"
        res.create_cron()
        res._update_registry()
        return res

    def write(self, vals):
        """
            Update the workflow automation record(s): validate reusable-workflow constraints,
            then refresh the cron job, registry, and trigger functions as needed.
            """
        # ── Guard: cannot deactivate a reusable automation that is in use ──
        # Only raises if active is explicitly set to False AND the automation
        # is reusable AND other active workflows depend on it.
        if vals.get('active') is False:
            for automation in self:
                if not automation.is_reusable:
                    continue
                dependents = automation.get_dependents()
                if dependents:
                    dep_names = ', '.join(d['name'] for d in dependents)
                    raise exceptions.ValidationError(_(
                        "Cannot deactivate '%(name)s' because it is used as a "
                        "reusable automation in the following active workflow(s): "
                        "%(deps)s. "
                        "Please remove or disconnect the 'Reuse Automation' node(s) "
                        "in those workflows first.",
                        name=automation.name,
                        deps=dep_names,
                    ))

        res = super().write(vals)
        time_fields = {
            'time_trigger_mode', 'time_trigger_time',
            'time_trigger_day', 'time_trigger_month',
            'time_trigger_weekday', 'active',
        }
        trigger_link_fields = {'function_id', 'trigger_function_ids'}
        if (time_fields | trigger_link_fields) & vals.keys():
            self.create_cron()
        self._update_registry()
        if 'flow_data' in vals:
            self._update_primary_function()
        return res

    def _update_primary_function(self):
        """
            Update the primary trigger function of the workflow.

            Sets the first extracted trigger function as the main function.
            """
        for automation in self:
            function_ids = automation._extract_trigger_function_ids_from_flow(automation.flow_data)
            new_function_id = function_ids[0] if function_ids else False
            # Use super().write() to bypass WorkAuto.write() override and avoid
            # triggering a recursive _update_registry() / create_cron() cycle.
            super(WorkAuto, automation).write({'function_id': new_function_id})

    def unlink(self):
        """Delete this workflow's cron jobs and node structures, then the record itself."""
        self.mapped('schedule_id').sudo().unlink()
        self.mapped('node_struct_ids').unlink()
        return super().unlink()

    def _unregister_hook(self):
        """
        Undo the ORM patches installed by _register_hook() by restoring each patched
        method's `.origin` on its ModelClass. Does not touch _onchange_methods.
        """
        try:
            NAMES = self.env['work.function'].search([]).mapped('func_name')
        except Exception as e:
            _logger.warning("_unregister_hook: could not fetch function names (transaction may be aborted): %s", e)
            return
        for ModelClass in self.env.registry.values():
            for name in NAMES:
                if name in ModelClass.__dict__:
                    try:
                        patched_fn = ModelClass.__dict__[name]
                        origin = getattr(patched_fn, 'origin', None)
                        if origin is not None:
                            setattr(ModelClass, name, origin)
                        else:
                            delattr(ModelClass, name)
                    except Exception:
                        pass

    def _update_registry(self):
        """Re-register this workflow's ORM hooks and invalidate the registry to apply changes."""
        if not self.env.registry.ready:
            return
        # Guard against recursive calls (e.g. _update_primary_function or
        # create_cron triggering another write() → _update_registry() cycle).
        if getattr(self.env.cr, '_wf_registry_updating', False):
            return
        self.env.cr._wf_registry_updating = True
        try:
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True
        except Exception as e:
            _logger.error("_update_registry failed: %s", e)
        finally:
            self.env.cr._wf_registry_updating = False

    def run_now(self):
        """
        Execute this time-triggered workflow immediately for manual testing,
        against a single record.

        This deliberately does NOT loop over every record of the model the
        way the real scheduled cron (_run_time_trigger) does. "Run Now" is a
        manual test action a user clicks once to check the workflow works --
        looping here queued up one real send (Mail/WhatsApp/etc.) per row in
        the table, which (a) spams every real contact in the model with a
        duplicate message and (b) for WhatsApp in particular, made one
        synchronous Graph API call per record in a single HTTP request, long
        enough on any non-trivial table to blow past the worker's request
        timeout -- which kills the DB cursor mid-loop and surfaces as a
        cascade of "cursor already closed" errors for every record still
        queued behind the one that was running when the timeout hit.
        Returns a dict with 'ok', 'records_processed', 'errors' keys.
        """
        self.ensure_one()
        if not self.active:
            return {'ok': False, 'error': 'Workflow is inactive.'}
        if not self.model_id:
            try:
                with self.env.cr.savepoint():
                    self._process({'trigger_type': 'time'})
                return {'ok': True, 'records_processed': 0, 'errors': []}
            except Exception as exc:
                return {'ok': False, 'error': str(exc)}

        try:
            model_name = self.model_id.sudo().model
            test_record = self.env[model_name].search([], order='id desc', limit=1)
        except Exception as exc:
            return {'ok': False, 'error': _("Could not fetch records: %s") % exc}

        if not test_record:
            return {
                'ok': True,
                'records_processed': 0,
                'errors': [],
                'warning': _("No records found in model '%s'. Nothing to execute.") % model_name,
            }

        try:
            with self.env.cr.savepoint():
                self._process({'trigger_type': 'time', 'records': test_record})
            return {'ok': True, 'records_processed': 1, 'errors': []}
        except Exception as exc:
            return {
                'ok': True,
                'records_processed': 0,
                'errors': [_("Record %s: %s") % (test_record.id, exc)],
            }

    def create_cron(self):
        """Create or update the `ir.cron` record for this workflow's time-based trigger."""
        interval_map = {
            'hour':  (1,  'hours'),
            'day':   (1,  'days'),
            'week':  (1,  'weeks'),
            'month': (1,  'months'),
            'year':  (12, 'months'),
        }
        for rec in self:
            if rec.trigger_type != 'time' or not rec.time_trigger_mode:
                if rec.schedule_id:
                    rec.schedule_id.sudo().unlink()
                continue

            interval_number, interval_type = interval_map[rec.time_trigger_mode]

            now = fields.Datetime.now()
            hour = int(rec.time_trigger_time or 0)
            minute = round(((rec.time_trigger_time or 0) - hour) * 60)
            nextcall = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if rec.time_trigger_mode == 'week':
                weekday = int(rec.time_trigger_weekday or '0')
                weekday = max(0, min(6, weekday))
                days_ahead = (weekday - nextcall.weekday()) % 7
                nextcall += relativedelta(days=days_ahead)

            if rec.time_trigger_mode in ('month', 'year'):
                day = max(1, rec.time_trigger_day or 1)
                try:
                    nextcall = nextcall.replace(day=day)
                except ValueError:
                    import calendar
                    last_day = calendar.monthrange(nextcall.year, nextcall.month)[1]
                    nextcall = nextcall.replace(day=last_day)

            if rec.time_trigger_mode == 'year':
                month = max(1, min(12, rec.time_trigger_month or 1))
                try:
                    nextcall = nextcall.replace(month=month)
                except ValueError:
                    nextcall = nextcall.replace(month=month, day=1)

            if nextcall <= now:
                if interval_type == 'hours':
                    nextcall += relativedelta(hours=interval_number)
                elif interval_type == 'days':
                    nextcall += relativedelta(days=interval_number)
                elif interval_type == 'weeks':
                    nextcall += relativedelta(weeks=interval_number)
                elif interval_type == 'months':
                    nextcall += relativedelta(months=interval_number)

            cron_vals = {
                'name': f'Workflow Automation: {rec.name}',
                'model_id': self.env['ir.model']._get('work.auto').id,
                'state': 'code',
                'code': f"env['work.auto'].browse({rec.id})._run_time_trigger()",
                'interval_number': interval_number,
                'interval_type': interval_type,
                'nextcall': nextcall,
                'numbercall': -1,
                'active': rec.active,
                'user_id': self.env.ref('base.user_root').id,
            }

            if rec.schedule_id:
                rec.schedule_id.sudo().try_write(cron_vals)
            else:
                cron = self.env['ir.cron'].sudo().create(cron_vals)
                # Use super().write() to avoid triggering the WorkAuto.write()
                # override (and its _update_registry() call) for this
                # internal schedule_id assignment.
                super(WorkAuto, rec.sudo()).write({'schedule_id': cron.id})

    def _run_time_trigger(self):
        """
            Run this time-triggered workflow once per record of its model, so
            current_record is always a single record in the generated code.
            """
        if not self.active:
            return
        if not self.model_id:
            try:
                with self.env.cr.savepoint():
                    self._process({'trigger_type': 'time'})
            except Exception as e:
                _logger.error(
                    "Workflow Automation '%s' (id=%s) time trigger failed: %s",
                    self.name, self.id, e,
                )
            return
        try:
            model_name = self.model_id.sudo().model
            all_records = self.env[model_name].search([])
        except Exception as e:
            _logger.error(
                "Workflow Automation '%s' (id=%s) could not fetch records for model: %s",
                self.name, self.id, e,
            )
            return
        if not all_records:
            _logger.info(
                "Workflow Automation '%s' (id=%s): no records found, skipping.",
                self.name, self.id,
            )
            return
        for rec in all_records:
            try:
                # Each record gets its own savepoint: a DB-level failure (e.g.
                # a constraint violation) aborts the current SQL transaction,
                # and without a rollback boundary here every subsequent
                # record's _process() call would also fail with a cascading
                # "current transaction is aborted" error even though only
                # this one record was actually bad.
                with self.env.cr.savepoint():
                    self._process({'trigger_type': 'time', 'records': rec})
            except Exception as e:
                _logger.error(
                    "Workflow Automation '%s' (id=%s) time trigger failed for record %s: %s",
                    self.name, self.id, rec.id, e,
                )

    def copy(self, default=None):
        """
            Duplicate the workflow along with its node structures, updating the
            copied flow data to reference the new node ids.
            """
        res = super().copy()
        res.name = f"{self.name}-copy({res.id})"
        if (self.flow_data.get('drawflow') and
                self.flow_data.get('drawflow').get('Home') and
                self.flow_data.get('drawflow').get('Home').get('data')):
            flow_data = self.flow_data.get('drawflow').get('Home').get('data')
            node_copies = []
            for nid, node in flow_data.items():
                copy_node = self.env["node.struct"].browse(node['data']['nodeId']).copy()
                node_copies.append(copy_node.id)
                node['data']['nodeId'] = copy_node.id
                node['html'] = f"{node['data']['name']}__{copy_node.id}"
            data = {'drawflow': {'Home': {'data': flow_data}}}
            res.flow_data = data
            res.node_struct_ids = node_copies
        return res

    @api.model
    def parse_view_and_fetch_functions(self, model_id):
        """
            Parse `model_id`'s XML views for regular and Studio workflow buttons, and
            return a list of dicts describing each button function.
            """
        button_functions = {}
        model = self.env["ir.model"].sudo().browse(model_id)
        model_name = model.model
        views = self.env['ir.ui.view'].sudo().search([('model', '=', model_name)])
        for view in views:
            arch = view.arch_base or view.arch_db
            if not arch:
                continue
            try:
                view_arch = etree.fromstring(arch.encode('utf-8'))
            except Exception:
                continue
            # Include:
            # 1. regular object buttons
            # 2. legacy workflow buttons saved as type='workflow'
            # 3. normalized Studio workflow buttons identified by studio_wf_ name prefix
            button_nodes = view_arch.xpath(
                "//button[@type='object' or @type='workflow' or starts-with(@name, 'studio_wf_')]"
            )
            for button in button_nodes:
                button_name = button.attrib.get('name')
                if button_name:
                    button_string = (
                        button.attrib.get('string', button_name) or
                        button.attrib.get('title', button_name)
                    )
                    field_in_button = button.xpath(".//field[@string]")
                    if field_in_button:
                        button_string = field_in_button[0].attrib.get('string', button_name)
                    unique_key = f"{button_name}_{button_string}"
                    button_context = button.attrib.get('context', button_name)
                    is_studio_workflow_button = button_name.startswith('studio_wf_')
                    if button_context == button_name or is_studio_workflow_button:
                        words = button_string.split('_')
                        formatted_name = " ".join(words).capitalize()
                        button_functions[unique_key] = {
                            'model': model_name,
                            'button_function': button_name,
                            'button_string': formatted_name,
                            'button_val': unique_key,
                        }
        return list(button_functions.values())

    @api.model
    def get_actions_for_model(self, model_id):
        actions = self.env["ir.actions.server"].sudo().search_read([("binding_model_id", "=", model_id)], ["id", "name"])
        window_actions = self.env["ir.actions.act_window"].sudo().search_read([("binding_model_id", "=", model_id)], ["id", "name"])
        report_actions = self.env["ir.actions.report"].sudo().search_read([("binding_model_id", "=", model_id)], ["id", "name"])
        return actions, window_actions, report_actions
