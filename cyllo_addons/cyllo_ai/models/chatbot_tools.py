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
"""
ORM-bound tool implementations for the Cyllo AI engine.

Per the hybrid design, env-heavy tool logic lives on an ``AbstractModel``
(natural ``self.env`` access, runs as the user so ``ir.rules`` apply), while
the framework-agnostic engine lives in ``core/``. These methods are the
working implementations of analytics/CRUD/utility tools; the tool-dispatch
loop that registers and calls them lands in a later phase. The orchestrator
will reach them via ``env['chatbot.tools']``.
"""
import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict

from dateutil.relativedelta import relativedelta

import psycopg2
from odoo import models
from odoo.exceptions import AccessError
from odoo.fields import Date, _logger
from odoo.tools import SQL, Query, plaintext2html

from odoo.addons.cyllo_ai.core.field_security import SENSITIVE_COLUMNS
from odoo.addons.cyllo_ai.core.llm_client import LLMClient
from odoo.addons.cyllo_ai.core.retrieval.schema_index import SchemaIndex
from odoo.addons.cyllo_ai.core.retrieval.sql_guard import validate_plan

# Always offered to the query planner — joined in most analytical queries.
ALWAYS_MODELS = ['res.partner', 'res.currency']
# Common business models that cover synonyms keyword-search misses
# (e.g. "customers" -> res.partner). Only those present in the DB are used.
CORE_MODELS = [
    'res.partner', 'res.users', 'res.company', 'res.currency',
    'sale.order', 'sale.order.line',
    'purchase.order', 'purchase.order.line',
    'account.move', 'account.move.line', 'account.journal',
    'product.template', 'product.product', 'product.category',
    'stock.picking', 'stock.move', 'stock.quant', 'stock.location',
    'crm.lead', 'hr.employee', 'project.project', 'project.task', 'pos.order',
]
# When a header model is selected, include its line model so joins within a
# domain stay complete.
FAMILY_MODELS = {
    'sale.order': ['sale.order.line'],
    'purchase.order': ['purchase.order.line'],
    'account.move': ['account.move.line'],
    'stock.picking': ['stock.move'],
    'pos.order': ['pos.order.line'],
}

# ORM tier (search_records / aggregate_records) row caps
ORM_DEFAULT_LIMIT = 80
ORM_MAX_LIMIT = 200
GROUP_GRANULARITIES = {'year', 'quarter', 'month', 'week', 'day', 'hour'}
AGG_OPERATORS = {'sum', 'avg', 'min', 'max', 'count'}

# analytic_record (LLM-generated SQL) guardrails
ANALYTIC_DEFAULT_LIMIT = 200      # applied when the plan gives no limit
ANALYTIC_MAX_LIMIT = 500          # hard cap, whatever the plan asks for
ANALYTIC_TIMEOUT_MS = 15000       # statement_timeout on the sandbox cursor
ANALYTIC_ATTEMPTS = 2             # first try + one structured retry
# Markers that would let an LLM-authored fragment smuggle a second statement
# or comment-out the rest of the query we build around it.
SQL_BANNED_MARKERS = (';', '--', '/*')
# SENSITIVE_COLUMNS (credential fields never returned via raw analytics SQL) is
# imported from core.field_security so every raw-analytics path denies the same
# set. Group-restricted fields are handled separately, per field, via `groups`.
# Keys in the LLM's query plan holding parameter VALUES — passed to the
# driver separately (never interpolated), so they are exempt from the
# marker scan and may legitimately contain any character.
SQL_PARAM_KEYS = {'where_params', 'params'}

# Tier-0 metric registry: metric -> how the canonical accounting engine
# (abstract.financial.report.get_report — the SAME method the on-screen
# reports call) exposes it, and which report the link should open.
# '__income_total__' is the raw income account-type total (true revenue);
# the engine's 'total_income' key already nets out direct costs.
FINANCIAL_METRICS = {
    'gross_profit': {'source': 'gross_profit', 'report': 'Profit & Loss',
                     'action': 'cyllo_accounting.action_dynamic_profit_and_loss'},
    'revenue': {'source': '__income_total__', 'report': 'Profit & Loss',
                'action': 'cyllo_accounting.action_dynamic_profit_and_loss'},
    'expenses': {'source': 'total_expense', 'report': 'Profit & Loss',
                 'action': 'cyllo_accounting.action_dynamic_profit_and_loss'},
    'net_profit': {'source': 'total_earnings', 'report': 'Profit & Loss',
                   'action': 'cyllo_accounting.action_dynamic_profit_and_loss'},
    'total_assets': {'source': 'total_assets', 'report': 'Balance Sheet',
                     'action': 'cyllo_accounting.action_dynamic_balance_sheet'},
    'current_assets': {'source': 'total_current_asset', 'report': 'Balance Sheet',
                       'action': 'cyllo_accounting.action_dynamic_balance_sheet'},
    'total_liabilities': {'source': 'total_liability', 'report': 'Balance Sheet',
                          'action': 'cyllo_accounting.action_dynamic_balance_sheet'},
    'current_liabilities': {'source': 'total_current_liability', 'report': 'Balance Sheet',
                            'action': 'cyllo_accounting.action_dynamic_balance_sheet'},
    'equity': {'source': 'total_equity', 'report': 'Balance Sheet',
               'action': 'cyllo_accounting.action_dynamic_balance_sheet'},
}
FINANCIAL_PERIODS = ('this_month', 'last_month', 'this_quarter', 'last_quarter',
                     'this_year', 'ytd', 'last_year')

# Official accounting reports: link target + (where cheaply available) which
# engine to invoke for headline figures. These are report ENGINES, not
# searchable models.
ACCOUNTING_REPORTS = {
    'profit_and_loss': {'label': 'Profit & Loss',
                        'action': 'cyllo_accounting.action_dynamic_profit_and_loss',
                        'headline': 'pnl'},
    'balance_sheet': {'label': 'Balance Sheet',
                      'action': 'cyllo_accounting.action_dynamic_balance_sheet',
                      'headline': 'balance'},
    'trial_balance': {'label': 'Trial Balance',
                      'action': 'cyllo_accounting.action_dynamic_trial_balance',
                      'headline': 'trial'},
    'general_ledger': {'label': 'General Ledger',
                       'action': 'cyllo_accounting.action_dynamic_general_ledger'},
    'partner_ledger': {'label': 'Partner Ledger',
                       'action': 'cyllo_accounting.action_dynamic_partner_ledger'},
    'aged_receivable': {'label': 'Aged Receivable',
                        'action': 'cyllo_accounting.action_aged_receivable'},
    'aged_payable': {'label': 'Aged Payable',
                     'action': 'cyllo_accounting.action_aged_payable'},
    'tax_report': {'label': 'Tax Report',
                   'action': 'cyllo_accounting.action_dynamic_tax_report'},
    'cash_book': {'label': 'Cash Book',
                  'action': 'cyllo_accounting.action_dynamic_cash_book'},
    'bank_book': {'label': 'Bank Book',
                  'action': 'cyllo_accounting.action_dynamic_bank_book'},
}

# Deep-link filters: tool argument -> (model to resolve names against, URL param).
# The report UI applies whichever of these it supports and ignores the rest.
REPORT_FILTERS = {
    'partners': ('res.partner', 'cyllo_partner_ids'),
    'journals': ('account.journal', 'cyllo_journal_ids'),
    'analytics': ('account.analytic.account', 'cyllo_analytic_ids'),
    'accounts': ('account.account', 'cyllo_account_ids'),
}

# Reports whose contents can be read (summarized) for analysis, not just linked.
READABLE_REPORTS = {'partner_ledger', 'aged_receivable', 'aged_payable',
                    'trial_balance', 'profit_and_loss', 'balance_sheet'}
# Aged engine bucket keys -> readable names (UI columns: At Date, 1-30, ... Older)
AGED_BUCKETS = [('diff0_sum', 'at_date'), ('diff1_sum', 'overdue_1_30'),
                ('diff2_sum', 'overdue_31_60'), ('diff3_sum', 'overdue_61_90'),
                ('diff4_sum', 'overdue_91_120'), ('diff5_sum', 'older')]


class CylloQuery(Query):
    group_by = None

    def select(self, *args: str | SQL) -> SQL:
        """ Return the SELECT query as an ``SQL`` object. """
        sql_args = map(SQL, args) if args else [SQL.identifier(self.table, 'id')]
        return SQL(
            "%s%s%s%s%s%s%s",
            SQL("SELECT %s", SQL(", ").join(sql_args)),
            SQL(" FROM %s", self.from_clause),
            SQL(" WHERE %s", self.where_clause) if self._where_clauses else SQL(),
            SQL(f" GROUP BY {self.group_by}") if self.group_by else SQL(),
            SQL(" ORDER BY %s", self._order) if self._order else SQL(),
            SQL(" LIMIT %s", self.limit) if self.limit else SQL(),
            SQL(" OFFSET %s", self.offset) if self.offset else SQL(),
        )


