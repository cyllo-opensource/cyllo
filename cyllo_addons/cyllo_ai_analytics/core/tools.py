# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
"""
Analytics tools contributed to the Cyllo AI assistant.

Pure ``Tool`` subclasses (framework-free), mirroring how cyllo_ai's built-in
tools wrap ``chatbot.tools``: they declare name/description/schema and dispatch
to this module's ORM model via the runtime context's ``env``.
"""
from odoo.addons.cyllo_ai.core.tools.base import Tool, ToolContext


class RecommendChartTool(Tool):
    name = "recommend_chart"
    label = "Recommending a chart"
    description = (
        "Recommend AND render the best chart for the given data. Provide the "
        "data (categories + one or more numeric series); the system picks the "
        "most suitable chart type — line for a time trend, pie for parts of a "
        "whole, bar for category comparisons, scatter for numeric correlation "
        "— and renders it. Use this when you have data to visualize but want "
        "the chart type chosen for you; use render_chart when you already know "
        "the exact type."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "series": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "data": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["data"],
                },
                "description": "One or more numeric data series.",
            },
            "categories": {
                "type": "array", "items": {"type": "string"},
                "description": "X-axis labels (bar/line) or slice names (pie).",
            },
            "title": {"type": "string", "description": "Chart title."},
            "category_kind": {
                "type": "string",
                "enum": ["category", "time", "number"],
                "description": "What the categories represent: 'time' for "
                               "dates/periods (favours a line), 'number' for a "
                               "numeric axis (favours scatter), or 'category' "
                               "for labels. Guides the recommendation.",
            },
        },
        "required": ["series"],
    }

    def run(self, ctx: ToolContext, series=None, categories=None, title="",
            category_kind="category"):
        return ctx.env["cyllo.ai.analytics.tools"].recommend_chart(
            series, categories, title, category_kind)


class SuggestSheetChartsTool(Tool):
    name = "suggest_sheet_charts"
    label = "Suggesting charts"
    description = (
        "Suggest ready-to-apply charts for the analytics SHEET the user is "
        "currently building. Use this whenever the user asks for chart ideas / "
        "suggestions / recommendations for their sheet, wants more of them, or "
        "asks for charts about a particular topic (e.g. 'charts about "
        "customers', 'revenue by month'). It reads the sheet's own available "
        "dimensions and measures and returns apply-ready cards — do NOT invent "
        "data or use render_chart/recommend_chart for this. Only available when "
        "the user is on a sheet (the sheet context is provided automatically)."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": "The user's intent in their own words, e.g. "
                               "'revenue by month' or 'charts about customers'. "
                               "Leave empty for a general set of suggestions.",
            },
        },
    }

    def run(self, ctx: ToolContext, focus=""):
        sheet_ctx = (ctx.ui_context or {}).get("sheet") or {}
        dims = sheet_ctx.get("dimensions") or []
        meas = sheet_ctx.get("measures") or []
        if not dims or not meas:
            return {"message": "There's no sheet open, or it has no available "
                               "dimension/measure fields yet — ask the user to "
                               "add tables and fields to the sheet first."}
        Sheet = ctx.env["dashboard.sheet"]
        sheet_id = sheet_ctx.get("sheet_id")
        sheet = Sheet.browse(sheet_id) if sheet_id else Sheet
        suggestions = sheet.suggest_charts_for_sheet(dims, meas, focus=focus or None)
        if not suggestions:
            return {"message": "I couldn't find useful chart pairings from the "
                               "sheet's available fields."}
        return {
            "message": f"Here are {len(suggestions)} chart suggestion(s).",
            "suggestions": suggestions,
        }


