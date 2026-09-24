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

import ast
import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class Aggregation:
    """Helper class to represent a SQL aggregation that can be merged."""
    def __init__(self, aggregate, column, filters=None):
        self.aggregate = aggregate.upper()
        self.column = column
        self.filters = filters or []

    def to_sql(self):
        if not self.filters:
            return f"{self.aggregate}({self.column})"
        # Combine filters with OR to include all records from merged periods
        combined_filter = " OR ".join(f"({f})" for f in self.filters)
        return f"{self.aggregate}({self.column}) FILTER (WHERE {combined_filter})"

    def __str__(self):
        return self.to_sql()


_ALLOWED_OPERATORS = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Pow: '^',
    ast.USub: '-',
    ast.UAdd: '+',
    # Comparisons
    ast.Eq: '=',
    ast.NotEq: '!=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Gt: '>',
    ast.GtE: '>=',
}

_ALLOWED_FUNCS = {
    'abs': 'ABS',
    'round': 'ROUND',
    'min': 'MIN',  # Default to aggregate, handled specially in _to_sql
    'max': 'MAX',  # Default to aggregate, handled specially in _to_sql
    'if': 'CASE WHEN {0} THEN {1} ELSE {2} END',
    'if_func': 'CASE WHEN {0} THEN {1} ELSE {2} END',
    'sum': 'SUM',
    'avg': 'AVG',
    'count': 'COUNT',
    'least': 'LEAST',
    'greatest': 'GREATEST',
    'coalesce': 'COALESCE',
    'nullif': 'NULLIF',
}


