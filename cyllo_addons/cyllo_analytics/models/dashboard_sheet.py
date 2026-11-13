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
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.addons.iap.tools import iap_tools

import tiktoken

_logger = logging.getLogger(__name__)

AGGREGATE_RE = re.compile(r'\b(SUM|AVG|MIN|MAX|COUNT)\s*\(', re.IGNORECASE)


def _has_aggregate(expression):
    """Return True if the SQL expression already contains an aggregate call."""
    return bool(AGGREGATE_RE.search(expression or ''))


GLOBAL_FILTER_OPERATORS = {'=': '=', '>=': '>=', '<=': '<=', 'in': 'IN'}


SQL_IDENTIFIER_RE = re.compile(
    r'^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?$', re.IGNORECASE)

TRAILING_CLAUSE_RE = re.compile(
    r'\b(GROUP\s+BY|ORDER\s+BY|LIMIT|OFFSET)\b', re.IGNORECASE)

GPT_MODEL = "gpt-3.5-turbo"
GPT_TOKN_LMT = 16385
DEFAULT_OLG_ENDPOINT = "https://olg.api.odoo.com"


class DashboardSheet(models.Model):
    """Dashboard Sheet Model"""
    _name = "dashboard.sheet"
    _description = "Dashboard Sheet"
    _inherit = ["image.mixin"]

    name = fields.Char(required=True)
    table_ids = fields.One2many(
        "dashboard.sheet.table",
        string="Tables",
        inverse_name="sheet_id"
    )
    filter_ids = fields.One2many(
        "dashboard.sheet.filter",
        "sheet_id",
        string="Filters"
    )
    axis_ids = fields.One2many(
        "dashboard.sheet.axis",
        "sheet_id",
        string="Filters"
    )
    query = fields.Text(
        string="Query Editor",
        compute="_compute_query",
        store=True
    )
    query_gen = fields.Text(string="Query Generated")
    dimension = fields.Char(compute="_compute_dimension")
    measure = fields.Text(compute="_compute_dimension")
    type = fields.Char()
    dimension_axis = fields.Selection(
        [
            ("x", "X"),
            ("y", "Y")
        ]
    )
    is_enabled = fields.Boolean(
        string="Enabled",
        default=True
    )
    limit = fields.Integer(default=0)
    dashboard_sheet_option_ids = fields.One2many(
        "dashboard.sheet.option",
        "dashboard_sheet_id"
    )
    kpi_name = fields.Char(string="Name")
    kpi_target = fields.Float()
    kpi_view = fields.Selection(
        [
            ("View 1", "View 1"),
            ("View 2", "View 2"),
            ("no_view", "No View")
        ],
        string="KPI Target View",
    )
    kpi_description = fields.Text()
    kpi_redirect = fields.Boolean("KPI Redirect")
    kpi_target_perc = fields.Float("KPI Target Percentage")
    kpi_icon = fields.Char("KPI Icon")
    kpi_model = fields.Char("KPI Model")
    sheet_type_id = fields.Many2one(
        "dashboard.sheet.type",
        "Sheet Type"
    )
    sheet_filter_ids = fields.One2many(
        "dashboard.sheet.global",
        "sheet_id"
    )
    currency_id = fields.Many2one(
        'res.currency',
        'Currency'
    )
    annotation_ids = fields.One2many(
        'dashboard.sheet.annotation',
        'sheet_id',
        string='Annotations'
    )
    color_mapping_ids = fields.One2many(
        'dashboard.sheet.color.mapping',
        'sheet_id',
        string='Color Mappings'
    )

    @api.model
    def get_config_data(self):
        """Method to get configuration data."""
        get_param = self.env["ir.config_parameter"].sudo().get_param
        is_enable = get_param("cyllo_analytics.limit_record")
        limit = get_param("cyllo_analytics.limit")
        company = self.env.company
        default_theme = self.env.ref("cyllo_analytics.dashboard_theme_cyllo", raise_if_not_found=False)
        theme_colors = []
        if default_theme:
            theme_colors = default_theme.theme_color_ids.mapped("name")
        return {
            "is_enable": is_enable,
            "limit": limit if is_enable else 0,
            "sheet_types": self.env["dashboard.sheet.type"].search_read([]),
            "currency": {
                "id": company.currency_id.id,
                "display_name": company.currency_id.display_name,
            },
            "theme_color_ids": theme_colors,
        }

    @api.depends("axis_ids.alias")
    def _compute_dimension(self):
        """Method to compute dimension and measure fields based on axis aliases."""
        for rec in self:
            dimension = rec.axis_ids.filtered(
                lambda x: x.type == "dimension").mapped(
                "alias"
            )
            rec.dimension = dimension[0] if dimension else False
            measure = rec.axis_ids.filtered(
                lambda x: x.type == "measure").mapped(
                "alias"
            )
            rec.measure = str(measure)

    @api.depends(
        "axis_ids.alias", "axis_ids.column", "axis_ids.type",
        "axis_ids.aggregate_func", "axis_ids.sort_desc",
        "table_ids.join", "table_ids.linked", "limit",
        "filter_ids.is_active", "filter_ids.domain", "query_gen"
    )
    def _compute_query(self):
        """Generate the query from the given data"""
        for rec in self:
            if rec.query_gen:
                rec.query = rec.query_gen
                continue
            company_currency_id = str(self.env.company.currency_id.id)

            columns = rec.axis_ids.filtered(
                lambda x: x.type in ["measure", "dimension"]
            )
            joins = rec.table_ids.sorted(lambda x: bool(x.linked)).mapped(
                "join")
            where = rec.filter_ids.filtered(lambda x: x.is_active)
            measure_with_agg = columns.filtered(
                lambda x: x.type == 'measure' and _has_aggregate(x.query)
            )
            group_by = rec.axis_ids.filtered(lambda x: x.type == "group")
            if group_by or measure_with_agg:
                for col in columns:
                    if col.type == 'measure' and not _has_aggregate(col.query):
                        raw_expr = col.query.split(' AS ')[0].strip() if ' AS ' in (col.query or '') else col.column
                        agg = (col.aggregate_func or 'SUM').upper()
                        col.query = f"{agg}({raw_expr}) AS {col.alias}"
            col_queries = [
                (q or '').replace('{selectedCurrency}', company_currency_id)
                for q in columns.mapped('query')
            ]
            query = f"""SELECT {', '.join(col_queries)} FROM {' '.join(joins)}"""
            if where:
                # Resolve placeholder in WHERE domain clauses (safety net)
                where_clauses = [
                    (d or '').replace('{selectedCurrency}', company_currency_id)
                    for d in where.mapped('domain')
                ]
                query += f" WHERE {' AND '.join(where_clauses)}"
            not_columns_group = columns.filtered(lambda x: not _has_aggregate(x.query))
            if group_by:
                valid_group_by = group_by.filtered(lambda x: not any(agg in (x.column or '').upper() for agg in ['SUM(', 'AVG(', 'COUNT(', 'MIN(', 'MAX(']))
                
                group_by_clauses = []
                if valid_group_by:
                    group_by_clauses.extend(valid_group_by.mapped('column'))
                if not_columns_group:
                    group_by_clauses.extend(not_columns_group.mapped('alias'))
                
                if group_by_clauses:
                    query += f" GROUP BY {', '.join(group_by_clauses)}"
            elif measure_with_agg:
                group_targets = not_columns_group.mapped('alias')
                if group_targets:
                    query += f" GROUP BY {', '.join(group_targets)}"
            order_by = rec.axis_ids.filtered(lambda x: x.type == "order")
            if order_by:
                order_clauses = []
                for o in order_by:
                    matched_col = columns.filtered(lambda x: x.alias == o.alias or x.column == o.column)
                    order_expr = matched_col[0].alias if matched_col else o.column
                    order_clauses.append(f"{(order_expr or '').replace('{selectedCurrency}', company_currency_id)} {'DESC' if o.sort_desc else 'ASC'}")
                query += f" ORDER BY {', '.join(order_clauses)}"
            else:
                initial = False
                if group_by:
                    initial = group_by.mapped("column")[0]
                elif measure_with_agg and not_columns_group:
                    initial = not_columns_group.mapped("alias")[0]
                else:
                    main_table = rec.table_ids.filtered(lambda x: not x.linked)
                    if main_table:
                        main_table = main_table[-1]
                        initial = f"{main_table.join}.id" if main_table else False
                if initial:
                    query += f" ORDER BY {initial}"

            limit = rec.limit
            if limit:
                query += f" LIMIT {limit}"
            rec.query = query

    @api.model
    def update_limit(self, limit, ttype):
        """Method to check if a limit can be updated for a given chart type."""
        return (limit > 30 or not limit) and ttype in [
            "pie",
            "doughnut",
            "radar",
            "funnel",
        ]

    @api.model
    def create(self, vals_list):
        """Method to create records."""
        limit = vals_list.get("limit", 0)
        ttype = (
            self.env["dashboard.sheet.type"]
            .browse(vals_list.get("sheet_type_id"))
            .ttype
        )
        if self.update_limit(limit, ttype):
            vals_list["limit"] = 30
        return super().create(vals_list)

    def write(self, vals):
        """Method to write data to the record."""
        if "limit" in vals or "sheet_type_id" in vals:
            limit = vals.get("limit", self.limit)
            ttype_id = vals.get("sheet_type_id", self.sheet_type_id.id)
            ttype = self.env["dashboard.sheet.type"].browse(ttype_id).ttype
            if self.update_limit(limit, ttype):
                vals["limit"] = 30
        return super().write(vals)

    @api.model
    def get_data(self, model_id):
        """Get the data for the given model"""
        model = self.env["ir.model"].browse(model_id)
        model_obj = self.env[model.model]
        fields_get = model_obj.fields_get()
        all_fields = dict(
            filter(lambda x: x[1].get("store", False), fields_get.items())
        )
        return {
            "name": model.display_name,
            "model": model.model,
            "id": model_id,
            "table": model_obj._table,
            "fields": all_fields,
        }

    @api.model
    def update_data(self, data):
        """Method to update data based on received input (optimized)."""
        vals = {}
        show_position_warning = False
        if data.get("image"):
            vals["image_1920"] = data["image"].split(",")[1]
        if data.get("name"):
            vals["name"] = data["name"]
        if data.get("currency"):
            vals["currency_id"] = data["currency"]
        if "limit" in data:
            vals["limit"] = data["limit"]
        if data.get("query"):
            vals["query_gen"] = data["query"]
        if data.get("type"):
            vals["type"] = data["type"][1]
            vals["sheet_type_id"] = data["type"][0]
        if data.get("dimension_axis"):
            vals["dimension_axis"] = data["dimension_axis"]
        if data.get("annotations"):
            pass
        if data.get("kpi"):
            kpi = data["kpi"]
            vals.update({
                "kpi_target": kpi.get("target"),
                "kpi_view": kpi.get("measureView"),
                "kpi_description": kpi.get("description"),
                "kpi_redirect": kpi.get("redirect"),
                "kpi_name": kpi.get("name"),
                "kpi_target_perc": kpi.get("kpiTarget") if isinstance(kpi.get("kpiTarget"), (int, float)) else 0,
                "kpi_icon": kpi.get("icon"),
            })

        if data.get("id"):
            rec = self.browse(data["id"])
            old_type = rec.type
            new_type = vals.get("type", old_type)
            is_graph_before_now_kpi = old_type != "kpi" and new_type == "kpi"
            is_kpi_before_now_graph = old_type == "kpi" and new_type != "kpi"
            is_chart_before_now_table = old_type not in ("kpi", "table") and new_type == "table"
            is_table_before_now_chart = old_type == "table" and new_type not in ("kpi", "table")
            rec.write(vals)

            configs = [c["id"] for c in data.get("configs", [])]
            sheet_option_ids = rec.dashboard_sheet_option_ids.filtered(
                lambda x: x.dashboard_config_id.id in configs
            ).ids
            is_new_sheet = not bool(len(data.get("configs", [])) > len(sheet_option_ids))

            if is_graph_before_now_kpi:
                for record in rec.dashboard_sheet_option_ids:
                    record.write({"attributes": {**record.attributes, "graph_width": 3, "graph_height": 2}})
            if is_kpi_before_now_graph:
                show_position_warning = True
                rec.dashboard_sheet_option_ids.unlink()
            if is_chart_before_now_table:
                show_position_warning = True
                rec.dashboard_sheet_option_ids.unlink()
            if is_table_before_now_chart:
                show_position_warning = True
                rec.dashboard_sheet_option_ids.unlink()
        else:
            rec = self.create(vals)
            is_new_sheet = True

        for config_id in data.get("configs", []):
            config = self.env["dashboard.config"].browse(config_id["id"])
            if rec.id not in config.sheet_ids.ids:
                config.write({"sheet_ids": [fields.Command.link(rec.id)]})

        batch_vals = {}

        filter_commands = []
        sheet_filter = []
        for where in data.get("where", []):
            w_vals = {
                "name": where["name"],
                "domain": where["domain"],
                "is_active": where["active"],
                "domain_py_expression": where["domain_py_expression"],
            }
            if not str(where.get("id")).isdigit():
                w_vals["sheet_id"] = rec.id
                filter_id = self.env["dashboard.sheet.filter"].create(w_vals)
                w_vals["id"] = filter_id.id
                sheet_filter.append(w_vals)
            else:
                filter_commands.append(fields.Command.update(int(where["id"]), w_vals))
        if filter_commands: batch_vals["filter_ids"] = filter_commands

        # table_ids
        table_commands = []
        for join in data.get("joinData", []):
            j_vals = {
                "name": join["name"],
                "model": join["model"],
                "join": join["join"],
                "linked": join.get("string", False),
                "field": join.get("field", False),
                "model_id": join.get("model_id", False),
            }
            if not join.get("id"):
                table_commands.append(fields.Command.create(j_vals))
            else:
                table_commands.append(fields.Command.update(join["id"], j_vals))
        if table_commands: batch_vals["table_ids"] = table_commands

        axis_commands = []
        incoming_axis_ids = set()
        dim = data.get("dimension")
        if dim and dim.get("id"):
            incoming_axis_ids.add(dim["id"])
        for msr in data.get("measure", []):
            if msr.get("id"):
                incoming_axis_ids.add(msr["id"])
        existing_dim_measure = rec.axis_ids.filtered(lambda x: x.type in ('dimension', 'measure'))
        orphaned = existing_dim_measure.filtered(lambda x: x.id not in incoming_axis_ids)
        if orphaned:
            orphaned.unlink()

        if dim:
            d_vals = {k: dim[k] for k in ["value", "alias", "query", "column"] if k in dim}
            d_vals.update({
                "type": "dimension", "is_preset": dim.get("isPreset", False),
                "raw_formula": dim.get("rawFormula", False), "variables": dim.get("variables", False),
                "preset_id": dim.get("preset_id", False),
                "calculation_type": dim.get("calculation_type", False),
                "aggregate_func": dim.get("aggregate_func", False),
                "variable_configs": dim.get("variable_configs", False),
            })
            if not dim.get("id"): axis_commands.append(fields.Command.create(d_vals))
            else: axis_commands.append(fields.Command.update(dim["id"], d_vals))

        for msr in data.get("measure", []):
            m_vals = {k: msr[k] for k in ["value", "alias", "query", "column", "monetaryInBase"] if k in msr}
            m_vals.update({
                "type": "measure", "is_preset": msr.get("isPreset", False),
                "raw_formula": msr.get("rawFormula", False), "variables": msr.get("variables", False),
                "preset_id": msr.get("preset_id", False),
                "calculation_type": msr.get("calculation_type", False),
                "aggregate_func": msr.get("aggregate_func", False),
                "variable_configs": msr.get("variable_configs", False),
            })
            if not msr.get("id"): axis_commands.append(fields.Command.create(m_vals))
            else: axis_commands.append(fields.Command.update(msr["id"], m_vals))

        rec.axis_ids.filtered(lambda x: x.type == 'group').unlink()
        for grp in data.get("group_by", []):
            g_vals = {k: grp[k] for k in ["value", "alias", "query", "column"] if k in grp}
            g_vals.update({
                "source_column": grp.get("source_column", False), "date_group": grp.get("date_group", False),
                "type": "group",
            })
            axis_commands.append(fields.Command.create(g_vals))

        for ord in data.get("order_by", []):
            o_vals = {k: ord[k] for k in ["value", "alias", "query", "column", "sort_desc"] if k in ord}
            o_vals["type"] = "order"
            if not ord.get("id"): axis_commands.append(fields.Command.create(o_vals))
            else: axis_commands.append(fields.Command.update(ord["id"], o_vals))
        if axis_commands: batch_vals["axis_ids"] = axis_commands

        # Global Options (sheet_filter_ids)
        if data.get("options"):
            global_commands = []
            for option in (data["options"].values() if isinstance(data["options"], dict) else data["options"]):
                if not option: continue
                o_vals = {
                    "sheet_id": rec.id, "global_filter_id": option["global_filter_id"],
                    "field": option["field"], "name": option["name"],
                }
                existing = self.env["dashboard.sheet.global"].search([
                    ("sheet_id", "=", rec.id), ("global_filter_id", "=", option["global_filter_id"]),
                ], limit=1)
                if existing: global_commands.append(fields.Command.update(existing.id, o_vals))
                else: global_commands.append(fields.Command.create(o_vals))
            if global_commands: batch_vals["sheet_filter_ids"] = global_commands

        if batch_vals:
            rec.write(batch_vals)

        # Update Color Mappings
        if "color_mappings" in data:
            rec.color_mapping_ids.unlink()
            for mapping in data["color_mappings"]:
                val_max = mapping.get("max_value", "")
                self.env["dashboard.sheet.color.mapping"].create({
                    "sheet_id": rec.id,
                    "measure_alias": mapping.get("measure_alias"),
                    "min_value": float(mapping.get("min_value", 0)),
                    "max_value": str(val_max) if val_max is not None else "",
                    "color": mapping.get("color", "#344BD2"),
                    "indicator": mapping.get("indicator", ""),
                    "notes": mapping.get("notes", ""),
                })
        
        # Update Annotations (Dedicated section)
        if "annotations" in data:
            rec.annotation_ids.unlink()
            for note in data["annotations"]:
                self.env["dashboard.sheet.annotation"].create({
                    "sheet_id": rec.id,
                    "measure_alias": note.get("measure_alias"),
                    "dimension_label": note.get("dimension_label"),
                    "notes": note.get("notes", ""),
                })

        rec.unlink_data(data.get("unlink_list", {"axis":[], "tables":[], "where":[], "configs":[]}))
        return {
            "rec_id": rec.id,
            "sheet_filter": sheet_filter,
            "is_new_sheet": is_new_sheet,
            "show_position_warning": show_position_warning,
        }

    def set_sheet_position(self, config_id, **kwargs):
        """Method to set the position of the sheet within a dashboard configuration."""
        self.write(
            {
                "dashboard_sheet_option_ids": [
                    fields.Command.create(
                        {"dashboard_config_id": config_id, "attributes": kwargs}
                    )
                ]
            }
        )

    def unlink_data(self, unlink_list):
        """Method to unlink data based on the provided unlink list."""
        if unlink_list["axis"]:
            self.env["dashboard.sheet.axis"].browse(
                unlink_list["axis"]).unlink()
        if unlink_list["tables"]:
            self.env["dashboard.sheet.table"].browse(
                unlink_list["tables"]).unlink()
        if unlink_list["where"] and isinstance(unlink_list["where"], int):
            self.env["dashboard.sheet.filter"].browse(
                unlink_list["where"]).unlink()
        for config in unlink_list["configs"]:
            attributes = self.env["dashboard.sheet.option"].search(
                [
                    ("dashboard_sheet_id", "=", self.id),
                    ("dashboard_config_id", "=", config),
                ]
            )
            attributes.unlink()
            self.env["dashboard.config"].browse(config).write(
                {"sheet_ids": [fields.Command.unlink(self.id)]}
            )

    @staticmethod
    def count_gpt_tokens(text):
        """Returns the length of the tokens"""
        tokenizer = tiktoken.encoding_for_model(GPT_MODEL)
        tokens = tokenizer.encode(text)
        return len(tokens)

    @staticmethod
    def get_base_prompt(prompt_data, regenerate=False):
        prompt = (
            "Generate an explanation using AI for the given graph data. "
            f"Graph data {prompt_data}. The AI should provide a "
            "comprehensive and insightful short explanation of the "
            "data presented in the graph, including key trends, "
            "anomalies, and any significant insights. The explanation "
            "should be suitable for inclusion in a BI dashboard's "
            "'Explain with AI' feature, and it should be clear and "
            "understandable to a non-technical audience. Please provide "
            "a detailed explanation of the data in the graph, "
            "highlighting any critical data points, changes over time, "
            "and any correlations or patterns that might be of "
            "significance to the viewer. Feel free to use natural "
            "language and provide context that enhances the user's "
            "understanding of the data. Also, highlight only the "
            "important parts (words) with two asterisks at the "
            "beginning and at the end, Make sure it is in "
            "MarkDown language."
        )
        # Todo: Add user lang to the gpt
        if regenerate:
            prompt += (
                "Regenerate the response different from previous "
                "one and it should be shorter and very understandable."
            )

        return prompt

    def base_prompt_generator(self, prompt_data, regenerate=False):
        prompt_len = len(prompt_data)
        percentage_cuts = [
            0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9,
            0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97,
            0.98, 0.99, 0.991, 0.992, 0.993, 0.994, 0.995,
            0.996, 0.997, 0.998, 0.999
        ]  # Cut percentages
        prompt = self.get_base_prompt(prompt_data, regenerate)
        token_count = self.count_gpt_tokens(prompt)
        if token_count > GPT_TOKN_LMT:
            for cut in percentage_cuts:
                start_index = int(prompt_len * cut)
                prompt_segment = prompt_data[start_index:]
                prompt = self.get_base_prompt(prompt_segment, regenerate)
                token_count = self.count_gpt_tokens(prompt)
                if token_count <= GPT_TOKN_LMT:
                    return prompt, 1 - cut
            return prompt, 1 - percentage_cuts[-1], token_count
        return prompt, 1, token_count

    @api.model
    def explain_with_ai(self, prompt_data, regenerate=False):
        """Generate an explanation using AI for the given graph data."""
        prompt, cut, token_count = self.base_prompt_generator(prompt_data,
                                                              regenerate)
        is_error = not bool(prompt_data)
        return {
            **self._make_ai_response(prompt, is_error, [], cut),
            "request_token": token_count
        }

    @api.model
    def chat_with_ai(self, prompt, conversation_history):
        request_token = self.count_gpt_tokens(prompt)
        return {**self._make_ai_response(prompt, False,
                                         conversation_history, 1),
                "request_token": request_token}

    def _ai_error(self, message):
        """Response of a failed AI request, shown in place of the answer."""
        return {
            "is_error": True,
            "api_error": False,
            "explanation": message,
            "cut": 1,
            "response_token": self.count_gpt_tokens(message),
        }

    def _cyllo_ai_client(self):
        """LLM client of the Cyllo AI configuration marked "Use For AI", or None
        when Cyllo AI is not installed or has no complete configuration."""
        if 'cyllo.ai.config' not in self.env:
            return None
        from odoo.addons.cyllo_ai.core.llm_client import LLMClient
        client = LLMClient(self.env)
        return client if client.is_configured() else None

    def _make_ai_response(self, prompt, is_error, conversation_history, cut):
        """Answer through Cyllo AI when it is configured, else through the Odoo AI service."""
        client = self._cyllo_ai_client()
        if client:
            return self.make_response_with_cyllo_ai(client, prompt, is_error,
                                                    conversation_history, cut)
        return self.make_response_with_default(prompt, is_error,
                                               conversation_history, cut)

    def make_response_with_cyllo_ai(self, client, prompt, is_error,
                                    conversation_history, cut):
        """Answer with the Cyllo AI configuration marked "Use For AI"."""
        messages = list(conversation_history or []) + [
            {"role": "user", "content": prompt}]
        try:
            explanation = client.complete(messages)
        except Exception as error:
            _logger.warning("AI Insights request failed: %s", error)
            return self._ai_error(_(
                "Sorry, we could not generate a response. Please try again later.\n\n%s",
                error))
        return {
            "is_error": is_error,
            "api_error": False,
            "explanation": explanation,
            "cut": cut,
            "response_token": self.count_gpt_tokens(explanation),
        }

    def make_response_with_default(self, prompt, is_error,
                                   conversation_history, cut):
        """Answer with the Odoo AI service (IAP)."""
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        database_id = IrConfigParameter.get_param("database.uuid")
        try:
            response = iap_tools.iap_jsonrpc(
                DEFAULT_OLG_ENDPOINT + "/api/olg/1/chat",
                params={
                    "prompt": prompt,
                    "conversation_history": conversation_history or [],
                    "database_id": database_id,
                },
                timeout=30,
            )
        except AccessError:
            return self._ai_error(_("Oops, it looks like our AI is unreachable!"))
        except Exception:
            return self._ai_error(_(
                "Sorry, we could not generate a response. Please try again later."))
        if response["status"] == "success":
            return {
                "is_error": is_error,
                "api_error": False,
                "explanation": response["content"],
                "cut": cut,
                "response_token": self.count_gpt_tokens(response["content"])
            }
        if response["status"] == "error_prompt_too_long":
            return self._ai_error(_(
                "It looks like there's a lot of information to process, The AI "
                "model won't be able to process the request at this time!!"))
        if response["status"] == "limit_call_reached":
            return self._ai_error(_(
                "You've reached the maximum number of requests for now. "
                "Please take a short break and try again later!"))
        return self._ai_error(_(
            "Sorry, we could not generate a response. Please try again later."))

    @staticmethod
    def _tables_in_query(query):
        """The tables a query actually reads, upper-cased.

        A dashboard's global filter is mapped to one field, and a sheet on
        that dashboard may not read the table that field lives on. The
        dashboard skips such a filter rather than producing SQL that cannot
        run; this is the same test, server side.
        """
        upper = (query or '').upper()
        start = upper.find('FROM')
        if start == -1:
            return set()
        return {
            match.group(1)
            for match in re.finditer(
                r'(?:FROM|JOIN)\s+"?([A-Z_][A-Z0-9_]*)"?', upper[start:])
        }

    def _global_filter_where(self, config_id, values):
        """The WHERE fragment a dashboard's global filters add to this sheet.

        Returns "" when nothing applies, which leaves the sheet's own query
        untouched.
        """
        self.ensure_one()
        if not config_id or not values:
            return ''
        links = self.env['dashboard.sheet.global'].search([
            ('sheet_id', '=', self.id),
            ('global_filter_id.dashboard_config_id', '=', int(config_id)),
        ])
        tables = self._tables_in_query(self.query)
        clauses = []
        for link in links:
            global_filter = link.global_filter_id
            value = (values or {}).get(global_filter.code)
            if value is None or value == '' or value == []:
                continue
            field = (link.field or '').strip()
            if not SQL_IDENTIFIER_RE.match(field):
                _logger.warning(
                    "Skipping global filter %s on sheet %s: %r is not a plain "
                    "column reference", global_filter.code, self.id, field)
                continue
            if '.' in field and field.split('.')[0].upper() not in tables:
                continue
            operator = GLOBAL_FILTER_OPERATORS.get(global_filter.operator)
            if not operator:
                continue
            if operator == 'IN':
                value = tuple(value) if isinstance(value, (list, tuple)) else (value,)
                if not value:
                    continue
            literal = self.env.cr.mogrify('%s', (value,)).decode()
            clauses.append(f"{field} {operator} {literal}")
        return ' AND '.join(clauses)

    @staticmethod
    def _inject_where(query, condition):
        """Add ``condition`` to ``query``, extending any WHERE already there.

        Mirrors applyFilters() in cy_dashboard_mixin.js so a chart filtered
        through a presentation matches the same chart on the dashboard.
        """
        if not condition:
            return query
        start = (query or '').upper().rfind('FROM')
        if start == -1:
            return query
        head, tail = query[:start], query[start:]
        existing = re.search(
            r'\bWHERE\b\s+(.+?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)',
            tail, re.IGNORECASE | re.DOTALL)
        if existing:
            # Trailing space matters: the match ends flush against GROUP BY.
            merged = f"WHERE ({existing.group(1).strip()}) AND ({condition}) "
            tail = tail[:existing.start()] + merged + tail[existing.end():]
            return head + tail
        trailing = TRAILING_CLAUSE_RE.search(tail)
        cut = trailing.start() if trailing else len(tail)
        return f"{head}{tail[:cut]} WHERE {condition} {tail[cut:]}".rstrip()

    @api.model
    def fetch_sheet_data(self, sheet_ids, filters=None):
        """Run each sheet's stored query and return ``{sheet_id: rows}``.

        Added for the presentation editor, which draws several charts on one
        slide and would otherwise make a round trip per chart. The SQL is
        read from the sheet record here rather than accepted from the
        caller, so a client can only ask for a sheet *by id* - it cannot
        choose what SQL runs.

        Access is limited to sheets reachable through a dashboard.config the
        user may read, which is what the record rules on that model already
        express.

        ``filters`` carries the presentation's "as shown on dashboard"
        boxes::

            {"<sheet_id>": {"config_id": 7, "values": {"date_0": "2025-01-01"}}}

        Sheets absent from it are run unfiltered, which is the default and
        what every existing caller gets by passing nothing. Only the *values*
        come from the client; the field and operator each value is applied
        through are read from the dashboard's own global filter records, so
        a caller cannot choose what SQL is built.
        """
        if isinstance(sheet_ids, int):
            sheet_ids = [sheet_ids]
        try:
            requested = {int(sheet_id) for sheet_id in (sheet_ids or [])}
        except (TypeError, ValueError):
            return {}
        if not requested:
            return {}

        configs = self.env['dashboard.config'].search(
            [('sheet_ids', 'in', list(requested))])
        allowed = set(configs.sheet_ids.ids) & requested
        unreachable = requested - allowed
        if unreachable:
            # A deck may draw from sheets that sit on no dashboard at all -
            # one hidden from its dashboard, or built straight from Sheets.
            # Those have no dashboard whose rules could grant them, so they
            # fall back to this model's own access. A sheet that IS on a
            # dashboard the user may not read stays refused.
            on_a_dashboard = set(self.env['dashboard.config'].sudo().search(
                [('sheet_ids', 'in', list(unreachable))]).sheet_ids.ids)
            orphans = unreachable - on_a_dashboard
            if orphans:
                allowed |= set(self.search([('id', 'in', list(orphans))]).ids)
        if allowed != requested:
            _logger.warning(
                "fetch_sheet_data: dropping sheet ids not reachable by user "
                "%s: %s", self.env.user.login, sorted(requested - allowed))

        executor = self.env['dashboard.config']
        result = {}
        for sheet in self.browse(sorted(allowed)):
            query = (sheet.query or '').strip()
            if not query:
                result[str(sheet.id)] = []
                continue
            # A query saved by the sheet editor is deliberately the *base*
            # query: "Base query MUST NOT include dynamic sheet filters so the
            # dashboard can toggle them properly". The dashboard puts them back
            # as it renders and the editor previews with them, so a consumer
            # that runs the bare query shows an unfiltered total nobody else
            # shows. Only query_gen is built that way; a query this model
            # computed already carries them.
            if sheet.query_gen:
                active = sheet.filter_ids.filtered(lambda f: f.is_active)
                domains = [d for d in active.mapped('domain') if d]
                if domains:
                    query = sheet._inject_where(
                        query, ' AND '.join('(%s)' % d for d in domains))
            wanted = (filters or {}).get(str(sheet.id)) or (
                filters or {}).get(sheet.id)
            if wanted:
                try:
                    condition = sheet._global_filter_where(
                        wanted.get('config_id'), wanted.get('values'))
                    query = sheet._inject_where(query, condition)
                except Exception:
                    _logger.exception(
                        "Global filters for sheet %s could not be applied",
                        sheet.id)
            try:
                rows = executor.sql_execute(query)
            except Exception:
                _logger.exception("Query for dashboard sheet %s failed", sheet.id)
                result[str(sheet.id)] = []
                continue
            result[str(sheet.id)] = rows if isinstance(rows, list) else []
        return result

    def get_sheet_data(self):
        """Method to retrieve data related to the sheet."""
        has_error = {"error": False, "value": []}
        configs = self.env["dashboard.config"].search(
            [("sheet_ids", "in", self.ids)])
        where = self.filter_ids.read(["name", "domain", "domain_py_expression", "is_active"])
        for data in where:
            data["active"] = data.pop("is_active")

        join_data = []
        all_models = []
        join = []
        
        # Batch read for table_ids
        tables = self.table_ids.read(["field", "join", "model", "model_id", "name", "linked"])
        for table_val in tables:
            if table_val["model_id"]:
                model_id = table_val["model_id"][0]
                join.append(table_val["join"])
                val = {
                    "field": table_val["field"],
                    "join": table_val["join"],
                    "model": table_val["model"],
                    "model_id": model_id,
                    "name": table_val["name"],
                    "string": table_val["linked"],
                    "id": table_val["id"],
                }
                join_data.append(val)
                all_models.append(
                    {"linked_by": val, **self.get_data(model_id)})
            else:
                has_error["error"] = True
                has_error["value"].append(table_val["model"])
        dimension = self.axis_ids.filtered(
            lambda x: x.type == "dimension").read(
            ["alias", "query", "column", "value", "type", "is_preset", "raw_formula", "variables", "preset_id", "calculation_type", "aggregate_func", "variable_configs"]
        )
        measure = self.axis_ids.filtered(lambda x: x.type == "measure").read(
            ["alias", "query", "monetaryInBase", "column", "value", "type", "is_preset", "raw_formula", "variables", "preset_id", "calculation_type", "aggregate_func", "variable_configs"]
        )
        group = self.axis_ids.filtered(lambda x: x.type == "group").read(
            ["alias", "query", "column", "value", "type", "source_column", "date_group"]
        )
        order = self.axis_ids.filtered(lambda x: x.type == "order").read(
            ["alias", "query", "column", "value", "type", "sort_desc"]
        )
        options = {}
        for option in self.env["dashboard.sheet.global"].search_read(
                [("sheet_id", "=", self.id)]
        ):
            options[option["global_filter_id"][0]] = {
                "id": option["id"],
                "global_filter_id": option["global_filter_id"][0],
                "field": option["field"],
                "name": option["name"],
            }
        primary_model = self.table_ids.filtered(lambda x: not x.linked)[:1].model if self.table_ids else False
        dim_axis = self.axis_ids.filtered(lambda x: x.type == "dimension")[:1]
        dimension_field = dim_axis.column if dim_axis else False
        
        return {
            "has_error": has_error,
            "dimension": dimension,
            "dimension_axis": self.dimension_axis,
            "measure": measure,
            "groupBy": group,
            "orderBy": order,
            "name": self.name,
            "currency": self.currency_id.read(['id', 'display_name']),
            "limit": self.limit,
            "type": [self.sheet_type_id.id, self.type],
            "configs": configs.read(["display_name"]) if configs else [],
            "where": where,
            "join": join,
            "joinData": join_data,
            "models": all_models,
            "options": options,
            "model": primary_model,
            "dimension_field": dimension_field,
            "kpi": {
                "target": self.kpi_target,
                "measureView": self.kpi_view,
                "description": self.kpi_description,
                "redirect": self.kpi_redirect,
                "name": self.kpi_name,
                "kpiTarget": self.kpi_target_perc,
                "icon": self.kpi_icon,
                "model": self.kpi_model,
            },
            "color_mappings": self.color_mapping_ids.filtered(lambda m: not m.notes or m.indicator).read(["measure_alias", "min_value", "max_value", "color", "indicator", "notes"]),
            "annotations": self.annotation_ids.read(["measure_alias", "dimension_label", "notes"]),
        }

    def get_dashboard_sheet(self):
        """Method to get dashboard sheet data."""
        res = self.read()[0]
        res["name"] = res["name"] + " (COPY)"
        res["currency_id"] = self.currency_id.id
        res["axis_ids"] = self.axis_ids.read()
        res["filter_ids"] = self.filter_ids.read()
        res["sheet_filter_ids"] = self.sheet_filter_ids.read()
        res["sheet_type_id"] = self.sheet_type_id.id
        res["table_ids"] = self.table_ids.read()
        return [res]

    def duplicate_sheet(self):
        """Method to duplicate a dashboard sheet."""
        res = self.get_dashboard_sheet()
        val = self.create_duplicate(res)
        return val.id

    def create_duplicate(self, record):
        """Method to create a duplicate of a dashboard sheet."""
        create_val = [
            {
                "name": sheet["name"],
                "currency_id": sheet["currency_id"],
                "type": sheet["type"],
                "limit": sheet["limit"],
                "query_gen": sheet["query_gen"],
                "dimension_axis": sheet["dimension_axis"],
                "is_enabled": sheet["is_enabled"],
                "axis_ids": [
                    fields.Command.create(
                        {
                            "value": rec["value"],
                            "alias": rec["alias"],
                            "query": rec["query"],
                            "monetaryInBase": rec["monetaryInBase"],
                            "column": rec["column"],
                            "type": rec["type"],
                            "is_preset": rec.get("is_preset", False),
                            "raw_formula": rec.get("raw_formula", False),
                            "variables": rec.get("variables", False),
                            "variable_configs": rec.get("variable_configs", False),
                            "calculation_type": rec.get("calculation_type", False),
                            "aggregate_func": rec.get("aggregate_func", False),
                            "preset_id": rec.get("preset_id")[0] if isinstance(rec.get("preset_id"), tuple) else rec.get("preset_id", False),
                        }
                    )
                    for rec in sheet["axis_ids"]
                ],
                "table_ids": [
                    fields.Command.create(
                        {
                            "name": table["name"],
                            "model": table["model"],
                            "linked": table["linked"],
                            "field": table["field"],
                            "join": table["join"],
                            "model_id": self.env["ir.model"]
                            .search([("model", "=", table["model"])])
                            .id,
                        }
                    )
                    for table in sheet["table_ids"]
                ],
                "filter_ids": [
                    fields.Command.create(
                        {
                            "name": filter_data.get("name", False),
                            "domain": filter_data.get("domain", False),
                            "is_active": filter_data.get("is_active", False),
                        }
                    )
                    for filter_data in sheet["filter_ids"]
                ],
            }
            for sheet in record
        ]
        return self.create(create_val)

    def fetch_data(self, field_list, config_id):
        """Method to fetch data related to the sheet."""
        sub_data = (
            self.dashboard_sheet_option_ids.filtered(
                lambda res: res.dashboard_config_id.id == config_id
            )
            .sorted(key="id", reverse=False)
            .read(["attributes"])
        )
        rec = self.read(field_list)[0]
        rec["dashboard_sheet_option_ids"] = sub_data
        rec["filter_ids"] = self.filter_ids.read(
            ["name", "domain", "is_active", "sheet_id", "domain_py_expression"]
        )
        rec["table_ids"] = self.table_ids.read()
        rec["axis_ids"] = self.axis_ids.read()
        filters = self.sheet_filter_ids.filtered(
            lambda res: res.global_filter_id.dashboard_config_id.id == config_id
        )
        rec["sheet_filter_ids"] = (
            [filter_id.get_data() for filter_id in filters] if filters else []
        )
        return rec