class EditCurrentChartTool(Tool):
    name = "edit_current_chart"
    label = "Updating the chart"
    description = (
        "Modify the chart the user ALREADY has on the analytics sheet — change "
        "its type (bar/line/pie/doughnut/radar/scatter/…), its dimension "
        "(group-by), and/or its measure. Use this whenever the user refers to "
        "the existing chart: 'make it a pie', 'show it by customer', 'use "
        "quantity instead', 'switch to a line'. For brand-new chart IDEAS use "
        "suggest_sheet_charts instead. Pass ONLY the parts that change; pick any "
        "dimension/measure from the sheet's available fields (provided in "
        "context). The change is applied to the sheet immediately."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "description": "New chart type, e.g. 'bar', 'line', 'pie', "
                               "'doughnut', 'radar', 'scatter'. Omit to keep the "
                               "current type.",
            },
            "dimension_column": {
                "type": "string",
                "description": "New dimension column (from the available list). "
                               "Omit to keep the current dimension.",
            },
            "measure_column": {
                "type": "string",
                "description": "New measure column (from the available list). "
                               "Omit to keep the current measure.",
            },
        },
    }

    def run(self, ctx: ToolContext, chart_type="", dimension_column="", measure_column=""):
        sheet_ctx = (ctx.ui_context or {}).get("sheet") or {}
        current = sheet_ctx.get("current_chart") or {}
        if not current:
            return {"message": "There's no chart on the sheet to edit yet — ask "
                               "for a suggestion first (e.g. 'suggest charts')."}
        # Type-only change: no need to touch the dimension/measure — flip the type.
        if chart_type and not dimension_column and not measure_column:
            return {"message": f"Switching the chart to {chart_type}.",
                    "apply_edit": {"chart_type": chart_type}}
        # Dimension/measure change: fill the unspecified side from the current chart.
        dim_col = dimension_column or (current.get("dimension") or {}).get("column")
        meas_col = measure_column or (current.get("measure") or {}).get("column")
        if not dim_col or not meas_col:
            return {"message": "I can only refine a chart I set up here. Try "
                               "asking for a fresh suggestion (e.g. 'suggest "
                               "charts by customer')."}
        dims = sheet_ctx.get("dimensions") or []
        meas = sheet_ctx.get("measures") or []
        Sheet = ctx.env["dashboard.sheet"]
        sheet_id = sheet_ctx.get("sheet_id")
        sheet = Sheet.browse(sheet_id) if sheet_id else Sheet
        ctype = chart_type or current.get("chart_type")
        suggestion = sheet.build_chart_suggestion(dim_col, meas_col, ctype, dims, meas)
        if not suggestion:
            return {"message": "I couldn't build that change from the sheet's "
                               "available fields."}
        return {"message": "Updating the chart.", "apply_edit": {"suggestion": suggestion}}


class OpenQuickDashboardTool(Tool):
    name = "open_quick_dashboard"
    label = "Opening the dashboard builder"
    description = (
        "Open the quick-dashboard BUILDER in the chat. Use this whenever the user "
        "asks to create / build / make a dashboard (e.g. 'create a dashboard', "
        "'build me a sales dashboard', 'make a dashboard for sales and "
        "purchases'). It shows a builder card where they pick table(s) and get "
        "chart proposals. If the user named the subject area(s) — 'sales', "
        "'purchases', 'inventory' — pass them as `tables` and the builder opens "
        "pre-filled and generates proposals automatically. This tool only OPENS "
        "the builder; the user curates and creates from there (or asks you to)."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "tables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subject areas or table names the dashboard is "
                               "about, in the user's words (e.g. ['sales', "
                               "'purchase']) or technical model names (e.g. "
                               "['sale.order']). Leave empty if the user didn't "
                               "say — the builder opens with an empty picker.",
            },
        },
    }

    def run(self, ctx: ToolContext, tables=None):
        seed = ctx.env["dashboard.sheet"].resolve_analytics_models(tables or [])
        if seed:
            names = ", ".join(m["name"] for m in seed)
            msg = (f"Opening the dashboard builder for {names} and generating "
                   "chart proposals.")
        else:
            msg = ("Opening the dashboard builder — pick the table(s) you want "
                   "and I'll suggest charts.")
        return {
            "message": msg,
            "widget": {
                "key": "quick_dashboard",
                "props": {"seed_models": seed, "auto_generate": bool(seed)},
            },
        }