def _to_sql(node, bindings):
    """Recursively convert an AST node to a SQL snippet."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return f"'{node.value}'"
        return str(node.value)
    elif isinstance(node, ast.Name):
        # Placeholders are handled via bindings
        if node.id in bindings:
            return bindings[node.id]
        raise UserError(f"Unbound variable: {node.id}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise UserError(f"Unsupported operator: {op_type.__name__}")
        left = _to_sql(node.left, bindings)
        right = _to_sql(node.right, bindings)

        # Optimization: Merge compatible aggregations in additions (e.g., Sum(X) f1 + Sum(X) f2)
        if isinstance(node.op, ast.Add):
            if isinstance(left, Aggregation) and isinstance(right, Aggregation):
                if left.aggregate == right.aggregate and left.column == right.column:
                    # Only merge SUM and COUNT as a single aggregation with OR condition
                    if left.aggregate in ('SUM', 'COUNT'):
                        return Aggregation(left.aggregate, left.column, left.filters + right.filters)

        # Convert Aggregation objects to SQL strings if not merged
        left_sql = left.to_sql() if isinstance(left, Aggregation) else str(left)
        right_sql = right.to_sql() if isinstance(right, Aggregation) else str(right)

        if isinstance(node.op, ast.Div):
            # Ensure float division in PostgreSQL
            return f"(({left_sql})::float / NULLIF(({right_sql}), 0))"
        return f"({left_sql} {_ALLOWED_OPERATORS[op_type]} {right_sql})"
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise UserError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _to_sql(node.operand, bindings)
        operand_sql = operand.to_sql() if isinstance(operand, Aggregation) else str(operand)
        return f"({_ALLOWED_OPERATORS[op_type]}{operand_sql})"
    elif isinstance(node, ast.Compare):
        left = _to_sql(node.left, bindings)
        ops = []
        for op, right in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _ALLOWED_OPERATORS:
                raise UserError(f"Unsupported comparison: {op_type.__name__}")
            ops.append(f"{_ALLOWED_OPERATORS[op_type]} {_to_sql(right, bindings)}")
        return f"({left} {' '.join(ops)})"
    elif isinstance(node, ast.BoolOp):
        op_sql = ' AND ' if isinstance(node.op, ast.And) else ' OR '
        values = []
        for v in node.values:
            res = _to_sql(v, bindings)
            values.append(res.to_sql() if isinstance(res, Aggregation) else str(res))
        return f"({op_sql.join(values)})"
    elif isinstance(node, ast.IfExp):
        test = _to_sql(node.test, bindings)
        body = _to_sql(node.body, bindings)
        orelse = _to_sql(node.orelse, bindings)
        
        test_sql = test.to_sql() if isinstance(test, Aggregation) else str(test)
        body_sql = body.to_sql() if isinstance(body, Aggregation) else str(body)
        orelse_sql = orelse.to_sql() if isinstance(orelse, Aggregation) else str(orelse)
        
        return f"(CASE WHEN {test_sql} THEN {body_sql} ELSE {orelse_sql} END)"
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            if isinstance(node.func, ast.Constant):
                raise UserError(f"Invalid formula: '{node.func.value}' is not a function. Did you miss an operator (e.g., '*') before the parenthesis?")
            raise UserError(f"Invalid formula: Expression of type '{type(node.func).__name__}' is not callable.")
        if node.func.id not in _ALLOWED_FUNCS:
            raise UserError(f"Unsupported function call: '{node.func.id}'. Allowed functions are: {', '.join(_ALLOWED_FUNCS.keys())}")
        args = [_to_sql(a, bindings) for a in node.args]
        args_sql = [a.to_sql() if isinstance(a, Aggregation) else str(a) for a in args]
        func_id = node.func.id
        template = _ALLOWED_FUNCS[func_id]

        # Special handling for min/max: if multiple args, use LEAST/GREATEST
        if func_id in ('min', 'max') and len(args_sql) > 1:
            template = 'LEAST' if func_id == 'min' else 'GREATEST'

        if '{0}' in template:
            return template.format(*args_sql)
        return f"{template}({', '.join(args_sql)})"
    else:
        raise UserError(f"Unsupported expression node type: {type(node).__name__}")


class CalculationPreset(models.Model):
    """Calculation Preset – stores reusable analytics formulas with placeholders."""
    _name = 'calculation.preset'
    _description = 'Calculation Preset'
    _order = 'name asc'

    name = fields.Char(string='Preset Name', required=True)
    description = fields.Text(string='Description')
    formula = fields.Text(
        string='Formula',
        required=True,
        help='Formula using {placeholder} variables. '
             'Example: ({revenue} - {last_revenue}) / {last_revenue} * 100'
    )
    variables = fields.Text(
        string='Variables (JSON)',
        default='[]',
        help='JSON list of variable definitions: [{"name": "revenue", "label": "Revenue"}]'
    )
    calculation_type = fields.Selection([
        ('row', 'Row-level'),
        ('aggregate', 'Aggregated')
    ], string='Calculation Type', default='aggregate', required=True)
    model_id = fields.Many2one('ir.model', string='Model Reference')
    category = fields.Char(string='Category', default='Common Formulas')
    sheet_id = fields.Many2one('dashboard.sheet', string='Linked Sheet', ondelete='cascade')
    active = fields.Boolean(default=True)

    def unlink(self):
        return super(CalculationPreset, self).unlink()

    def copy(self, default=None):
        default = dict(default or {})
        return super(CalculationPreset, self).copy(default)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @api.model
    def get_all_presets(self, sheet_id=None):
        """Return all active presets as a list of dicts (called from JS (optimized))."""
        domain = [('active', '=', True), ('name', 'not ilike', 'My Preset')]
        return self.search_read(domain, ['id', 'name', 'description', 'formula', 'variables', 'calculation_type', 'sheet_id'])

    @api.model
    def save_preset(self, vals):
        """Create or update a preset. Returns the record id."""
        preset_id = vals.get('id', False)
        data = {
            'name': vals.get('name', ''),
            'description': vals.get('description', ''),
            'formula': vals.get('formula', ''),
            'variables': vals.get('variables', '[]'),
            'calculation_type': vals.get('calculation_type', 'aggregate'),
            'sheet_id': vals.get('sheet_id', False),
        }
        if not data['name']:
            raise UserError('Preset name is required.')
        if not data['formula']:
            raise UserError('Formula is required.')

        if preset_id:
            rec = self.browse(preset_id)
            rec.write(data)
            return preset_id
        else:
            rec = self.create(data)
            return rec.id

    @api.model
    def delete_preset(self, preset_id):
        """Delete (archive) a preset by id."""
        rec = self.browse(preset_id)
        rec.write({'active': False})
        return True

    def write(self, vals):
        """Override write to update linked dashboard.sheet.axis records."""
        res = super(CalculationPreset, self).write(vals)
        if any(k in vals for k in ['formula', 'variables']):
            # Update all linked axis records
            axis_vals = {}
            if 'formula' in vals:
                axis_vals['raw_formula'] = vals['formula']
            if 'variables' in vals:
                axis_vals['variables'] = vals['variables']

            if axis_vals:
                self.env['dashboard.sheet.axis'].sudo().search([
                    ('preset_id', 'in', self.ids)
                ]).write(axis_vals)
        return res

    @api.model
    def translate_to_sql(self, formula, bindings):
        """
        Translate a formula string with variable bindings to a SQL snippet.
        :param formula: str e.g. '({a} - {b}) / {b}'
        :param bindings: dict e.g. {'a': '"res_partner"."revenue"', 'b': '1000'}
        :return: str SQL snippet
        """
        expr = formula
        # Standardize placeholders for AST parsing: replace {name} with name_p
        # This allows us to use ast.parse safely on identifiers.
        # Also replace 'if(' with 'if_func(' to avoid Python keyword conflict.
        expr = re.sub(r'\bif\s*\(', 'if_func(', expr)
        
        clean_bindings = {}
        for name, sql_ref in bindings.items():
            internal_name = f"var_{name}"
            expr = expr.replace('{' + name + '}', internal_name)
            clean_bindings[internal_name] = sql_ref

        try:
            tree = ast.parse(expr, mode='eval')
            res = _to_sql(tree.body, clean_bindings)
            return res.to_sql() if isinstance(res, Aggregation) else str(res)
        except (SyntaxError, UserError) as e:
            raise UserError(f'Formula error: {e}')

    @api.model
    def translate_to_sql_advanced(self, formula, variable_configs, tables=None, calculation_type='aggregate'):
        """
        Translate a formula with per-variable aggregation and filters.

        Uses PostgreSQL FILTER (WHERE ...) clause for per-variable filtering
        so that aggregates correctly participate in the outer GROUP BY.

        :param formula: str e.g. '{current} / {previous} * 100'
        :param variable_configs: list of dicts with name, column, aggregate, filter_domain
        :param tables: str - (deprecated, kept for backward compat)
        :param calculation_type: 'aggregate' or 'row'
        :return: str SQL expression
        """
        bindings = {}
        for var_cfg in variable_configs:
            var_name = var_cfg['name']
            column = var_cfg.get('column', '')
            aggregate = var_cfg.get('aggregate', 'SUM')

            if not column:
                raise UserError(f'No field selected for variable "{var_name}".')

            filter_domain = var_cfg.get('filter_domain', '')
            has_filter = bool(filter_domain and filter_domain.strip())

            if calculation_type == 'row':
                # Row-level: per-row expression, filter becomes CASE WHEN
                if has_filter:
                    bindings[var_name] = f"CASE WHEN {filter_domain} THEN {column} ELSE NULL END"
                else:
                    bindings[var_name] = column
            else:
                if aggregate:
                    if aggregate.upper() in ('SUM', 'COUNT'):
                        # Use Aggregation object for potential merging
                        bindings[var_name] = Aggregation(aggregate, column, [filter_domain] if has_filter else [])
                    else:
                        if has_filter:
                            bindings[var_name] = f"{aggregate}({column}) FILTER (WHERE {filter_domain})"
                        else:
                            bindings[var_name] = f"{aggregate}({column})"
                else:
                    # No aggregate — use column directly (with CASE WHEN for filtering)
                    if has_filter:
                        bindings[var_name] = f"CASE WHEN {filter_domain} THEN {column} ELSE NULL END"
                    else:
                        bindings[var_name] = column

        return self.translate_to_sql(formula, bindings)

    @api.model
    def extract_variables(self, formula):
        """Return list of variable names found in {braces} in the formula."""
        return list(dict.fromkeys(re.findall(r'\{([^}]+)\}', formula)))