class DashboardSheetFilter(models.Model):
    """Dashboard Sheet filter Model"""
    _name = "dashboard.sheet.filter"
    _description = "Dashboard Sheet filter"

    sheet_id = fields.Many2one("dashboard.sheet")
    name = fields.Char(required=True)
    domain = fields.Text()
    domain_py_expression = fields.Json()
    is_active = fields.Boolean("Active", default=True)



class DashboardSheetTable(models.Model):
    """Model representing tables used in dashboard sheets."""
    _name = "dashboard.sheet.table"
    _description = "Dashboard Sheet Table"

    name = fields.Char(required=True)
    model = fields.Char(required=True)
    linked = fields.Char("Linked String")
    field = fields.Char()
    join = fields.Text(required=True)
    sheet_id = fields.Many2one("dashboard.sheet")
    model_id = fields.Many2one(
        "ir.model",
        compute="_compute_model_id"
    )

    @api.depends("model")
    def _compute_model_id(self):
        """"""
        for rec in self:
            rec.model_id = (
                self.env["ir.model"].sudo().search([("model", "=", rec.model)],
                                                   limit=1)
            )


class DashboardSheetAxis(models.Model):
    """Model representing axis values used in dashboard sheets."""
    _name = "dashboard.sheet.axis"
    _description = "Dashboard Sheet Axis"
    _rec_name = "value"

    value = fields.Char("Name")
    alias = fields.Char("Alias")
    query = fields.Text("Text")
    monetaryInBase = fields.Text("Base Value Query")
    column = fields.Char("Column")
    source_column = fields.Char("Source Column", help="Original column before TO_CHAR grouping (e.g. sale_order.create_date)")
    date_group = fields.Char("Date Group", help="Date grouping level: Day, Month, or Year")
    type = fields.Selection(
        selection=[
            ("measure", "Measure"),
            ("dimension", "Dimension"),
            ("group", "Group By"),
            ("order", "Order By"),
        ]
    )
    sort_desc = fields.Boolean("Sort Descending", default=False)
    is_preset = fields.Boolean("Is Preset", default=False)
    raw_formula = fields.Text("Raw Formula")
    variables = fields.Text("Variables")
    calculation_type = fields.Selection([
        ('row', 'Row-level'),
        ('aggregate', 'Aggregated')
    ], string='Calculation Type')
    aggregate_func = fields.Selection([
        ('SUM', 'Sum'),
        ('AVG', 'Average'),
        ('MIN', 'Minimum'),
        ('MAX', 'Maximum'),
        ('COUNT', 'Count')
    ], string='Aggregate Function')
    variable_configs = fields.Text(
        "Variable Configs (JSON)",
        help="JSON: per-variable aggregation, filters, and time ranges"
    )
    preset_id = fields.Many2one(
        "calculation.preset",
        string="Template Preset",
        ondelete="set null"
    )
    sheet_id = fields.Many2one(
        "dashboard.sheet",
        "Sheet"
    )