class EditQuickDashboardTool(Tool):
    name = "edit_quick_dashboard"
    label = "Updating the dashboard builder"
    description = (
        "Change the quick-dashboard BUILDER the user is currently curating in the "
        "chat (the card panel with checkboxes). Use this for their edits while "
        "the builder is open: change a proposed chart's TYPE ('make the customer "
        "chart a pie'), keep/drop a chart ('remove the vendor one', 'only the "
        "first two'), add/remove a table ('add purchases'), rename it ('call it "
        "Q3 Review'), or create it ('create it', 'go ahead'). Reference a chart "
        "by its `card_id` from the builder context; match it from the title the "
        "user names, and ask which one if two are close. Only offer a chart type "
        "listed in that chart's allowed types."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set_chart_type", "toggle_chart", "add_table",
                         "remove_table", "rename", "create"],
                "description": "The change to make.",
            },
            "card_id": {
                "type": "string",
                "description": "Target chart's id (for set_chart_type / "
                               "toggle_chart), from the builder context.",
            },
            "chart_type": {
                "type": "string",
                "description": "New type for set_chart_type — must be one of the "
                               "target chart's allowed types.",
            },
            "selected": {
                "type": "boolean",
                "description": "For toggle_chart: true to keep the chart, false "
                               "to drop it.",
            },
            "table": {
                "type": "string",
                "description": "For add_table / remove_table: the subject area or "
                               "model, in the user's words or a technical name.",
            },
            "name": {
                "type": "string",
                "description": "For rename: the new dashboard name.",
            },
        },
        "required": ["action"],
    }

    def run(self, ctx: ToolContext, action="", card_id="", chart_type="",
            selected=None, table="", name=""):
        qd = (ctx.ui_context or {}).get("quick_dashboard") or {}
        cards = qd.get("cards") or []
        if not qd:
            return {"message": "There's no dashboard builder open — open one first "
                               "with open_quick_dashboard."}

        def _card(cid):
            return next((c for c in cards if str(c.get("id")) == str(cid)), None)

        if action == "set_chart_type":
            card = _card(card_id)
            if not card:
                return {"message": "I couldn't tell which chart to change — ask "
                                   "the user which one (by its title)."}
            allowed = card.get("allowed_chart_types") or []
            if chart_type not in allowed:
                return {"message": f'"{card.get("title")}" can be: '
                                   f'{", ".join(allowed) or "(none)"}. '
                                   f'"{chart_type}" is not available for it.'}
            return {"message": f'Changing "{card.get("title")}" to a {chart_type} chart.',
                    "apply_qd": {"action": "set_chart_type",
                                 "card_id": card.get("id"), "chart_type": chart_type}}

        if action == "toggle_chart":
            card = _card(card_id)
            if not card:
                return {"message": "I couldn't tell which chart you meant — ask "
                                   "the user which one (by its title)."}
            keep = bool(selected)
            return {"message": ("Keeping" if keep else "Removing")
                    + f' "{card.get("title")}".',
                    "apply_qd": {"action": "toggle_chart",
                                 "card_id": card.get("id"), "selected": keep}}

        if action == "add_table":
            resolved = ctx.env["dashboard.sheet"].resolve_analytics_models([table])
            if not resolved:
                return {"message": f'I couldn\'t find a table matching "{table}".'}
            m = resolved[0]
            return {"message": f'Adding {m["name"]} and generating its charts.',
                    "apply_qd": {"action": "add_table", "model": m["model"],
                                 "name": m["name"]}}

        if action == "remove_table":
            tables = qd.get("tables") or []
            t = (table or "").strip().lower()
            match = next((x for x in tables if isinstance(x, dict) and (
                x.get("model") == table
                or t and (t in (x.get("name") or "").lower()
                          or t in (x.get("model") or "").lower()))), None)
            if not match:
                return {"message": f'"{table}" isn\'t one of the picked tables.'}
            return {"message": f'Removing {match.get("name")}.',
                    "apply_qd": {"action": "remove_table", "model": match.get("model")}}

        if action == "rename":
            if not (name or "").strip():
                return {"message": "What should the dashboard be called?"}
            return {"message": f'Renaming the dashboard to "{name.strip()}".',
                    "apply_qd": {"action": "rename", "name": name.strip()}}

        if action == "create":
            if not any(c.get("selected") for c in cards):
                return {"message": "No charts are selected yet — keep at least one "
                                   "before creating the dashboard."}
            return {"message": "Creating the dashboard.",
                    "apply_qd": {"action": "create"}}

        return {"message": f"Unknown builder action: {action}."}