class ChatbotTools(models.AbstractModel):
    """Tool implementations (analytics, CRUD, utilities) for the agent."""
    _name = "chatbot.tools"
    _description = "Chatbot Tool Implementations"

    def _register_hook(self):
        """Drop the cached schema on every registry load (covers module
        installs/upgrades and Studio field changes, which reload the registry)."""
        res = super()._register_hook()
        SchemaIndex.invalidate(self.env.cr.dbname)
        return res

    # -------------------------------------------------------------------------
    # LLM access (delegates to the core, framework-free client)
    # -------------------------------------------------------------------------

    def _call_llm(self, prompt):
        """Call the configured LLM via the core client and return its text."""
        return LLMClient(self.env).complete(prompt)

    # -------------------------------------------------------------------------
    # Model / table resolution helpers (delegated to the cached SchemaIndex)
    # -------------------------------------------------------------------------

    def _schema(self):
        return SchemaIndex(self.env)

    def _get_model_from_table(self, tables):
        """Retrieve model names for given table names (pass through model names)."""
        if not tables:
            return []
        if isinstance(tables, str):
            tables = [tables]
        schema = self._schema()
        return [schema.model_from_table(t) for t in tables]

    def _get_table_from_model(self, inputs):
        """Retrieve table names for given model names (pass through table names)."""
        if not inputs:
            return []
        if isinstance(inputs, str):
            inputs = [inputs]
        schema = self._schema()
        return [schema.table_from_model(m) for m in inputs]

    def _get_model_name(self):
        """Select appropriate model names where _auto = True (cached)."""
        return self._schema().auto_model_names()

    def _candidate_models(self, user_query, limit=25):
        """
        Deterministically pick the models a query likely needs — NO LLM call.

        Order (so nothing important is starved by the cap):
          1. always-models (partner/currency) — kept first, never dropped
          2. keyword-search hits — query-specific, incl. niche/custom models
          3. common business models — synonym coverage
          4. sibling line models of anything selected — join completeness
        Capped, present-only. Replaces the per-tool "table selector" LLM
        round-trip that used to dump the entire model list.
        """
        schema = self._schema()
        ordered, seen = [], set()

        def add(model):
            if model not in seen and schema.has_model(model):
                ordered.append(model)
                seen.add(model)

        for m in ALWAYS_MODELS:
            add(m)
        for hit in schema.search_models(user_query, limit=limit):
            add(hit['model'])
        for m in CORE_MODELS:
            add(m)
        for m in list(ordered):  # sibling line models for join completeness
            for sib in FAMILY_MODELS.get(m, []):
                add(sib)

        result = ordered[:limit] if ordered else schema.auto_model_names()[:limit]
        _logger.debug("[cyllo_ai] candidate models (%d) for %r: %s",
                      len(result), (user_query or '')[:60], result)
        return result

    # -------------------------------------------------------------------------
    # Typed CRUD execution (security hardening, Tier B)
    #
    # A write is a typed operation — {model, action, values{}, filters[]} — not
    # an LLM-authored code string. It is executed directly via the ORM as the
    # requesting user (ir.rules/ACL apply). Field names, operators and relations
    # are validated/resolved against the LIVE registry, so the planner's hints
    # are never trusted. Writes pass the confirmation gate and are recorded to
    # the cyllo.ai.audit log.
    # -------------------------------------------------------------------------
    _ALLOWED_DOMAIN_OPERATORS = frozenset({
        '=', '!=', '>', '>=', '<', '<=', 'like', 'not like', 'ilike',
        'not ilike', '=like', '=ilike', 'in', 'not in', 'child_of', 'parent_of',
    })

    def _plan_resolve_m2o(self, comodel, value):
        """Resolve a many2one value to an id using the field's real comodel.

        Ids pass through; a name (string) is resolved via ``name_search`` on the
        related model. Empty values clear the field.
        """
        if value in (None, False, ""):
            return False
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            if comodel not in self.env:
                raise ValueError(f"unknown related model '{comodel}'")
            hits = self.env[comodel].name_search(value, limit=1)
            if not hits:
                raise ValueError(f"no '{comodel}' record matching {value!r}")
            return hits[0][0]
        return value

    def _plan_x2many_commands(self, comodel, value):
        """Convert an x2many value into ORM Command tuples.

        Accepts a single line object, a list of line objects (each a
        ``{field: value}`` map → new lines), a list of ids (replace the set),
        or already well-formed command tuples.
        """
        if comodel not in self.env:
            raise ValueError(f"unknown related model '{comodel}'")
        if value in (None, False):
            return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError(
                f"x2many value must be a list of line objects, got "
                f"{type(value).__name__}")
        items = list(value)
        if not items:
            return []
        # Already command tuples, e.g. (0, 0, {...}) / (6, 0, [...]).
        if all(isinstance(v, (list, tuple)) and len(v) == 3
               and isinstance(v[0], int) for v in items):
            return [tuple(v) for v in items]
        # A list of ids → replace the whole set.
        if all(isinstance(v, int) for v in items):
            return [(6, 0, list(items))]
        # A list of line objects → create each.
        if all(isinstance(v, dict) for v in items):
            return [(0, 0, self._plan_build_values(comodel, obj)) for obj in items]
        raise ValueError("unrecognized x2many line format")

    def _plan_build_values(self, model_name, values_obj):
        """Build a validated ORM values dict from a ``{field: value}`` object.

        Each field is resolved by its actual type on ``model_name``: many2one
        names → ids, x2many lists → Command tuples, scalars pass through. An
        unknown field raises (the model receives a corrective error).
        """
        if not isinstance(values_obj, dict):
            raise ValueError("values must be an object of field -> value")
        fields_meta = self.env[model_name]._fields
        out = {}
        for field, raw in values_obj.items():
            fmeta = fields_meta.get(field)
            if fmeta is None:
                raise ValueError(f"unknown field '{field}' on {model_name}")
            if fmeta.type in ('one2many', 'many2many'):
                out[field] = self._plan_x2many_commands(fmeta.comodel_name, raw)
            elif fmeta.type == 'many2one':
                out[field] = self._plan_resolve_m2o(fmeta.comodel_name, raw)
            else:
                out[field] = raw
        return out

    def _plan_build_domain(self, filters):
        """Build and validate a search domain.

        Accepts each condition as a ``[field, op, value]`` triple or a
        ``{"field","operator","value"}`` object (the planner uses both).
        """
        domain = []
        for f in (filters or []):
            if isinstance(f, dict):
                field = f.get("field")
                operator = f.get("operator") or f.get("op") or "="
                value = f.get("value")
            elif isinstance(f, (list, tuple)) and len(f) == 3:
                field, operator, value = f
            else:
                raise ValueError(f"invalid filter {f!r}")
            if not field:
                raise ValueError(f"filter is missing a field: {f!r}")
            if operator not in self._ALLOWED_DOMAIN_OPERATORS:
                raise ValueError(f"disallowed operator '{operator}'")
            domain.append((field, operator, value))
        return domain

    def _describe_operation(self, op):
        """Build a human preview for a write op; also validates fields early
        (raises on an unknown field/operator before the user is asked)."""
        action, model_name = op["action"], op["model"]
        desc = self.env[model_name]._description or model_name
        lines = ["**Review this operation before it runs:**\n",
                 f"**Action:** {action} — {desc} ({model_name})"]
        domain = self._plan_build_domain(op.get("filters"))
        if domain:
            match_desc = ", ".join(f"{f[0]} {f[1]} {f[2]!r}" for f in domain)
            # Bare filters (e.g. "id = '7'") don't tell the user WHICH record
            # that is — resolve to display names so they can sanity-check the
            # match before approving, not just the raw id.
            try:
                records = self.env[model_name].search(domain, limit=6)
            except Exception:
                records = self.env[model_name]
            if records:
                names = ", ".join(records.mapped('display_name'))
                if len(records) == 6:
                    names += ", …"
                match_desc += f" → {names}"
            lines.append("**Match:** " + match_desc)
        values = op.get("values") or {}
        if values:
            self._plan_build_values(model_name, values)  # validate
            lines.append("**Values:** " + ", ".join(
                f"{k} = {v!r}" for k, v in values.items()))
        lines.append("\nReply **proceed** to apply, or tell me what to change.")
        return "\n".join(lines)

    def _execute_plan(self, plan):
        """Execute a typed CRUD operation directly via the ORM (no eval).

        Runs as the requesting user, so ir.rules/ACL apply. Validates the model,
        fields and operators, resolves relational values, performs the action,
        and audits successful writes. Returns a result/error summary.
        """
        if not isinstance(plan, dict):
            return {"error": "Invalid operation."}
        action = plan.get("action")
        model_name = plan.get("model")
        if action not in ("create", "read", "update", "delete"):
            return {"error": f"Unsupported action: {action!r}."}
        if not model_name or model_name not in self.env:
            return {"error": f"Unknown model: {model_name!r}."}
        try:
            Model = self.env[model_name]
            values = self._plan_build_values(model_name, plan.get("values") or {})
            domain = self._plan_build_domain(plan.get("filters"))

            if action == "create":
                rec = Model.create(values)
                self._audit_action("create", model_name, values, rec)
                return {"message": "✅ Record created.", "model": model_name,
                        "id": rec.id, "name": rec.display_name}
            if action == "read":
                recs = Model.search(domain)
                # Bounded for now; full cap-and-spill is a later phase.
                return {"message": f"✅ Found {len(recs)} record(s).",
                        "result": recs[:50].read()}
            if action == "update":
                recs = Model.search(domain)
                if not recs:
                    return {"message": "No matching records to update."}
                recs.write(values)
                self._audit_action("update", model_name, values, recs)
                return {"message": f"✅ Updated {len(recs)} record(s).",
                        "model": model_name, "ids": recs.ids}
            if action == "delete":
                recs = Model.search(domain)
                if not recs:
                    return {"message": "No matching records to delete."}
                ids, count = recs.ids, len(recs)
                recs.unlink()
                self._audit_action("delete", model_name, {}, record_ids=ids)
                return {"message": f"✅ Deleted {count} record(s)."}
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] operation failed: %s | op=%r", e, plan)
            return {"error": f"❌ Operation failed: {e}"}

    def _audit_action(self, action, model_name, values, records=None, record_ids=None):
        """Record a successful write to cyllo.ai.audit (best-effort).

        Written with sudo so logging never depends on the user's rights on the
        audit model itself; the records being acted on were already access-
        checked by running the operation as the user.
        """
        try:
            ids = (list(record_ids) if record_ids is not None
                   else (records.ids if records is not None else []))
            self.env['cyllo.ai.audit'].sudo().create({
                'user_id': self.env.user.id,
                'model_name': model_name,
                'action': action,
                'record_ids': json.dumps(ids),
                'values': json.dumps(values, default=str)[:4000],
            })
        except Exception:
            _logger.exception("[cyllo_ai] audit log write failed")

    def _get_fields_for_models(self, models, crud=False):
        """Retrieve field names for a list of Cyllo model names (cached)."""
        return self._schema().fields_for_models(models, crud)

    def _is_translatable_field(self, model_field: str):
        """Checks if a field is translatable using Cyllo metadata."""
        try:
            model, field = model_field.split('.')
            model_name = self._get_model_from_table(model)[0]
            return self.env[model_name]._fields[field].translate
        except Exception as e:
            _logger.debug(
                'Failed to check if field %s is translatable: %s', model_field, str(e), exc_info=True
            )
        return False

    def _normalize_main_table(self, main_table_info: Any) -> Dict[str, str]:
        """Accept a string or dict and return {"name": <table>, "alias": <alias>}."""
        if isinstance(main_table_info, str):
            return {"name": main_table_info, "alias": main_table_info}
        name = (main_table_info.get("name") or main_table_info.get("table") or main_table_info.get("alias"))
        alias = (main_table_info.get("alias") or main_table_info.get("name") or main_table_info.get("table"))
        if not name or not alias:
            raise ValueError("Invalid main_table format. Expected string or dict with name/alias.")
        return {"name": name, "alias": alias}

    # -------------------------------------------------------------------------
    # SQL / ORM query builders
    # -------------------------------------------------------------------------

    @classmethod
    def _guard_llm_sql(cls, node, path="query"):
        """Reject statement separators / comment markers anywhere in the
        LLM-authored query plan.

        Every string in the plan ends up interpolated into the single SELECT
        we build (select list, where clause, joins, group/order), so ``;``,
        ``--`` and ``/*`` must never appear — they would allow a second
        statement or comment out the safety clauses appended after the
        fragment. Parameter values (SQL_PARAM_KEYS) are exempt: they go to
        the driver separately and are safe by parametrization.
        """
        if isinstance(node, dict):
            for k, v in node.items():
                if k in SQL_PARAM_KEYS:
                    continue
                cls._guard_llm_sql(v, f"{path}.{k}")
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                cls._guard_llm_sql(v, f"{path}[{i}]")
        elif isinstance(node, str):
            for marker in SQL_BANNED_MARKERS:
                if marker in node:
                    raise ValueError(
                        f"unsafe SQL fragment in {path}: {marker!r} is not allowed")

    def _execute_analytic_sql(self, sql, params):
        """Run analytics SQL on a dedicated READ ONLY sandbox cursor.

        The LLM-generated query never touches the request's main transaction:
        a fresh cursor is opened, its transaction is set READ ONLY (writes are
        rejected by Postgres itself, whatever the SQL says) with a statement
        timeout, and it is closed after fetching. A failed query therefore
        can't poison the main transaction either. Caveat: a separate
        transaction cannot see this request's uncommitted writes — acceptable
        for analytics reads.

        Returns ``(rows, column_names)``.
        """
        with self.env.registry.cursor() as cr:
            # Ensure a fresh transaction: SET TRANSACTION READ ONLY is only
            # valid before any other statement in the transaction.
            cr.rollback()
            cr.execute("SET TRANSACTION READ ONLY")
            cr.execute("SET LOCAL statement_timeout = %s", (ANALYTIC_TIMEOUT_MS,))
            cr.execute(sql, params)
            rows = cr.fetchall()
            column_names = [d[0] for d in cr.description]
        return rows, column_names

    def _get_query_object(self, sql_query):
        """Build a CylloQuery SQL object from a structured SQL query dictionary."""
        self._guard_llm_sql(sql_query)
        main_table = self._normalize_main_table(sql_query.get("main_table"))
        query = CylloQuery(
            self.env.cr,
            self._get_table_from_model(main_table["alias"])[0],
            self._get_table_from_model(main_table["name"])[0]
        )

        for join in sql_query.get("joins", []):
            lhs_table = self._get_table_from_model(join['lhs_alias'])[0]
            lhs_column = self._get_table_from_model(join['lhs_column'])[0]
            rhs_table = self._get_table_from_model(join['rhs_alias'])[0]
            rhs_column = self._get_table_from_model(join['rhs_column'])[0]
            join_condition = SQL(f"{lhs_table}.{lhs_column} = {rhs_table}.{rhs_column}")
            query.add_join(
                join["type"], rhs_table,
                self._get_table_from_model(join['rhs_table'])[0], join_condition
            )

        where = sql_query.get("where")
        if isinstance(where, dict):
            where_clause = (where.get("where_clause") or "").strip()
            where_params = where.get("where_params", [])
        elif isinstance(where, str):
            where_clause = where.strip()
            where_params = sql_query.get("where_params", []) if isinstance(
                sql_query.get("where_params"), list) else []
        else:
            where_clause, where_params = "", []

        extract_map = {
            "YEAR": lambda d: datetime.fromisoformat(d).year,
            "MONTH": lambda d: datetime.fromisoformat(d).month,
            "DAY": lambda d: datetime.fromisoformat(d).day,
        }
        for extract_part, extract_func in extract_map.items():
            extract_pattern = f"EXTRACT({extract_part} FROM %s)"
            if extract_pattern in where_clause:
                where_clause = where_clause.replace(extract_pattern, "%s")
                where_params = [
                    extract_func(p) if isinstance(p, str) and "-" in p else p
                    for p in where_params
                ]

        if isinstance(where_params, list) and "IN %s" in where_clause:
            where_params = [
                tuple(p) if isinstance(p, list) else p for p in where_params
            ]

        if "BETWEEN %s AND %s" in where_clause:
            where_params = [
                datetime.fromisoformat(p).date() if isinstance(p, str) and "-" in p else p
                for p in where_params
            ]

        if where_clause:
            pattern = re.compile(r'(\w+\.\w+)\s+(ILIKE|=|!=|LIKE|NOT ILIKE|NOT LIKE)', re.IGNORECASE)
            matches = pattern.findall(where_clause)
            for field, operator in matches:
                if "->>" not in field and self._is_translatable_field(field):
                    where_clause = where_clause.replace(field, f"{field}->>'en_US'")

            placeholder_count = where_clause.count("%s")
            if isinstance(where_params, list):
                if placeholder_count == 0:
                    where_params = []
                elif len(where_params) > placeholder_count:
                    where_params = where_params[:placeholder_count]
                elif len(where_params) < placeholder_count:
                    where_params += [None] * (placeholder_count - len(where_params))
            query.add_where(where_clause, where_params)

        if sql_query.get("group_by"):
            query.group_by = sql_query["group_by"]
        if sql_query.get("order_by"):
            query.order = sql_query["order_by"]
        # Row cap is always enforced: the plan's limit is honored up to
        # ANALYTIC_MAX_LIMIT; a missing/invalid limit gets the default.
        try:
            limit = int(sql_query.get("limit") or ANALYTIC_DEFAULT_LIMIT)
        except (TypeError, ValueError):
            limit = ANALYTIC_DEFAULT_LIMIT
        query.limit = max(1, min(limit, ANALYTIC_MAX_LIMIT))

        return query

    # -------------------------------------------------------------------------
    # Tool implementations
    # -------------------------------------------------------------------------

    @staticmethod
    def _unwrap_translation(value):
        """Unwrap a translatable (JSONB) value ``{"en_US": ...}`` to plain text;
        pass everything else through unchanged."""
        if isinstance(value, dict):
            return value.get('en_US') or next(iter(value.values()), None)
        return value

    @staticmethod
    def _key_for_select(field, fallback):
        """Derive a result key for one SELECT expression: an ``AS`` label wins;
        else ``table.column`` becomes ``table_column`` (unambiguous across
        joins); else the raw cursor column name."""
        m = re.search(r'\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\s*$', field or '',
                      re.IGNORECASE)
        if m:
            return m.group(1)
        plain = re.fullmatch(
            r'\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*', field or '')
        if plain:
            return f"{plain.group(1)}_{plain.group(2)}"
        return fallback

    def _build_result_keys(self, select_fields, column_names):
        """Unique result keys aligned position-for-position with the SELECT,
        so no two columns collide (duplicates get a numeric suffix)."""
        keys, counts = [], {}
        for i, col in enumerate(column_names):
            field = select_fields[i] if i < len(select_fields) else col
            key = self._key_for_select(field, col)
            counts[key] = counts.get(key, 0) + 1
            keys.append(key if counts[key] == 1 else f"{key}_{counts[key]}")
        return keys

    def _check_field_access(self, idents, schema):
        """Enforce field-level (column) access on the raw-SQL read path.

        Raw SQL bypasses Odoo's field security, so it is re-applied here as the
        requesting user: a hard denylist for credential fields Odoo masks
        specially (they carry no field ``groups``), plus each field's own
        ``groups`` restriction — the same check the ORM performs. Raises
        ``AccessError`` (terminal — a retry cannot grant access) on the first
        referenced column the user may not read.

        ``idents`` are the ``(table, column)`` pairs referenced across
        SELECT / WHERE / GROUP / ORDER (from ``validate_plan``); WHERE is
        included because filtering on a restricted field also leaks it.
        """
        checked = set()
        for alias, column in idents or []:
            if (alias, column) in checked:
                continue
            checked.add((alias, column))
            if column in SENSITIVE_COLUMNS:
                raise AccessError(
                    f"Field '{column}' is not accessible via analytics.")
            model = schema.model_from_table(alias)
            if model not in self.env:
                continue
            field = self.env[model]._fields.get(column)
            # Mirror the ORM's own field-group check (models.py: field.groups
            # and not self.env.su and not self.user_has_groups(field.groups)).
            if field is not None and field.groups and not self.env.su \
                    and not self.user_has_groups(field.groups):
                raise AccessError(
                    f"You do not have access to the field '{column}' on {model}.")

    def analytic_record(self, user_query: str, company_ids: list) -> str:
        """Execute an analytic SQL query based on the user question.

        The LLM only ever produces a structured query PLAN (JSON) — never raw
        SQL. Each attempt runs the plan through the same guarded pipeline:
        marker scan (_guard_llm_sql), build, ir.rules, then execution on a
        READ ONLY sandbox cursor with a statement timeout and hard row cap.
        A failed attempt feeds the error back and the LLM regenerates the
        PLAN; there is deliberately no raw-SQL correction path, as it would
        bypass every guard.
        """
        try:
            # Deterministic candidate selection — no extra LLM round-trip.
            model_list = self._candidate_models(user_query)
            fields_info = self._get_fields_for_models(model_list)
            tables = self._get_table_from_model(model_list)

            base_prompt = f"""
You are generating a SQL query PLAN (structured JSON) based on the following inputs:

- User Query: "{user_query}"
- Available Tables: {tables}
- Fields to Retrieve (by model): {fields_info}
- System Time: {Date.today()}

The plan is validated against a strict safe subset before it runs. Anything
outside the rules below is REJECTED — follow them exactly.

Identifiers:
- Reference columns ONLY as table_column pairs written table.column, using the
  underscored physical table names from "Available Tables" (e.g. sale_order.amount_total).
  NEVER use dotted model names (not "sale.order") and NEVER dotted paths
  (not partner_id.name — join instead).
- main_table name and alias must both be the underscored table name (alias = table name).
- Always include the id field of each selected table.
- Prefer product_template.name over product_product.name, res_partner.name over res_users.name.

WHERE (where_clause): a boolean expression over ONLY these shapes —
- comparisons: table.column OP %s, where OP is one of = != <> < <= > >= LIKE ILIKE
- table.column NOT LIKE %s, table.column IN %s, table.column BETWEEN %s AND %s,
  table.column IS NULL, table.column IS NOT NULL
- combine with AND / OR / NOT and parentheses.
- EVERY value is a %s placeholder passed in where_params — NEVER write a literal
  string ('x') or number (5) in the clause. The right side of a comparison is
  ALWAYS %s (never another column).
- NO subqueries (no SELECT inside), NO arithmetic, NO casts (::), NO EXTRACT.
  For dates use a range: date_col >= %s AND date_col < %s (compute the bounds and
  pass them in where_params).
- Only these functions may wrap a column here: LOWER, UPPER, COALESCE, DATE_TRUNC.

SELECT (list of strings): each item is table.column, an aggregate
SUM/COUNT/AVG/MIN/MAX(...) (including COUNT(*) and COUNT(DISTINCT table.column)),
a scalar LOWER/UPPER/COALESCE/DATE_TRUNC(...), or arithmetic between columns and
numbers (table.qty * table.price), each optionally followed by "AS label".
For time buckets use DATE_TRUNC('month', table.date_col) (a quoted granularity
literal is allowed ONLY as a function argument).

GROUP BY / ORDER BY (strings, comma-separated): table.column terms or a SELECT
"AS" label by name (GROUP BY may also use the scalar functions; ORDER BY may also
use aggregates and a trailing ASC/DESC).

Correct measures (avoid double counting):
- To total money at the ORDER level, aggregate sale_order.amount_total joined
  only to sale_order (no line join).
- To total money by a LINE-level attribute (product, category), aggregate the
  LINE amount sale_order_line.price_subtotal / price_total — NEVER
  sale_order.amount_total across a line join (it counts the order total once per
  line and inflates the result).

General:
- Valid JSON only (RFC 8259); use JSON lists, never tuples.
- Join types must be "JOIN" or "LEFT JOIN"; join only when needed.
- HAVING is not available: to filter by an aggregate, order by it and present
  the qualifying rows.
- Comparison values go in %s / where_params; do not put a bare literal on the
  right of a WHERE comparison. Never include SQL comments (--, /*) or semicolons.

Output Format (as JSON):
- main_table: {{name, alias}} (both the underscored table name)
- select: list of strings
- joins: list of {{type, lhs_alias, lhs_column, rhs_table, rhs_column, rhs_alias}}
- where: {{where_clause (str), where_params (list)}}
- group_by: str or null
- order_by: str or null
- limit: int or null

Output JSON only — no explanations or text outside the structure.
"""
            failure = None
            for attempt in range(ANALYTIC_ATTEMPTS):
                prompt = base_prompt if failure is None else (
                    base_prompt
                    + f"\nYour previous attempt failed:\n{failure}\n\n"
                      "Generate a corrected query that resolves this error, in "
                      "EXACTLY the same JSON structure specified above. "
                      "Output JSON only.\n")
                sql_response = self._call_llm(prompt)
                sql_query_str = re.sub(r"```(?:json|python)?", "", sql_response).replace("`", "").strip()
                sql = params = None
                try:
                    sql_query = json.loads(sql_query_str)
                    # Allowlist-validate every LLM-authored fragment and derive
                    # the set of tables the query may touch — NEVER trusting the
                    # plan's self-reported "tables". A guard rejection
                    # (SqlGuardError, a ValueError) is caught below and fed back
                    # for a structured retry.
                    schema = self._schema()
                    validated = validate_plan(sql_query, schema.columns_for)
                    # Field-level (column) access — raw SQL bypasses Odoo's
                    # field security, so re-apply it as the user. An AccessError
                    # here is terminal (not caught below): a retry can't grant
                    # access, so the turn ends with the denial.
                    self._check_field_access(validated.idents, schema)
                    query = self._get_query_object(sql_query)
                    # Enforce ACL + record rules on the DERIVED table set: every
                    # referenced business model must be readable by this user
                    # (check_access_rights), and its record rules are applied to
                    # the query (_apply_ir_rules). An access denial raises
                    # AccessError, which is intentionally NOT caught here — a
                    # retry cannot grant access, so the turn ends with the error.
                    # Relation tables with no model carry no rules and are skipped.
                    env_scoped = self.env(context=dict(
                        self.env.context, allowed_company_ids=company_ids))
                    for table in validated.tables:
                        model = schema.model_from_table(table)
                        if model not in env_scoped:
                            _logger.debug("[cyllo_ai] analytic: table %r has no "
                                          "model; skipping ACL", table)
                            continue
                        model_obj = env_scoped[model]
                        model_obj.check_access_rights("read")
                        model_obj._apply_ir_rules(query, "read")
                        model_obj._flush_search([])

                    select_fields = sql_query.get("select") or []
                    sql, params = query.select(*[SQL(f) for f in select_fields])
                    rows, column_names = self._execute_analytic_sql(sql, params)
                except (psycopg2.Error, ValueError, KeyError, TypeError, IndexError) as e:
                    failure = (f"SQL:\n{sql}\n\nError:\n{e}"
                               if sql is not None else str(e))
                    _logger.info("[cyllo_ai] analytic attempt %d/%d failed: %s",
                                 attempt + 1, ANALYTIC_ATTEMPTS, str(e)[:200])
                    continue

                # Unique, informative keys aligned to the SELECT so joined
                # columns that share a name (e.g. two `id`/`name` columns) do
                # not collide and silently overwrite each other. Translatable
                # (JSONB) values are unwrapped from {"en_US": ...} to plain text.
                keys = self._build_result_keys(select_fields, column_names)
                result = [
                    {k: self._unwrap_translation(v) for k, v in zip(keys, row)}
                    for row in rows
                ]
                # Map each SELECT expression to its result key by position.
                field_key = ({f: keys[i] for i, f in enumerate(select_fields)}
                             if len(keys) == len(select_fields) else {})

                entities = []
                id_fields = [f for f in select_fields if f.endswith(".id")]
                for id_field in id_fields:
                    table_name = id_field.split(".", 1)[0]
                    model_name = self._get_model_from_table(table_name)[0]
                    name_field = next(
                        (f for f in select_fields if f.startswith(f"{table_name}.") and
                         (f.endswith(".name") or f.endswith(".display_name"))),
                        None
                    )
                    id_key = field_key.get(id_field)
                    if not id_key:
                        continue
                    name_key = field_key.get(name_field) if name_field else None
                    for row in result:
                        record_id = row.get(id_key)
                        text = row.get(name_key) if name_key else None
                        if isinstance(text, str) and text.strip():
                            entities.append({"text": text, "record_id": record_id,
                                             "model": model_name})

                return json.dumps({"result": result, "entities": entities}, default=str)

            return f"⚠️ Error in analytic_record: {failure}"

        except Exception as e:
            return f"⚠️ Error in analytic_record: {str(e)}"

    def write_records(self, model, action, values=None, filters=None):
        """Single typed entry point for create/read/update/delete.

        The agent calls this directly with typed args (no separate planning LLM
        call). Reads run immediately; writes are validated, previewed, and paused
        for confirmation — the typed op is stored server-side and executed
        verbatim on confirm, so it cannot be altered in transit.
        """
        op = {"model": model, "action": action,
              "values": values or {}, "filters": filters or []}
        if action not in ("create", "read", "update", "delete"):
            return {"error": f"Unsupported action: {action!r}."}
        if not model or model not in self.env:
            return {"error": f"Unknown model: {model!r}."}
        if action == "read":
            return self._execute_plan(op)
        # Write: validate + preview, then pause for confirmation.
        try:
            preview = self._describe_operation(op)
        except Exception as e:
            return {"error": f"❌ {e}"}
        _logger.info("[cyllo_ai] write pending confirm: %s %s", action, model)
        return {"__interrupt__": True, "message": preview,
                "pending_query": json.dumps(op)}

    def execute_confirmed_crud(self, query):
        """Execute a user-confirmed write operation (stored typed op)."""
        if isinstance(query, dict):
            op = query
        else:
            try:
                op = json.loads(query)
            except (TypeError, ValueError):
                return {"error": "Invalid operation payload."}
        if not isinstance(op, dict):
            return {"error": "Invalid operation payload."}
        return self._execute_plan(op)

    def get_url(self, text: str, record_id: str, model: str) -> str:
        """Generate a Cyllo record URL from a record ID and model name."""
        return (
            f'/web#id={record_id}'
            f'&model={self._get_model_from_table(model)[0]}&view_type=form'
        )

    def currency_conversion(self, amount: float, from_currency_name: str, to_currency_name: str) -> dict:
        """Convert an amount between currencies using configured exchange rates."""
        Currency = self.env['res.currency']
        from_currency = Currency.search([("name", "=", from_currency_name)], limit=1)
        to_currency = Currency.search([("name", "=", to_currency_name)], limit=1)

        if not from_currency.active:
            return {"error": f"Currency '{from_currency_name}' is inactive."}
        if not to_currency.active:
            return {"error": f"Currency '{to_currency_name}' is inactive."}

        converted_amount = from_currency._convert(amount, to_currency, self.env.company)
        return {"amount": converted_amount, "from": from_currency_name, "to": to_currency_name}

    def get_currency_name(self, currency_id: int) -> dict:
        """Return the currency name for a given currency ID."""
        currency = self.env['res.currency'].search([('id', '=', currency_id)], limit=1)
        if not currency.active:
            return {"error": f"Currency with id '{currency_id}' is inactive."}
        return {'name': currency.name}

    # -------------------------------------------------------------------------
    # ORM tier tools (hybrid querying — tier 1 retrieval, tier 2 aggregation)
    #
    # These run as the user (no sudo), so ir.rules and field ACLs are enforced
    # by the ORM itself. All inputs are validated against the SchemaIndex
    # BEFORE execution; validation failures return corrective, "did you mean"
    # style errors so the agent self-corrects in one loop step.
    # -------------------------------------------------------------------------

    def _company_env(self, company_ids):
        """Environment scoped to the requesting user's allowed companies."""
        if company_ids:
            return self.env(context=dict(self.env.context, allowed_company_ids=company_ids))
        return self.env

    def _check_model_and_domain(self, schema, model, domain):
        """Return a corrective error string, or None if model + domain are valid."""
        if not schema.has_model(model):
            return schema.describe_model(model).get('error', f"Unknown model '{model}'.")
        if not schema.is_searchable(model):
            return (f"'{model}' is a transient wizard model, not business data. "
                    f"Query a regular business model instead — or, for accounting "
                    f"reports, use the accounting_report tool.")
        errors = schema.validate_domain(model, domain or [])
        return "; ".join(errors) if errors else None

    def _default_fields(self, schema, model, max_fields=6):
        """
        Informative default columns when the caller omits ``fields`` — so a
        bare search still yields a useful table (name, partner, date, amount,
        state) instead of display_name only. Deterministic, schema-derived.
        """
        metas = schema.model_fields(model)
        chosen = []

        def take(*names):
            for n in names:
                if n in metas and n not in chosen:
                    chosen.append(n)
                    return True
            return False

        take('name', 'display_name', 'x_name')
        take('partner_id')
        # a business date column
        if not take('date_order', 'date', 'invoice_date', 'date_start', 'scheduled_date'):
            for n in sorted(metas):
                m = metas[n]
                if m['type'] in ('date', 'datetime') and m['business']:
                    chosen.append(n)
                    break
        # a money column
        if not take('amount_total', 'amount_untaxed', 'price_total', 'price_subtotal'):
            for n in sorted(metas):
                m = metas[n]
                if m['aggregatable'] and m['type'] == 'monetary':
                    chosen.append(n)
                    break
        take('state')
        take('user_id')
        return chosen[:max_fields] or ['display_name']

    def search_records(self, model, domain=None, fields=None, limit=None,
                       order=None, company_ids=None):
        """Tier-1 retrieval via ORM ``search_read``."""
        schema = self._schema()
        domain = domain or []
        err = self._check_model_and_domain(schema, model, domain)
        if not err and fields:
            errs = schema.validate_fields(model, fields)
            err = "; ".join(errs) if errs else None
        if not err and order:
            order_fields = [p.strip().split()[0] for p in order.split(',') if p.strip()]
            errs = schema.validate_fields(model, order_fields)
            err = "; ".join(errs) if errs else None
        if err:
            return {"error": err}

        try:
            limit = max(1, min(int(limit or ORM_DEFAULT_LIMIT), ORM_MAX_LIMIT))
        except (TypeError, ValueError):
            limit = ORM_DEFAULT_LIMIT

        try:
            env = self._company_env(company_ids)
            records = env[model].search_read(
                domain, fields or self._default_fields(schema, model),
                limit=limit, order=order or None)
            total = env[model].search_count(domain)
            return json.loads(json.dumps({
                "model": model,
                "total_count": total,
                "returned": len(records),
                "records": records,
            }, default=str))
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] search_records failed model=%s: %s", model, e)
            return {"error": f"search_records failed: {e}"}

    def count_records(self, model, domain=None, company_ids=None):
        """Count records matching a domain via ORM ``search_count``."""
        schema = self._schema()
        err = self._check_model_and_domain(schema, model, domain or [])
        if err:
            return {"error": err}
        try:
            count = self._company_env(company_ids)[model].search_count(domain or [])
            return {"model": model, "count": count}
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] count_records failed model=%s: %s", model, e)
            return {"error": f"count_records failed: {e}"}

    def aggregate_records(self, model, domain=None, groupby=None, aggregates=None,
                          company_ids=None):
        """Tier-2 grouped aggregation via ORM ``read_group``."""
        schema = self._schema()
        domain = domain or []
        groupby = [groupby] if isinstance(groupby, str) else list(groupby or [])
        aggregates = [aggregates] if isinstance(aggregates, str) else list(aggregates or [])

        err = self._check_model_and_domain(schema, model, domain)
        if err:
            return {"error": err}

        errors = []
        for g in groupby:
            base, _, gran = g.partition(':')
            meta = schema.field_meta(model, base)
            if meta is None:
                sugg = schema.suggest_fields(model, base)
                errors.append(f"Unknown groupby field '{base}' on {model} "
                              f"(dotted paths are not supported in groupby)."
                              + (f" Did you mean: {', '.join(sugg)}?" if sugg else ""))
            elif gran and meta['type'] not in ('date', 'datetime'):
                errors.append(f"Granularity ':{gran}' requires a date/datetime field; "
                              f"'{base}' is {meta['type']}.")
            elif gran and gran not in GROUP_GRANULARITIES:
                errors.append(f"Unknown granularity ':{gran}'. "
                              f"Use one of: {', '.join(sorted(GROUP_GRANULARITIES))}.")
            elif not meta['groupable']:
                errors.append(f"Field '{base}' ({meta['type']}) is not groupable. "
                              f"Groupable fields on {model}: "
                              f"{', '.join(schema.groupable_fields(model)[:20])}")

        agg_fields = []
        for a in aggregates:
            fname, _, op = a.partition(':')
            op = op or 'sum'
            meta = schema.field_meta(model, fname)
            if op not in AGG_OPERATORS:
                errors.append(f"Unknown aggregate operator ':{op}'. "
                              f"Use one of: {', '.join(sorted(AGG_OPERATORS))}.")
            elif meta is None:
                sugg = schema.suggest_fields(model, fname)
                errors.append(f"Unknown aggregate field '{fname}' on {model}."
                              + (f" Did you mean: {', '.join(sugg)}?" if sugg else ""))
            elif op != 'count' and not meta['aggregatable']:
                errors.append(f"Field '{fname}' ({meta['type']}) is not numeric. "
                              f"Aggregatable fields on {model}: "
                              f"{', '.join(schema.aggregatable_fields(model))}")
            else:
                agg_fields.append(f"{fname}:{op}")

        if errors:
            return {"error": "; ".join(errors)}
        if not groupby and not agg_fields:
            return {"error": "Provide at least one of groupby or aggregates."}

        try:
            env = self._company_env(company_ids)
            groups = env[model].read_group(domain, agg_fields, groupby, lazy=False)
            cleaned = []
            for g in groups[:ORM_MAX_LIMIT]:
                g.pop('__domain', None)
                g.pop('__range', None)
                cleaned.append(g)
            out = {"model": model, "group_count": len(groups), "groups": cleaned}
            if len(groups) > ORM_MAX_LIMIT:
                out["note"] = f"Showing first {ORM_MAX_LIMIT} of {len(groups)} groups."
            return json.loads(json.dumps(out, default=str))
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] aggregate_records failed model=%s: %s", model, e)
            return {"error": f"aggregate_records failed: {e}"}

    def get_model_fields(self, model):
        """Describe a model: fields, types, relations, groupable/aggregatable."""
        return self._schema().describe_model(model)

    # -------------------------------------------------------------------------
    # Functional introspection — "how do I / where is" answers are read from
    # the ERP itself (menus, settings, schema), never from model memory: a
    # path returned by find_menu exists in THIS install by construction.
    # All reads run as the user — group-hidden menus stay hidden.
    # -------------------------------------------------------------------------

    @staticmethod
    def _query_tokens(query):
        return [t for t in re.split(r"[^\w]+", (query or "").lower()) if len(t) >= 2]

    def find_menu(self, query, limit=10):
        """Search menus visible to the user by full path; paths + action links.

        ``complete_name`` is a non-stored computed field, so matching happens
        in Python over the visible set (small: a few hundred rows, and
        ``_visible_menu_ids`` is ormcached per group set).
        """
        tokens = self._query_tokens(query)
        if not tokens:
            return {"error": "query is required, e.g. 'tax configuration'."}
        Menu = self.env['ir.ui.menu']
        menus = Menu.browse(sorted(Menu._visible_menu_ids()))
        scored = []
        for menu in menus:
            path = menu.complete_name or menu.name or ""
            hay = path.lower()
            score = sum(1 for t in tokens if t in hay)
            if score:
                scored.append((score, bool(menu.action), path, menu))
        if not scored:
            return {"query": query, "menus": [],
                    "message": "No matching menu found — the feature may be "
                               "named differently or not installed."}
        # prefer: all tokens matched > clickable (has an action) > shorter path
        full = [s for s in scored if s[0] == len(tokens)]
        pool = full or scored
        pool.sort(key=lambda s: (-s[0], not s[1], len(s[2])))
        results = []
        for score, has_action, path, menu in pool[:limit]:
            item = {"path": path.replace("/", " / ")}
            if has_action and menu.action:
                item["action_id"] = menu.action.id
                item["link"] = f"/web#action={menu.action.id}"
            results.append(item)
        return {"query": query, "menus": results}

    def find_setting(self, query, limit=10):
        """Search res.config.settings field labels/help — the Settings screen
        itself.

        Uses ``fields_get()`` (registry metadata), NOT ``ir.model.fields``:
        that table is readable only by admins, while fields_get works for any
        user and applies field-level group visibility on top.
        """
        tokens = self._query_tokens(query)
        if not tokens:
            return {"error": "query is required, e.g. 'multi currency'."}
        try:
            fields_meta = self.env['res.config.settings'].fields_get(
                attributes=['string', 'help'])
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] find_setting failed: %s", e)
            return {"error": f"find_setting failed: {e}"}

        def kind(name):
            if name.startswith("module_"):
                return "app/module toggle"
            if name.startswith("group_"):
                return "feature toggle"
            if name.startswith("default_"):
                return "default value"
            return "setting"

        scored = []
        for name, meta in fields_meta.items():
            label = meta.get('string') or ''
            help_ = meta.get('help') or ''
            hay_label = label.lower()
            hay = hay_label + ' ' + help_.lower()
            if sum(1 for t in tokens if t in hay) != len(tokens):
                continue  # every token must match label or help
            label_hits = sum(1 for t in tokens if t in hay_label)
            scored.append((label_hits, name, label, help_))
        # label hits before help-only hits, then alphabetical for stability
        scored.sort(key=lambda s: (-s[0], s[2]))

        results = [{
            "label": label,
            "technical_name": name,
            "kind": kind(name),
            "help": help_[:300],
        } for _hits, name, label, help_ in scored[:limit]]
        out = {"query": query, "settings": results}
        action = self.env.ref("base_setup.action_general_configuration",
                              raise_if_not_found=False)
        if action:
            out["settings_link"] = f"/web#action={action.id}"
        if not results:
            out["message"] = ("No matching setting found — the feature may be "
                              "named differently or not installed.")
        return out

    def describe_feature(self, query):
        """One-call aggregate for functionality/navigation questions:
        matching menus + settings + data models."""
        menus = self.find_menu(query, limit=8)
        settings = self.find_setting(query, limit=8)
        try:
            models_hits = self._schema().search_models(query, limit=5)
        except Exception:
            models_hits = []
        out = {
            "query": query,
            "menus": menus.get("menus", []),
            "settings": settings.get("settings", []),
            "models": models_hits,
        }
        if settings.get("settings_link"):
            out["settings_link"] = settings["settings_link"]
        if not (out["menus"] or out["settings"] or out["models"]):
            out["message"] = ("Nothing matching found in menus, settings or data "
                              "models. Tell the user the feature was not found in "
                              "this Cyllo install — do not guess an answer.")
        return out

    # -------------------------------------------------------------------------
    # Communication — send email / SMS, always preview + confirm.
    #
    # ``prepare_*`` drafts the message and pauses the turn (``__interrupt__``,
    # same sandbox as risky CRUD); on the user's confirmation the orchestrator
    # dispatches to ``execute_confirmed_*``. Everything runs as the user.
    # -------------------------------------------------------------------------

    def _outgoing_mail_server_configured(self):
        """True if an outgoing mail server is set up (Settings > Technical >
        Email > Outgoing Mail Servers). Uses Odoo's own resolver so routing by
        from-filter is respected; a falsy result means no usable record exists."""
        MailServer = self.env['ir.mail_server'].sudo()
        from_email = MailServer._get_default_from_address() or self.env.user.email_formatted
        mail_server, _ = MailServer._find_mail_server(from_email)
        return bool(mail_server)

    _NO_MAIL_SERVER_MSG = (
        "No outgoing mail server is configured, so I can't send email yet. "
        "Set one up in Settings → Technical → Email → Outgoing Mail Servers."
    )

    def _resolve_partner(self, partner_id=None, partner=None):
        """Resolve a recipient by id or name. Returns (record, error)."""
        Partner = self.env['res.partner']
        if partner_id:
            rec = Partner.browse(int(partner_id))
            if rec.exists():
                return rec, None
        if partner:
            hits = Partner.name_search(partner, limit=2)
            if hits:
                return Partner.browse(hits[0][0]), None
            return None, f"No partner found matching '{partner}'."
        return None, "Provide partner_id or partner (the recipient's name)."

    def _resolve_user(self, user_id=None, user=None):
        """Resolve an internal user (share=False) by id or name. Returns
        (record, error)."""
        Users = self.env['res.users']
        internal = [('share', '=', False)]
        if user_id:
            rec = Users.browse(int(user_id))
            if rec.exists() and not rec.share:
                return rec, None
        if user:
            hits = Users.name_search(user, args=internal, limit=2)
            if hits:
                return Users.browse(hits[0][0]), None
            return None, f"No internal user found matching '{user}'."
        return None, "Provide user_id or user (the recipient's name)."

    def prepare_email(self, message, partner_id=None, partner=None, subject=None):
        """Draft an email and pause for the user's confirmation (preview)."""
        body = (message or "").strip()
        if not body:
            return {"error": "message (the email body) is required."}
        if not self._outgoing_mail_server_configured():
            return {"error": self._NO_MAIL_SERVER_MSG}
        rec, err = self._resolve_partner(partner_id, partner)
        if err:
            return {"error": err}
        if not rec.email:
            return {"error": f"'{rec.display_name}' has no email address on file — "
                             "ask the user for an address or another recipient."}
        subject = (subject or "").strip() or f"Message from {self.env.company.name}"
        preview = (
            "**Review this email before it is sent:**\n\n"
            f"**To:** {rec.display_name} ({rec.email})\n"
            f"**Subject:** {subject}\n\n"
            "---\n\n"
            f"{body}\n\n"
            "---\n"
            "Reply **proceed** to send it, or tell me what to change."
        )
        return {
            "__interrupt__": True,
            "pending_query": json.dumps({
                "kind": "send_email", "partner_id": rec.id,
                "subject": subject, "body": body,
            }),
            "message": preview,
        }

    def execute_confirmed_email(self, query):
        """Send a user-confirmed email via the recipient's chatter (mail.thread
        notification — same path as emailing from the partner form)."""
        try:
            data = json.loads(query)
            partner = self.env['res.partner'].browse(int(data["partner_id"]))
            if not partner.exists():
                return {"error": "The recipient no longer exists."}
            partner.message_post(
                body=plaintext2html(data["body"]),
                subject=data["subject"],
                partner_ids=[partner.id],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            return {"message": f"✅ Email sent to {partner.display_name} ({partner.email})."}
        except Exception as e:
            self.env.cr.rollback()
            _logger.exception("[cyllo_ai] confirmed email send failed")
            return {"error": f"Email send failed: {e}"}

    def prepare_text_message(self, message, partner_id=None, partner=None):
        """Draft an SMS via the Cyllo SMS gateway and pause for confirmation."""
        text = (message or "").strip()
        if not text:
            return {"error": "message (the SMS text) is required."}
        if 'send.sms' not in self.env:
            return {"error": "SMS sending is not available — the SMS gateway "
                             "module is not installed."}
        gateway = self.env['sms.gateway.config'].search(
            [('is_active', '=', True)], limit=1)
        if not gateway:
            return {"error": "No active SMS gateway is configured — activate one "
                             "under the SMS Gateway settings first."}
        rec, err = self._resolve_partner(partner_id, partner)
        if err:
            return {"error": err}
        number = rec.mobile or rec.phone
        if not number:
            return {"error": f"'{rec.display_name}' has no mobile/phone number on file."}
        preview = (
            "**Review this SMS before it is sent:**\n\n"
            f"**To:** {rec.display_name} ({number})\n"
            f"**Via:** {gateway.name}\n\n"
            "---\n\n"
            f"{text}\n\n"
            "---\n"
            "Reply **proceed** to send it, or tell me what to change."
        )
        return {
            "__interrupt__": True,
            "pending_query": json.dumps({
                "kind": "send_text", "partner_id": rec.id,
                "gateway_id": gateway.id, "number": number, "text": text,
            }),
            "message": preview,
        }

    def execute_confirmed_text(self, query):
        """Send a user-confirmed SMS through the configured gateway."""
        try:
            data = json.loads(query)
            wizard = self.env['send.sms'].create({
                'sms_id': data['gateway_id'],
                'sms_to': data['number'],
                'text': data['text'],
            })
            wizard.action_send_sms()
            return {"message": f"✅ SMS sent to {data['number']}."}
        except Exception as e:
            self.env.cr.rollback()
            _logger.exception("[cyllo_ai] confirmed SMS send failed")
            return {"error": f"SMS send failed: {e}"}

    def prepare_internal_message(self, message, user_id=None, user=None):
        """Draft an internal Discuss message to a colleague and pause for the
        user's confirmation (preview). Delivered in-app via the Discuss bus —
        no outgoing mail server involved."""
        body = (message or "").strip()
        if not body:
            return {"error": "message (the message text) is required."}
        rec, err = self._resolve_user(user_id, user)
        if err:
            return {"error": err}
        if rec.id == self.env.user.id:
            return {"error": "You can't send an internal message to yourself."}
        preview = (
            "**Review this internal message before it is sent:**\n\n"
            f"**To:** {rec.name}\n\n"
            "---\n\n"
            f"{body}\n\n"
            "---\n"
            "Reply **proceed** to send it, or tell me what to change."
        )
        return {
            "__interrupt__": True,
            "pending_query": json.dumps({
                "kind": "send_internal_message", "user_id": rec.id, "body": body,
            }),
            "message": preview,
        }

    def execute_confirmed_internal_message(self, query):
        """Send a user-confirmed internal message as a Discuss direct message
        (1:1 chat channel, created or reused via channel_get)."""
        try:
            data = json.loads(query)
            user = self.env['res.users'].browse(int(data["user_id"]))
            if not user.exists():
                return {"error": "The recipient no longer exists."}
            channel = self.env['discuss.channel'].channel_get(
                [user.partner_id.id])
            channel.message_post(
                body=plaintext2html(data["body"]),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            return {"message": f"✅ Message sent to {user.name}."}
        except Exception as e:
            self.env.cr.rollback()
            _logger.exception("[cyllo_ai] confirmed internal message send failed")
            return {"error": f"Message send failed: {e}"}

    # -------------------------------------------------------------------------
    # Tier 0 — canonical financial metrics
    #
    # Defined accounting metrics (profit, revenue, assets…) are NEVER
    # re-derived by the LLM. They are computed by invoking the same engine
    # method the on-screen accounting reports call, so the chat answer is
    # identical to the official report for the same period.
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_period(period=None, start_date=None, end_date=None):
        """Resolve a named period (or explicit dates) into ISO start/end + label.

        Deterministic server-side date math — LLMs are never trusted with
        date-window arithmetic. Returns (start_iso, end_iso, label) or raises
        ValueError with a corrective message.
        """
        if start_date or end_date:
            if not (start_date and end_date):
                raise ValueError("Provide both start_date and end_date (YYYY-MM-DD), "
                                 "or use a named period.")
            try:
                s = datetime.strptime(start_date, '%Y-%m-%d').date()
                e = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Dates must be in YYYY-MM-DD format.")
            if s > e:
                raise ValueError("start_date must be on or before end_date.")
        else:
            today = date.today()
            p = (period or 'this_month').strip().lower()
            if p == 'this_month':
                s = today.replace(day=1)
                e = s + relativedelta(months=1, days=-1)
            elif p == 'last_month':
                e = today.replace(day=1) - timedelta(days=1)
                s = e.replace(day=1)
            elif p == 'this_quarter':
                s = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
                e = s + relativedelta(months=3, days=-1)
            elif p == 'last_quarter':
                this_q = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
                s = this_q - relativedelta(months=3)
                e = this_q - timedelta(days=1)
            elif p == 'this_year':
                s, e = date(today.year, 1, 1), date(today.year, 12, 31)
            elif p == 'ytd':
                s, e = date(today.year, 1, 1), today
            elif p == 'last_year':
                s, e = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
            else:
                raise ValueError(f"Unknown period '{period}'. "
                                 f"Use one of: {', '.join(FINANCIAL_PERIODS)} "
                                 f"or explicit start_date/end_date.")
        label = f"{s.strftime('%d/%m/%Y')} – {e.strftime('%d/%m/%Y')}"
        return s.isoformat(), e.isoformat(), label

    @staticmethod
    def _parse_engine_number(value):
        """Engine values arrive as '1,234.56' strings or floats — normalize."""
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(',', ''))
        except (TypeError, ValueError):
            return None

    def financial_metric(self, metric, period=None, start_date=None, end_date=None,
                         company_ids=None):
        """Compute a defined accounting metric via the canonical report engine."""
        spec = FINANCIAL_METRICS.get((metric or '').strip().lower())
        if spec is None:
            return {"error": f"Unknown metric '{metric}'. "
                             f"Valid metrics: {', '.join(sorted(FINANCIAL_METRICS))}."}
        if 'abstract.financial.report' not in self.env:
            return {"error": "The accounting reports engine (cyllo_accounting) is not "
                             "installed, so financial metrics cannot be computed."}
        try:
            start, end, label = self._resolve_period(period, start_date, end_date)
        except ValueError as e:
            return {"error": str(e)}

        try:
            env = self._company_env(company_ids)
            # target_move=['posted'] mirrors the report UI's default (posted
            # entries only) — and the engine's SQL requires a non-empty value.
            data, _filters = env['abstract.financial.report'].get_report(
                1, 'year', start_date=start, end_date=end,
                target_move=['posted'])
            d = data[0]

            if spec['source'] == '__income_total__':
                income = d.get('income')
                raw = income[2] if income and len(income) > 2 else None
            else:
                raw = d.get(spec['source'])
            value = self._parse_engine_number(raw)
            if value is None:
                return {"error": f"The report engine returned no value for '{metric}' "
                                 f"in {label}."}

            currency = self.env.company.currency_id
            action = self.env.ref(spec['action'], raise_if_not_found=False)

            result = {
                "metric": metric,
                "value": value,
                "formatted": f"{currency.symbol or ''}{value:,.2f}",
                "currency": currency.name,
                "period": {"start": start, "end": end, "label": label},
                "report": spec['report'],
                "provenance": f"Computed by the {spec['report']} report engine "
                              f"for {label}.",
            }
            if action:
                result["report_link"] = (f"/web#action={action.id}"
                                         f"&cyllo_date_from={start}&cyllo_date_to={end}")
            else:
                result["report_link_note"] = "Report link unavailable."
            _logger.info("[cyllo_ai] financial_metric %s %s -> %s",
                         metric, label, result["formatted"])
            return result
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] financial_metric failed metric=%s: %s", metric, e)
            return {"error": f"financial_metric failed: {e}"}

    def _resolve_filter_ids(self, model, values):
        """Resolve a mixed list of names/ids against ``model``.

        Returns ``(ids, unmatched_names)``. Runs as the user, so resolution
        respects record rules.
        """
        ids, missing = [], []
        Model = self.env[model]
        for v in values or []:
            if isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit()):
                ids.append(int(v))
                continue
            found = Model.name_search(str(v).strip(), limit=1)
            if found:
                ids.append(found[0][0])
            else:
                missing.append(str(v))
        return ids, missing

    def accounting_report(self, report, period=None, start_date=None, end_date=None,
                          partners=None, journals=None, analytics=None, accounts=None,
                          include_draft=False, company_ids=None):
        """Link to an official accounting report (filters pre-applied), with
        headline figures where the engine can be invoked cheaply. Never
        re-derives accounting numbers."""
        spec = ACCOUNTING_REPORTS.get((report or '').strip().lower())
        if spec is None:
            return {"error": f"Unknown report '{report}'. "
                             f"Valid reports: {', '.join(sorted(ACCOUNTING_REPORTS))}."}
        try:
            start, end, label = self._resolve_period(period, start_date, end_date)
        except ValueError as e:
            return {"error": str(e)}

        action = self.env.ref(spec['action'], raise_if_not_found=False)
        if action is None:
            return {"error": f"The {spec['label']} report is not available "
                             f"(is the cyllo_accounting module installed?)."}

        # Resolve name-based filters to ids and build the deep-link params.
        link_params = [f"cyllo_date_from={start}", f"cyllo_date_to={end}"]
        resolved, applied, unmatched = {}, [], []
        filter_args = {'partners': partners, 'journals': journals,
                       'analytics': analytics, 'accounts': accounts}
        for arg, values in filter_args.items():
            if not values:
                continue
            model, url_param = REPORT_FILTERS[arg]
            ids, missing = self._resolve_filter_ids(model, values)
            if ids:
                resolved[arg] = ids
                link_params.append(f"{url_param}={','.join(map(str, ids))}")
                applied.append(f"{arg}={len(ids)}")
            unmatched.extend(f"{arg[:-1]} '{m}'" for m in missing)
        target_move = ['posted', 'draft'] if include_draft else ['posted']
        if include_draft:
            link_params.append("cyllo_target_move=posted,draft")

        result = {
            "report": spec['label'],
            "period": {"start": start, "end": end, "label": label},
            "report_link": f"/web#action={action.id}&" + "&".join(link_params),
            "provenance": f"Official {spec['label']} report — the link opens "
                          f"filtered to {label}"
                          + (f" with {', '.join(applied)} applied" if applied else "")
                          + ".",
        }
        if unmatched:
            result["unmatched_filters"] = (
                f"Not found (ignored): {', '.join(unmatched)}.")

        # Best-effort headline figures from the canonical engines; a failure
        # here degrades to link-only, never fails the tool.
        try:
            headline = self._report_headline(
                spec.get('headline'), start, end, company_ids,
                journal_ids=resolved.get('journals'),
                analytic_ids=resolved.get('analytics'),
                target_move=target_move)
            if headline:
                result["headline"] = headline
        except Exception as e:
            _logger.warning("[cyllo_ai] accounting_report headline failed report=%s: %s",
                            report, e)
            self.env.cr.rollback()
            result["headline_note"] = "Headline totals unavailable; open the report."

        _logger.info("[cyllo_ai] accounting_report %s %s link=%s headline=%s",
                     report, label, result["report_link"], bool(result.get("headline")))
        return result

    def _report_headline(self, kind, start, end, company_ids,
                         journal_ids=None, analytic_ids=None, target_move=None):
        """Headline figures for a report period, via the same engines the UI calls."""
        if not kind:
            return None
        env = self._company_env(company_ids)
        target_move = target_move or ['posted']
        engine_kwargs = {'start_date': start, 'end_date': end}
        if journal_ids:
            engine_kwargs['journal_ids'] = journal_ids
        if analytic_ids:
            engine_kwargs['analytic_ids'] = analytic_ids

        if kind in ('pnl', 'balance') and 'abstract.financial.report' in self.env:
            data, _f = env['abstract.financial.report'].get_report(
                1, 'year', target_move=target_move, **engine_kwargs)
            d = data[0]
            keys = (('gross_profit', 'gross_profit'), ('total_expense', 'expenses'),
                    ('total_earnings', 'net_profit')) if kind == 'pnl' else \
                  (('total_assets', 'total_assets'), ('total_liability', 'total_liabilities'),
                   ('total_equity', 'equity'), ('total_balance', 'total_balance'))
            out = {}
            for engine_key, name in keys:
                v = self._parse_engine_number(d.get(engine_key))
                if v is not None:
                    out[name] = v
            return out or None

        if kind == 'trial' and 'trial.balance.report' in self.env:
            # NB: this engine's move-state filter kwarg is `options`
            res = env['trial.balance.report'].get_report(
                1, 'year', options=target_move, **engine_kwargs)
            totals = res[2][0] if len(res) > 2 and res[2] else {}
            common = res[3] if len(res) > 3 and isinstance(res[3], dict) else {}
            out = {}
            if totals:
                out['total_debit'] = self._parse_engine_number(totals.get('debit'))
                out['total_credit'] = self._parse_engine_number(totals.get('credit'))
            if common:
                out['end_debit_sum'] = self._parse_engine_number(common.get('end_debit_sum'))
                out['end_credit_sum'] = self._parse_engine_number(common.get('end_credit_sum'))
            return {k: v for k, v in out.items() if v is not None} or None

        return None

    def read_accounting_report(self, report, period=None, start_date=None, end_date=None,
                               partners=None, include_draft=False, limit=20,
                               company_ids=None):
        """Read a bounded, structured summary of an official report's contents
        for analysis/comparison. All numbers come from the canonical engines —
        never re-derived. Full detail stays behind the filtered report link."""
        key = (report or '').strip().lower()
        spec = ACCOUNTING_REPORTS.get(key)
        if spec is None:
            return {"error": f"Unknown report '{report}'. "
                             f"Valid reports: {', '.join(sorted(ACCOUNTING_REPORTS))}."}
        if key not in READABLE_REPORTS:
            return {"error": f"'{key}' is not readable yet — use accounting_report "
                             f"for its link. Readable reports: "
                             f"{', '.join(sorted(READABLE_REPORTS))}."}
        try:
            start, end, label = self._resolve_period(period, start_date, end_date)
        except ValueError as e:
            return {"error": str(e)}
        try:
            limit = max(1, min(int(limit or 20), 80))
        except (TypeError, ValueError):
            limit = 20

        partner_ids, unmatched = [], []
        if partners:
            partner_ids, missing = self._resolve_filter_ids('res.partner', partners)
            unmatched = [f"partner '{m}'" for m in missing]

        company_scope = company_ids or self.env.company.ids
        try:
            if key == 'partner_ledger':
                data = self._read_partner_ledger(start, end, partner_ids,
                                                 include_draft, company_scope, limit)
            elif key in ('aged_receivable', 'aged_payable'):
                account_type = ('asset_receivable' if key == 'aged_receivable'
                                else 'liability_payable')
                data = self._read_aged(account_type, end, partner_ids,
                                       company_scope, limit)
                data['note'] = (f"Aged report is as of {end} (posted, unreconciled "
                                f"entries only); buckets are days overdue.")
            elif key == 'trial_balance':
                data = self._read_trial_balance(start, end, include_draft,
                                                company_scope, limit)
            else:  # profit_and_loss / balance_sheet
                data = self._read_financial(start, end, include_draft, company_scope)
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("[cyllo_ai] read_accounting_report failed report=%s: %s",
                            key, e)
            return {"error": f"read_accounting_report failed: {e}"}

        result = {
            "report": spec['label'],
            "period": {"start": start, "end": end, "label": label},
            "data": data,
            "provenance": f"Data computed by the official {spec['label']} engine "
                          f"for {label}.",
        }
        if unmatched:
            result["unmatched_filters"] = f"Not found (ignored): {', '.join(unmatched)}."
        action = self.env.ref(spec['action'], raise_if_not_found=False)
        if action:
            params = [f"cyllo_date_from={start}", f"cyllo_date_to={end}"]
            if partner_ids:
                params.append(f"cyllo_partner_ids={','.join(map(str, partner_ids))}")
            if include_draft:
                params.append("cyllo_target_move=posted,draft")
            result["report_link"] = f"/web#action={action.id}&" + "&".join(params)
        _logger.info("[cyllo_ai] read_accounting_report %s %s", key, label)
        return json.loads(json.dumps(result, default=str))

    def _read_partner_ledger(self, start, end, partner_ids, include_draft,
                             company_ids, limit):
        """Per-partner debit/credit/balance summary from the partner ledger engine."""
        if 'partner.ledger.report' not in self.env:
            raise Exception("partner ledger engine not installed")
        env = self._company_env(company_ids)
        kwargs = {'startDate': start, 'endDate': end, 'company_id': list(company_ids)}
        if include_draft:
            kwargs['parent_state'] = ['posted', 'draft']
        if partner_ids:
            kwargs['partner_id'] = list(partner_ids)
        res, all_ids = env['partner.ledger.report'].get_report(0, limit, **kwargs)

        rows = []
        for pid, t in (res.get('partner_totals') or {}).items():
            debit = t.get('total_debit') or 0
            credit = t.get('total_credit') or 0
            rows.append({
                'partner': t.get('partner_name'),
                'partner_id': pid,
                'total_debit': debit,
                'total_credit': credit,
                'balance': round(debit - credit, 2),
                'entries': t.get('move_lines_count'),
            })
        rows.sort(key=lambda r: abs(r['balance'] or 0), reverse=True)
        return {
            'partners': rows,
            'partners_shown': len(rows),
            'partners_total': len(all_ids or []),
            'total_debit': res.get('totalDebitSum'),
            'total_credit': res.get('totalCreditSum'),
            'currency': res.get('currency_id'),
        }

    def _read_aged(self, account_type, as_of, partner_ids, company_ids, limit):
        """Per-partner aging buckets from the aged receivable/payable engine."""
        if 'aged.payable.receivable.report' not in self.env:
            raise Exception("aged report engine not installed")
        env = self._company_env(company_ids)
        res = env['aged.payable.receivable.report'].get_report(
            account_type, 0, limit, date=as_of, company_ids=list(company_ids))

        totals = res.get('partner_totals') or []
        if partner_ids:
            wanted = set(partner_ids)
            totals = [p for p in totals if p.get('partner_id') in wanted]
        rows = []
        for p in totals:
            row = {'partner': p.get('partner'), 'partner_id': p.get('partner_id'),
                   'total': self._parse_engine_number(p.get('sub_total'))}
            for engine_key, name in AGED_BUCKETS:
                row[name] = self._parse_engine_number(p.get(engine_key))
            rows.append(row)
        rows.sort(key=lambda r: abs(r.get('total') or 0), reverse=True)

        g = res.get('grand_total') or {}
        grand = {name: self._parse_engine_number(g.get(engine_key))
                 for engine_key, name in AGED_BUCKETS}
        grand['total'] = self._parse_engine_number(g.get('total'))
        out = {'partners': rows, 'partners_shown': len(rows),
               'grand_total': grand, 'currency': g.get('currency')}
        if partner_ids:
            out['selected_total'] = round(sum(r.get('total') or 0 for r in rows), 2)
            out['grand_total_note'] = ("grand_total covers the report page, "
                                       "not only the selected partners.")
        return out

    def _read_trial_balance(self, start, end, include_draft, company_ids, limit):
        """Per-account rows + totals from the trial balance engine."""
        if 'trial.balance.report' not in self.env:
            raise Exception("trial balance engine not installed")
        env = self._company_env(company_ids)
        target = ['posted', 'draft'] if include_draft else ['posted']
        res = env['trial.balance.report'].get_report(
            1, 'year', start_date=start, end_date=end, options=target)
        accounts = res[0] if res else []
        rows = []
        for a in accounts[:limit]:
            rows.append({
                'account': a.get('name'),
                'code': a.get('code'),
                'debit': self._parse_engine_number(a.get('debit')),
                'credit': self._parse_engine_number(a.get('credit')),
                'initial': a.get('initial_data'),
                'ending': a.get('end_data'),
            })
        totals = res[2][0] if len(res) > 2 and res[2] else {}
        common = res[3] if len(res) > 3 and isinstance(res[3], dict) else {}
        return {
            'accounts': rows,
            'accounts_shown': len(rows),
            'accounts_total': len(accounts),
            'totals': {
                'debit': self._parse_engine_number(totals.get('debit')),
                'credit': self._parse_engine_number(totals.get('credit')),
                **{k: self._parse_engine_number(v) for k, v in common.items()},
            },
        }

    def _read_financial(self, start, end, include_draft, company_ids):
        """All named totals from the P&L / Balance Sheet engine."""
        if 'abstract.financial.report' not in self.env:
            raise Exception("financial report engine not installed")
        env = self._company_env(company_ids)
        target = ['posted', 'draft'] if include_draft else ['posted']
        data, _f = env['abstract.financial.report'].get_report(
            1, 'year', start_date=start, end_date=end, target_move=target)
        d = data[0]
        keys = ['gross_profit', 'total_income', 'total_expense', 'total_earnings',
                'total_current_asset', 'total_assets', 'total_current_liability',
                'total_liability', 'total_equity', 'total_unallocated_earning',
                'total_balance']
        out = {k: self._parse_engine_number(d.get(k))
               for k in keys if d.get(k) is not None}
        income = d.get('income')
        if income and len(income) > 2:
            out['revenue'] = self._parse_engine_number(income[2])
        out['currency_symbol'] = d.get('currency_symbol')
        out['note'] = ("'revenue' is the raw income total; 'total_income' is net of "
                       "direct costs; 'total_earnings' is net profit.")
        return out

    def render_chart(self, chart_type='bar', title='', categories=None, series=None):
        """Build an Apache ECharts option from a simple spec.

        Returns ``{'chart_config': <echarts option>, 'message': <ack>}``. The
        orchestrator strips chart_config out to the UI and feeds only the short
        ack back to the LLM (so the full config doesn't bloat the context).
        """
        categories = categories or []
        series = series or []
        ctype = (chart_type or 'bar').lower()
        if ctype not in ('bar', 'line', 'pie', 'scatter'):
            ctype = 'bar'

        option = {'title': {'text': title or ''}, 'legend': {}}
        if ctype == 'pie':
            first = series[0] if series else {'name': title, 'data': []}
            data = [
                {'name': (categories[i] if i < len(categories) else str(i + 1)), 'value': v}
                for i, v in enumerate(first.get('data', []) or [])
            ]
            option['tooltip'] = {'trigger': 'item'}
            option['series'] = [{
                'name': first.get('name') or title, 'type': 'pie',
                'radius': '70%', 'data': data,
            }]
        elif ctype == 'scatter':
            option['tooltip'] = {'trigger': 'item'}
            option['xAxis'] = {'type': 'value'}
            option['yAxis'] = {'type': 'value'}
            option['series'] = [{
                'name': s.get('name'), 'type': 'scatter',
                'data': [[i, v] for i, v in enumerate(s.get('data', []) or [])],
            } for s in series]
        else:  # bar / line
            option['tooltip'] = {'trigger': 'axis'}
            option['grid'] = {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True}
            option['xAxis'] = {'type': 'category', 'data': categories}
            option['yAxis'] = {'type': 'value'}
            option['series'] = [{
                'name': s.get('name'), 'type': ctype, 'data': s.get('data', []) or [],
            } for s in series]
        # This ack is the model's only feedback about the chart, and it arrives
        # exactly when the model is deciding what to write — so it repeats the
        # placement instruction from the system prompt rather than just confirming.
        return {'chart_config': option,
                'message': 'Chart ready. Write `[[chart]]` on its own line at the '
                           'point in your answer where it should appear.'}