class DashboardSheetGlobal(models.Model):
    """Model representing global filters used in dashboard sheets."""
    _name = "dashboard.sheet.global"
    _description = "Dashboard Sheet Global"

    global_filter_id = fields.Many2one("dashboard.global.filter")
    field = fields.Char()
    name = fields.Char()
    sheet_id = fields.Many2one("dashboard.sheet")

    def get_data(self):
        """Retrieve data related to the global filter."""
        rec = self.read(["field", "name", "sheet_id"])[0]
        rec["global_filter_id"] = self.global_filter_id.read(
            ["name", "type", "dashboard_config_id", "relation", "code",
             "operator"]
        )[0]
        return rec


class DashboardSheetColorMapping(models.Model):
    """Model representing color mapping for measures in dashboard sheets."""
    _name = "dashboard.sheet.color.mapping"
    _description = "Dashboard Sheet Color Mapping"

    sheet_id = fields.Many2one("dashboard.sheet", string="Sheet", ondelete="cascade")
    measure_alias = fields.Char(string="Measure Alias")
    min_value = fields.Float(string="Min Value")
    max_value = fields.Char(string="Max Value")
    color = fields.Char(string="Color", default="#344BD2")
    indicator = fields.Char(string="Indicator")
    notes = fields.Text(string="Notes")


class DashboardSheetAnnotation(models.Model):
    """Dedicated model for user-added business annotations/notes on specific chart points."""
    _name = "dashboard.sheet.annotation"
    _description = "Dashboard Sheet Annotation"

    sheet_id = fields.Many2one("dashboard.sheet", string="Sheet", ondelete="cascade")
    measure_alias = fields.Char(string="Measure Alias")
    dimension_label = fields.Char(string="Dimension Label")
    notes = fields.Text(string="Notes")