class EditLiveDashboardTool(Tool):
    name = "edit_dashboard"
    label = "Updating the dashboard"
    description = (
        "Edit the CREATED dashboard the user is currently VIEWING (not the "
        "pre-create builder). Use this when a live dashboard is in context and "
        "the user asks to change it: change a chart's TYPE ('make the revenue "
        "chart a pie'), DROP a chart ('remove the vendor one'), ADD a chart "
        "('add sales by customer', 'chart purchases by vendor'), or RENAME the "
        "dashboard. Changes are saved to the dashboard immediately and it "
        "refreshes. Reference an existing chart by its `sheet_id` from the "
        "dashboard context; match it from the name the user says, and ask which "
        "one if two are close. Only set a chart type from that chart's allowed "
        "types. For ADD, name the `table` and (optionally) what to chart in "
        "`focus` — the chart is built and validated server-side."
    )
    # Writes to real records (reversible + access-checked); NOT read-only.
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set_chart_type", "drop_chart", "add_chart", "rename"],
                "description": "The change to make.",
            },
            "sheet_id": {
                "type": "integer",
                "description": "Target chart's sheet id (for set_chart_type / "
                               "drop_chart), from the dashboard context.",
            },
            "chart_type": {
                "type": "string",
                "description": "New type for set_chart_type (must be an allowed "
                               "type for that chart); optional preferred type for "
                               "add_chart.",
            },
            "table": {
                "type": "string",
                "description": "For add_chart: the table/subject to chart, in the "
                               "user's words or a technical model name.",
            },
            "focus": {
                "type": "string",
                "description": "For add_chart: what to chart, in the user's words "
                               "(e.g. 'revenue by customer'). Optional.",
            },
            "name": {
                "type": "string",
                "description": "For rename: the new dashboard name.",
            },
        },
        "required": ["action"],
    }

    def run(self, ctx: ToolContext, action="", sheet_id=None, chart_type="",
            table="", focus="", name=""):
        dash = (ctx.ui_context or {}).get("dashboard") or {}
        config_id = dash.get("config_id")
        if not config_id:
            return {"message": "There's no dashboard open to edit — open or view a "
                               "dashboard first (or use the builder to create one)."}
        Sheet = ctx.env["dashboard.sheet"]

        if action == "set_chart_type":
            res = Sheet.ai_dashboard_set_chart_type(config_id, sheet_id, chart_type)
            done = f'Changed "{res.get("title")}" to a {chart_type} chart.'
        elif action == "drop_chart":
            res = Sheet.ai_dashboard_drop_chart(config_id, sheet_id)
            done = f'Removed "{res.get("title")}" from the dashboard.'
        elif action == "add_chart":
            res = Sheet.ai_dashboard_add_chart(config_id, table, focus, chart_type)
            done = f'Added "{res.get("title")}" to the dashboard.'
        elif action == "rename":
            res = Sheet.ai_dashboard_rename(config_id, name)
            done = f'Renamed the dashboard to "{res.get("name")}".'
        else:
            return {"message": f"Unknown dashboard action: {action}."}

        if res.get("error"):
            return {"message": res["error"]}
        return {"message": done,
                "apply_dash": {"action": "reload", "config_id": config_id}}
