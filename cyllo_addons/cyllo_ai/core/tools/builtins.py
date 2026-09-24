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
Built-in tools — thin wrappers over the ``chatbot.tools`` implementations.

Each tool declares its name/description/schema/read-only flag (the engine uses
these for native function-calling) and dispatches to the ORM-bound method on
``chatbot.tools`` via the runtime context's ``env``. Company scope and the
originating query are injected from the context, never taken from the LLM.
"""
from .base import Tool, ToolContext
from .communication import SendEmailTool, SendTextTool, SendInternalMessageTool
from .functional import DescribeFeatureTool, FindMenuTool, FindSettingTool
from ..registry import ToolRegistry


class FinancialMetricTool(Tool):
    name = "financial_metric"
    label = "Computing financial metric"
    description = (
        "Compute a defined accounting metric (gross profit, revenue, expenses, net "
        "profit, assets, liabilities, equity) using Cyllo's official accounting "
        "report engine — the same calculation as Reporting > Accounting Reports. "
        "ALWAYS use this for accounting/financial metric questions; NEVER compute "
        "them with aggregate_records, search_records or analytic_record (those "
        "give wrong accounting numbers)."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "enum": ["gross_profit", "revenue", "expenses", "net_profit",
                         "total_assets", "current_assets", "total_liabilities",
                         "current_liabilities", "equity"],
                "description": "The accounting metric to compute.",
            },
            "period": {
                "type": "string",
                "enum": ["this_month", "last_month", "this_quarter", "last_quarter",
                         "this_year", "ytd", "last_year"],
                "description": "Named reporting period (server resolves the exact "
                               "dates). Mapping: 'current/this month' -> this_month; "
                               "'past/last/previous month' -> last_month; "
                               "'this year so far / year to date' -> ytd; "
                               "'this year' (full year) -> this_year. "
                               "Omit when giving explicit start_date/end_date.",
            },
            "start_date": {"type": "string",
                           "description": "Custom period start, YYYY-MM-DD."},
            "end_date": {"type": "string",
                         "description": "Custom period end, YYYY-MM-DD."},
        },
        "required": ["metric"],
    }

    def run(self, ctx: ToolContext, metric, period=None, start_date=None, end_date=None):
        return ctx.env['chatbot.tools'].financial_metric(
            metric, period, start_date, end_date, ctx.company_ids)


class AccountingReportTool(Tool):
    name = "accounting_report"
    label = "Opening accounting report"
    description = (
        "Get a link to an official accounting report (with headline totals where "
        "available): trial balance, general ledger, partner ledger, aged "
        "receivable/payable, tax report, cash/bank book, profit & loss, balance "
        "sheet. Use this for any accounting REPORT request, and as the fallback "
        "when no financial_metric matches. These reports are engines, NOT "
        "searchable models — never use search_records for them."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "report": {
                "type": "string",
                "enum": ["trial_balance", "general_ledger", "partner_ledger",
                         "aged_receivable", "aged_payable", "tax_report",
                         "cash_book", "bank_book", "profit_and_loss",
                         "balance_sheet"],
                "description": "Which official report.",
            },
            "period": {
                "type": "string",
                "enum": ["this_month", "last_month", "this_quarter", "last_quarter",
                         "this_year", "ytd", "last_year"],
                "description": "Named reporting period (server resolves the exact "
                               "dates). Mapping: 'current/this month' -> this_month; "
                               "'current/this year' -> this_year. Omit when giving "
                               "explicit start_date/end_date.",
            },
            "start_date": {"type": "string",
                           "description": "Custom period start, YYYY-MM-DD."},
            "end_date": {"type": "string",
                         "description": "Custom period end, YYYY-MM-DD."},
            "partners": {
                "type": "array", "items": {"type": "string"},
                "description": "Partner names (or ids) to filter by. Applies to "
                               "partner_ledger, cash_book and bank_book.",
            },
            "journals": {
                "type": "array", "items": {"type": "string"},
                "description": "Journal names (or ids) to filter by.",
            },
            "analytics": {
                "type": "array", "items": {"type": "string"},
                "description": "Analytic account names (or ids) to filter by.",
            },
            "accounts": {
                "type": "array", "items": {"type": "string"},
                "description": "Account names/codes (or ids) to filter by.",
            },
            "include_draft": {
                "type": "boolean",
                "description": "Include draft (unposted) entries. Default false "
                               "(posted only).",
            },
        },
        "required": ["report"],
    }

    def run(self, ctx: ToolContext, report, period=None, start_date=None, end_date=None,
            partners=None, journals=None, analytics=None, accounts=None,
            include_draft=False):
        return ctx.env['chatbot.tools'].accounting_report(
            report, period, start_date, end_date,
            partners, journals, analytics, accounts,
            include_draft, ctx.company_ids)


class ReadAccountingReportTool(Tool):
    name = "read_accounting_report"
    label = "Reading report data"
    description = (
        "Read a bounded summary of an official accounting report's CONTENTS for "
        "analysis and comparison: per-partner ledger totals, aging buckets, "
        "account balances, P&L/balance-sheet figures. Use when the user wants "
        "analysis, comparison or details of report data — not just a link. All "
        "numbers come from the official engines: present them as-is; when you "
        "compute a difference or ratio, show both operands. Still include the "
        "report_link in your answer."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "report": {
                "type": "string",
                "enum": ["partner_ledger", "aged_receivable", "aged_payable",
                         "trial_balance", "profit_and_loss", "balance_sheet"],
                "description": "Which report's data to read.",
            },
            "period": {
                "type": "string",
                "enum": ["this_month", "last_month", "this_quarter", "last_quarter",
                         "this_year", "ytd", "last_year"],
                "description": "Named reporting period. For aged reports the "
                               "period END date is used as the as-of date. Omit "
                               "when giving explicit start_date/end_date.",
            },
            "start_date": {"type": "string",
                           "description": "Custom period start, YYYY-MM-DD."},
            "end_date": {"type": "string",
                         "description": "Custom period end, YYYY-MM-DD."},
            "partners": {
                "type": "array", "items": {"type": "string"},
                "description": "Partner names (or ids) to restrict to — e.g. for "
                               "comparing specific partners.",
            },
            "include_draft": {
                "type": "boolean",
                "description": "Include draft entries (not applicable to aged "
                               "reports). Default false.",
            },
            "limit": {"type": "integer",
                      "description": "Max partners/accounts in the summary "
                                     "(default 20, max 80)."},
        },
        "required": ["report"],
    }

    def run(self, ctx: ToolContext, report, period=None, start_date=None, end_date=None,
            partners=None, include_draft=False, limit=20):
        return ctx.env['chatbot.tools'].read_accounting_report(
            report, period, start_date, end_date,
            partners, include_draft, limit, ctx.company_ids)


class SearchRecordsTool(Tool):
    name = "search_records"
    label = "Fetching records"
    description = (
        "Retrieve records from a Cyllo model with an Odoo domain filter. Use for "
        "lists, lookups and simple retrieval ('show/list/find/latest X'). Dotted "
        "paths work in domains (e.g. partner_id.country_id.code). Respects the "
        "user's access rights automatically. Prefer this over analytic_record "
        "whenever it can express the question."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "Model name, e.g. 'sale.order'."},
            "domain": {
                "type": "array", "items": {},
                "description": "Odoo domain, e.g. [[\"state\",\"=\",\"sale\"]]. "
                               "Empty/omitted for all records.",
            },
            "fields": {
                "type": "array", "items": {"type": "string"},
                "description": "Fields to return. If omitted, the model's key "
                               "business fields (name, partner, date, amount, "
                               "state) are returned automatically.",
            },
            "limit": {"type": "integer", "description": "Max records (default 80, max 200)."},
            "order": {"type": "string", "description": "Sort, e.g. 'date_order desc'."},
        },
        "required": ["model"],
    }

    def run(self, ctx: ToolContext, model, domain=None, fields=None, limit=None, order=None):
        return ctx.env['chatbot.tools'].search_records(
            model, domain, fields, limit, order, ctx.company_ids)


class CountRecordsTool(Tool):
    name = "count_records"
    label = "Counting records"
    description = "Count records of a Cyllo model matching an Odoo domain filter."
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "Model name, e.g. 'sale.order'."},
            "domain": {"type": "array", "items": {},
                       "description": "Odoo domain. Empty/omitted counts all records."},
        },
        "required": ["model"],
    }

    def run(self, ctx: ToolContext, model, domain=None):
        return ctx.env['chatbot.tools'].count_records(model, domain, ctx.company_ids)


class AggregateRecordsTool(Tool):
    name = "aggregate_records"
    label = "Aggregating data"
    description = (
        "Grouped aggregation over a Cyllo model (totals, averages, counts by group). "
        "Use for 'total/sum/average/breakdown of X by Y' questions. groupby supports "
        "date granularity like 'date_order:month'. Prefer this over analytic_record "
        "for single-model aggregations."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "Model name, e.g. 'sale.order'."},
            "domain": {"type": "array", "items": {},
                       "description": "Odoo domain filter applied before grouping."},
            "groupby": {
                "type": "array", "items": {"type": "string"},
                "description": "Fields to group by (direct fields only, no dotted paths). "
                               "Date fields accept granularity: 'date_order:month'.",
            },
            "aggregates": {
                "type": "array", "items": {"type": "string"},
                "description": "Numeric aggregations as 'field:op' with op in "
                               "sum/avg/min/max/count, e.g. 'amount_total:sum'.",
            },
        },
        "required": ["model"],
    }

    def run(self, ctx: ToolContext, model, domain=None, groupby=None, aggregates=None):
        return ctx.env['chatbot.tools'].aggregate_records(
            model, domain, groupby, aggregates, ctx.company_ids)


class GetModelFieldsTool(Tool):
    name = "get_model_fields"
    label = "Inspecting model"
    description = (
        "Describe a Cyllo model: its fields with types and relation targets, plus "
        "which fields are groupable and aggregatable. Call this before building a "
        "domain or aggregation when unsure of exact field names."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "Model name, e.g. 'sale.order'."},
        },
        "required": ["model"],
    }

    def run(self, ctx: ToolContext, model):
        return ctx.env['chatbot.tools'].get_model_fields(model)


class AnalyticRecordTool(Tool):
    name = "analytic_record"
    label = "Analyzing data"
    description = (
        "Run complex SQL analytics over Cyllo business data. Use ONLY for questions "
        "that search_records / aggregate_records cannot express: multi-model joins, "
        "subqueries, or cross-table comparisons. For simple lists use search_records; "
        "for single-model grouped totals use aggregate_records. Never use this for "
        "creating or modifying records."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The analytical question to answer. "
                               "Omit to use the user's current message.",
            },
        },
        "required": [],
    }

    def run(self, ctx: ToolContext, query=None):
        return ctx.env['chatbot.tools'].analytic_record(
            query or ctx.user_query, ctx.company_ids
        )


class WriteRecordsTool(Tool):
    name = "write_records"
    label = "Working on records"
    description = (
        "Create, read, update or delete Cyllo records. Provide the target "
        "`model`, the `action`, a `values` object (field → value; relational "
        "fields accept a name or id; x2many fields accept a list of line "
        "objects), and `filters` for read/update/delete. To change a field that "
        "lives on a related line, target that line's model (filter through the "
        "parent) or set it inside the parent's x2many `values`. Data-modifying "
        "actions are previewed and confirmed with the user automatically — call "
        "this directly, do not ask permission first."
    )
    is_read_only = False
    input_schema = {
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "description": "Target model, e.g. 'sale.order'.",
            },
            "action": {
                "type": "string",
                "enum": ["create", "read", "update", "delete"],
            },
            "values": {
                "type": "object",
                "description": "Field → value map for create/update. Relational "
                               "fields accept a name or id; x2many fields accept "
                               "a list of line objects (each a field → value map).",
                "additionalProperties": True,
            },
            "filters": {
                "type": "array",
                "description": "Conditions for read/update/delete, each a "
                               "[field, operator, value] triple.",
                "items": {"type": "array"},
            },
        },
        "required": ["model", "action"],
    }

    def run(self, ctx: ToolContext, model, action, values=None, filters=None):
        return ctx.env['chatbot.tools'].write_records(
            model, action, values=values, filters=filters)


class GetUrlTool(Tool):
    name = "get_url"
    label = "Building a link"
    description = (
        "Generate a Cyllo record URL from a record id and model, to render a "
        "clickable link to a record. Use only with a verified model + id."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The link text."},
            "record_id": {"type": "string", "description": "The record id."},
            "model": {"type": "string", "description": "The model or table name."},
        },
        "required": ["text", "record_id", "model"],
    }

    def run(self, ctx: ToolContext, text, record_id, model):
        return ctx.env['chatbot.tools'].get_url(text, record_id, model)


class CurrencyConversionTool(Tool):
    name = "currency_conversion"
    label = "Converting currency"
    description = (
        "Convert an amount from one currency to another using Cyllo's configured "
        "exchange rates."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "from_currency_name": {"type": "string"},
            "to_currency_name": {"type": "string"},
        },
        "required": ["amount", "from_currency_name", "to_currency_name"],
    }

    def run(self, ctx: ToolContext, amount, from_currency_name, to_currency_name):
        return ctx.env['chatbot.tools'].currency_conversion(
            amount, from_currency_name, to_currency_name
        )


class GetCurrencyNameTool(Tool):
    name = "get_currency_name"
    label = "Looking up currency"
    description = "Return the currency name for a given currency id."
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {"currency_id": {"type": "integer"}},
        "required": ["currency_id"],
    }

    def run(self, ctx: ToolContext, currency_id):
        return ctx.env['chatbot.tools'].get_currency_name(currency_id)


class RenderChartTool(Tool):
    name = "render_chart"
    label = "Building a chart"
    description = (
        "Render a chart to visualize data for the user. Call this AFTER obtaining "
        "numeric results (e.g. from analytic_record) when a comparison, trend, "
        "distribution or breakdown would help. Then also summarize the result in text."
    )
    is_read_only = True
    input_schema = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line", "pie", "scatter"],
                "description": "The chart type.",
            },
            "title": {"type": "string", "description": "Chart title."},
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "X-axis labels (bar/line) or slice names (pie).",
            },
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
                "description": "One or more data series.",
            },
        },
        "required": ["chart_type", "series"],
    }

    def run(self, ctx: ToolContext, chart_type="bar", title="", categories=None, series=None):
        return ctx.env['chatbot.tools'].render_chart(chart_type, title, categories, series)


# The built-in tool belt (ORM tiers first). Exposed as a constant so the agent
# seam (chatbot.agent._ai_tool_classes) can hand it to other modules to extend
# without editing this list.
DEFAULT_TOOL_CLASSES = (
    FinancialMetricTool,
    AccountingReportTool,
    ReadAccountingReportTool,
    SearchRecordsTool,
    CountRecordsTool,
    AggregateRecordsTool,
    GetModelFieldsTool,
    DescribeFeatureTool,
    FindMenuTool,
    FindSettingTool,
    AnalyticRecordTool,
    WriteRecordsTool,
    SendEmailTool,
    SendTextTool,
    SendInternalMessageTool,
    GetUrlTool,
    CurrencyConversionTool,
    GetCurrencyNameTool,
    RenderChartTool,
)


def build_registry_from(tool_classes) -> ToolRegistry:
    """Build a :class:`ToolRegistry` from an iterable of Tool classes."""
    registry = ToolRegistry()
    for tool_cls in tool_classes:
        registry.register(tool_cls())
    return registry


def build_default_registry() -> ToolRegistry:
    """Return a registry populated with the built-in tools (ORM tiers first)."""
    return build_registry_from(DEFAULT_TOOL_CLASSES)
