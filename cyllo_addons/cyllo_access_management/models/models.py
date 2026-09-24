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
import psycopg2

from odoo import api, models
from odoo.osv import expression

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_view(self, view_id=None, view_type='form', **options):
        """Apply profile-based access rules and modify the view architecture."""
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        user = self.env.user
        if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
            return res
        allowed_companies = self.env.context.get('allowed_company_ids', [self.env.company.id])
        if not self.env.registry.ready:
            return res
        try:
            with self.env.cr.savepoint(flush=False):
                profiles = user.sudo().profile_ids
                if not profiles:
                    return res
                access_mgmt = self.env['profile.management'].sudo().search([
                    ('profile_ids', 'in', profiles.ids),
                    ('is_activated', '=', True),
                    '|', ('company_ids', 'in', allowed_companies), ('company_ids', '=', False)
                ])
        except Exception:
            return res
        if not access_mgmt:
            return res

        model = res['model']

        is_profile_readonly = any(access_mgmt.mapped('is_readonly'))
        disable_chatter = any(access_mgmt.mapped('disable_chatter'))
        buttons_to_hide = access_mgmt.hide_buttons_tabs_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('button_ids')
        tabs_to_hide = access_mgmt.hide_buttons_tabs_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('tab_ids')
        filters_to_hide = access_mgmt.hide_filters_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('filter_ids')
        groups_to_hide = access_mgmt.hide_filters_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('group_ids')

        field_rules = access_mgmt.field_access_ids.filtered(
            lambda r: r.model_id.model == model
        )
        model_rules = access_mgmt.model_access_ids.filtered(
            lambda r: r.model_id.model == model
        )
        arch = etree.fromstring(res['arch'])
        if is_profile_readonly:
            arch.set("edit", "0")
            arch.set("create", "0")
            arch.set("delete", "0")
        if disable_chatter:
            chatter_nodes = arch.xpath("//chatter") + arch.xpath(
                "//div[contains(@class, 'oe_chatter')]")
            for node_chat in chatter_nodes:
                parent = node_chat.getparent()
                if parent is not None:
                    parent.remove(node_chat)
        if buttons_to_hide:
            for btn in buttons_to_hide:
                for node_btn in arch.xpath(f"//button[@name='{btn.name}']"):
                    node_btn.set("invisible", "1")
        if tabs_to_hide:
            for tab in tabs_to_hide:
                for node_tab in arch.xpath(f"//page[@string='{tab.string}']"):
                    node_tab.set("invisible", "1")
        if filters_to_hide:
            for flt in filters_to_hide:
                for node_flt in arch.xpath(f"//filter[@string='{flt.string}']"):
                    parent = node_flt.getparent()
                    if parent is not None:
                        parent.remove(node_flt)
        if groups_to_hide:
            for group in groups_to_hide:
                for node_grp in arch.xpath(
                        f"//filter[@string='{group.string}']"):
                    node_grp.set("invisible", "1")
        if field_rules:
            for rule in field_rules:
                for node_field in arch.xpath(
                        f"//field[@name='{rule.field_id.name}']"):
                    if rule.field_attribute in ['readonly', 'invisible', 'required']:
                        existing_attr = node_field.get(rule.field_attribute)
                        rule_domain = eval(rule.domain) if rule.domain else []
                        new_expr = self._domain_to_string(rule_domain)
                        final_expr = new_expr
                        if existing_attr:
                            if existing_attr.strip().startswith('['):
                                try:
                                    existing_list = eval(existing_attr)
                                    existing_expr = self._domain_to_string(existing_list)
                                except Exception:
                                    existing_expr = existing_attr
                            else:
                                existing_expr = existing_attr
                            if existing_expr in ["1", "True"]:
                                final_expr = "1"
                            elif existing_expr in ["0", "False"]:
                                final_expr = new_expr
                            elif new_expr in ["True", "1"]:
                                final_expr = "1"
                            elif new_expr in ["False", "0"]:
                                final_expr = existing_expr
                            else:
                                final_expr = f"({existing_expr}) or ({new_expr})"
                        
                        if final_expr == "True": final_expr = "1"
                        if final_expr == "False": final_expr = "0"

                        node_field.set(rule.field_attribute, final_expr)
                    if rule.field_attribute == 'remove_link':
                        node_field.set("options",
                                       '{"no_open": True, "no_create": True}')

        if field_rules:
            domain_fields = set()
            for rule in field_rules:
                if rule.domain:
                    try:
                        dom = eval(rule.domain)
                        for item in dom:
                            if isinstance(item, (list, tuple)) and len(item) == 3:
                                field_name = item[0].split('.')[0]
                                domain_fields.add(field_name)
                    except Exception:
                        pass
            
            existing_fields = set(res.get('fields', {}).keys())
            missing_fields = domain_fields - existing_fields
            if missing_fields:
                if model in self.env:
                    new_fields_defs = self.env[model].fields_get(allfields=list(missing_fields))
                    if 'fields' not in res:
                        res['fields'] = {}
                    res['fields'].update(new_fields_defs)
                    for field_name in missing_fields:
                        node = etree.Element('field', {'name': field_name, 'invisible': '1'})
                        arch.append(node)

        if model_rules:
            if any(model_rules.mapped('is_readonly')):
                arch.set("edit", "0")
                arch.set("create", "0")
                arch.set("delete", "0")
            if any(model_rules.mapped('hide_create')):
                arch.set("create", "0")
            if any(model_rules.mapped('hide_edit')):
                arch.set("edit", "0")
            if any(model_rules.mapped('hide_delete')):
                arch.set("delete", "0")
            if any(model_rules.mapped('hide_archive')):
                arch.set("archive", "0")
            if any(model_rules.mapped('hide_duplicate')):
                arch.set("duplicate", "0")
        res['arch'] = etree.tostring(arch, encoding="unicode")
        return res

    def _domain_to_string(self, domain):
        """
        Converts a domain list to a Python boolean expression string.

        Domains use prefix notation with operators:
        - '&' = AND operator (binary - takes 2 operands)
        - '|' = OR operator (binary - takes 2 operands)
        - '!' = NOT operator (unary - takes 1 operand)
        - Tuples = leaf conditions in format (field, operator, value)

        Examples:
            Input:  [('state', '=', 'draft')]
            Output: "state == 'draft'"

            Input:  ['|', ('active', '=', True), ('archived', '=', False)]
            Output: "(active == True or archived == False)"

            Input:  ['&', ('age', '>', 18), ('country', '=', 'US')]
            Output: "(age > 18 and country == 'US')"

        Args:
            domain (list): Domain in prefix notation

        Returns:
            str: Python boolean expression that can be used in view attributes
        """
        if not domain:
            return "True"

        domain_length = len(domain)
        current_position = 0  # Tracks current position in domain list during parsing

        def parse_next_expression():
            """
            Recursively parses the next expression from the domain.

            This uses nonlocal to maintain parsing position across recursive calls.
            Each call consumes one token and advances current_position.

            Returns:
                str: Parsed expression as a Python boolean string
            """
            nonlocal current_position
            if current_position >= domain_length:
                return "True"
            current_token = domain[current_position]
            current_position += 1  # Consume this token
            if isinstance(current_token, str):
                if current_token == '&':
                    left_operand = parse_next_expression()
                    right_operand = parse_next_expression()
                    return f"({left_operand} and {right_operand})"

                elif current_token == '|':
                    left_operand = parse_next_expression()
                    right_operand = parse_next_expression()
                    return f"({left_operand} or {right_operand})"

                elif current_token == '!':
                    negated_expression = parse_next_expression()
                    return f"(not {negated_expression})"

                return "True"

            elif isinstance(current_token, (list, tuple)):
                if len(current_token) != 3:
                    return "True"
                field_name, comparison_operator, comparison_value = current_token
                if comparison_value is True:
                    value_as_string = "True"
                elif comparison_value is False:
                    value_as_string = "False"
                elif comparison_value is None:
                    value_as_string = "False"
                elif isinstance(comparison_value, str):
                    value_as_string = f"'{comparison_value}'"
                elif isinstance(comparison_value, list):
                    value_as_string = f"{comparison_value}"
                else:
                    value_as_string = str(comparison_value)

                if comparison_operator == '=':
                    return f"{field_name} == {value_as_string}"
                if comparison_operator == '!=':
                    return f"{field_name} != {value_as_string}"
                if comparison_operator == 'in':
                    return f"{field_name} in {value_as_string}"
                if comparison_operator == 'not in':
                    return f"{field_name} not in {value_as_string}"
                if comparison_operator == '>':
                    return f"{field_name} > {value_as_string}"
                if comparison_operator == '>=':
                    return f"{field_name} >= {value_as_string}"
                if comparison_operator == '<':
                    return f"{field_name} < {value_as_string}"
                if comparison_operator == '<=':
                    return f"{field_name} <= {value_as_string}"

                return f"{field_name} {comparison_operator} {value_as_string}"

            return "True"
        parsed_expressions = []
        while current_position < domain_length:
            parsed_expressions.append(parse_next_expression())
        if not parsed_expressions:
            return "True"
        return " and ".join(parsed_expressions)

    @api.model
    def _search(self, domain, *args, **kwargs):
        """Apply profile-based domain restrictions during record searches."""
        if self.env.context.get("skip_profile_domain"):
            return super()._search(domain, *args, **kwargs)
        if not self.env.registry.ready:
            return super()._search(domain, *args, **kwargs)
        user = self.env.user
        if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
            return super()._search(domain, *args, **kwargs)
        try:
            with self.env.cr.savepoint(flush=False):
                profiles = user.sudo().profile_ids
                company_ids = self.env.context.get('allowed_company_ids') or [self.env.company.id]
                if profiles:
                    access_mgmt = self.env['profile.management'].sudo().with_context(
                        skip_profile_domain=True).search([
                        ('profile_ids', 'in', profiles.ids), ('is_activated', '=', True),
                        "|", ('company_ids', 'in', company_ids), ('company_ids', '=', False)
                    ])
                    if access_mgmt:
                        extra_domains = access_mgmt.domain_access_ids.filtered(
                            lambda rec: rec.model_name == self._name
                        ).mapped("domain")
                        for dom in extra_domains:
                            try:
                                dom_list = eval(dom) if dom else []
                                domain = expression.AND([domain, dom_list])
                            except Exception:
                                pass
        except Exception:
            pass
        return super()._search(domain, *args, **kwargs)
