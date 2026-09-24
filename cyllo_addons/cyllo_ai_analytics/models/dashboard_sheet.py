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
AI chart suggestions for the analytics sheet builder.

`suggest_charts_for_sheet` is called by the in-builder panel with the sheet's
*already-available* dimensions and measures (the exact fields shown in the
Dimensions/Measures panels). The LLM only SELECTS and pairs from those lists —
it never invents a field — and every pick is validated back against the lists,
so an invalid/hallucinated field is impossible by construction. The chart type
is chosen deterministically from the dimension's kind.

`suggest_charts_for_table` is the "quick dashboard" entry point: given a whole
model, it enumerates that model's storable fields into the same candidate lists
and reuses `suggest_charts_for_sheet`, so proposing charts for a table and for a
sheet share one code path (and one card shape for the UI).

The LLM call goes through cyllo_ai's provider-agnostic LLMClient (not the
legacy dashboard GPT path), unifying the AI stack.
"""
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.cyllo_ai.core.field_security import SENSITIVE_COLUMNS
from odoo.addons.cyllo_ai.core.llm_client import LLMClient

_logger = logging.getLogger(__name__)

# How many suggestions to return.
MAX_SUGGESTIONS = 6
# Field kinds treated as time / numeric for chart-type selection.
_TIME_TYPES = ("date", "datetime")
_NUMERIC_TYPES = ("integer", "float", "monetary")
# Field kinds usable as chart dimensions (group-by). Measures are the numeric
# kinds above; everything else (text, html, binary, x2many, …) isn't chartable.
_DIMENSION_TYPES = ("char", "selection", "date", "datetime", "many2one", "boolean")
# Technical/audit fields excluded from table enumeration — noise, not analytics.
_SKIP_FIELDS = frozenset({
    "id", "display_name", "create_uid", "create_date", "write_uid",
    "write_date", "__last_update", "sequence", "color",
})
_SKIP_FIELD_PREFIXES = ("message_", "activity_")
# Bound the candidate lists so a very wide model can't bloat the LLM prompt.
MAX_CANDIDATE_DIMENSIONS = 40
MAX_CANDIDATE_MEASURES = 25


class DashboardSheet(models.Model):
    _inherit = "dashboard.sheet"

    def suggest_charts_for_sheet(self, dimensions, measures, focus=None):
        """Return ranked chart suggestions built from the given fields.

        :param dimensions: list of ``{column, label, field_type}`` — the
            available dimension fields (from the builder's Dimensions panel).
        :param measures: same shape — the available measure fields.
        :param focus: optional free-text hint (the user's phrasing, e.g.
            "revenue by month" or "charts about customers") that biases which
            pairings the LLM proposes. ``None`` for the plain "generate" path.
        :returns: list of ``{title, question, dimension, measure, chart_type,
            reason}`` where ``dimension``/``measure`` are echoed field dicts the
            panel maps back to its own field objects to apply.
        """
        dims = [d for d in (dimensions or []) if d.get("column")]
        meas = [m for m in (measures or []) if m.get("column")]
        if not dims or not meas:
            return []

        picks = self._ai_pick_chart_pairs(dims, meas, focus)
        dim_by_col = {d["column"]: d for d in dims}
        meas_by_col = {m["column"]: m for m in meas}

        suggestions = []
        seen = set()
        for pick in picks:
            dim = dim_by_col.get(pick.get("dimension_column"))
            measure = meas_by_col.get(pick.get("measure_column"))
            if not dim or not measure:
                continue  # reject anything not in the candidate lists
            key = (dim["column"], measure["column"])
            if key in seen:
                continue
            seen.add(key)
            sugg = self._assemble_suggestion(
                dim, measure, title=pick.get("title"), question=pick.get("question"))
            if sugg is None:
                continue  # relation with no usable name column -> dropped
            suggestions.append(sugg)
            if len(suggestions) >= MAX_SUGGESTIONS:
                break
        return suggestions

    @api.model
    def suggest_charts_for_table(self, model_name, focus=None):
        """Propose charts for an entire model/table — the "quick dashboard" flow.

        Enumerates the model's storable fields into dimension/measure candidates
        and reuses :meth:`suggest_charts_for_sheet` to pick and shape them, so
        the result is the same ``{title, question, dimension, measure,
        chart_type, reason}`` cards the suggestion UI already renders.

        :param model_name: technical model name, e.g. ``"sale.order"``.
        :param focus: optional free-text hint biasing the picks.
        :returns: list of suggestion cards (empty if the model is unknown, the
            user cannot read it, or it has no usable dimension/measure fields).
        """
        if not model_name or model_name not in self.env:
            return []
        model = self.env[model_name]
        # Model-level access: sql_execute enforces record rules but not the model
        # ACL, so gate the whole proposal on the user's read right to this model.
        if not model.check_access_rights("read", raise_exception=False):
            return []
        dims, meas = self._enumerate_table_fields(model)
        if not dims or not meas:
            return []
        return self.suggest_charts_for_sheet(dims, meas, focus=focus)

    @api.model
    def resolve_analytics_models(self, terms):
        """Resolve free-text table names to real, chartable models — so the chat
        can turn "sales", "purchase" into ``sale.order``, ``purchase.order``
        safely. Matches an exact technical name first, then a name/model
        ``ilike``; keeps only NON-transient models the user can READ (same gates
        as the sheet's Tables picker). Returns ``[{model, name}]``, one best
        match per term, deduped and order-preserving.

        :param terms: list of free-text terms or technical model names.
        """
        out, seen = [], set()
        IrModel = self.env["ir.model"]
        for raw in (terms or []):
            term = (raw or "").strip()
            if not term:
                continue
            records = IrModel.search(
                ['|', ('model', '=', term),
                 '|', ('model', 'ilike', term), ('name', 'ilike', term)],
                limit=10)
            for rec in records:
                if rec.model in seen or rec.model not in self.env:
                    continue
                model = self.env[rec.model]
                if model._transient or model._abstract:
                    continue
                if not model.check_access_rights("read", raise_exception=False):
                    continue
                seen.add(rec.model)
                out.append({"model": rec.model, "name": rec.name})
                break  # best (first accessible, non-transient) match per term
        return out

    def _enumerate_table_fields(self, model):
        """Split a model's *storable* fields into dimension/measure candidates,
        in the shape :meth:`suggest_charts_for_sheet` expects.

        Field source is ``fields_get()`` — the same call the sheet builder uses —
        so field-level security is inherited for free (it excludes fields the
        user's groups can't access). On top we drop the masked credential columns
        (``SENSITIVE_COLUMNS``, which carry no ``groups``). Only stored fields
        qualify (raw SQL needs a real column); audit/technical fields are skipped;
        the lists are capped so a very wide model can't bloat the LLM prompt.
        """
        table = model._table
        dims, meas = [], []
        for name, meta in model.fields_get().items():
            if name in _SKIP_FIELDS or name.startswith(_SKIP_FIELD_PREFIXES):
                continue
            if name in SENSITIVE_COLUMNS:
                continue
            if not meta.get("store"):
                continue
            ftype = meta.get("type")
            candidate = {
                "column": f"{table}.{name}",
                "label": meta.get("string") or name,
                "field_type": ftype,
                "name": name,
                # Translatable chars are stored as JSONB; charts must read the
                # active-language value (-> 'en_US'), so carry the flag through.
                "is_json": bool(meta.get("translate")),
            }
            if ftype in _NUMERIC_TYPES:
                meas.append(candidate)
            elif ftype in _DIMENSION_TYPES:
                if ftype == "many2one":
                    # Resolved to the related record's display name (with a join)
                    # by _resolve_dimension_display, so charts never show ids.
                    candidate["model"] = {"relation": meta.get("relation")}
                dims.append(candidate)
        return dims[:MAX_CANDIDATE_DIMENSIONS], meas[:MAX_CANDIDATE_MEASURES]

    # -- quick dashboard: create charts + dashboard from picks ---------------

    @api.model
    def create_quick_dashboard(self, name, picks):
        """Create a dashboard with one chart per pick — the "quick dashboard" flow.

        Charts are INDEPENDENT and single-table; each pick's ``model`` selects its
        own base table, so a dashboard can span several models (e.g. sales +
        purchase) with NO joins between them. Atomic: builds a ``dashboard.sheet``
        per pick, creates the ``dashboard.config`` and links them; any failure
        rolls the whole thing back.

        Everything is re-validated server-side (client input is NOT trusted):
        create rights are required (admins only, per ir.model.access), and each
        pick's model + columns must be in the user's accessible set, so a tampered
        pick can neither escalate nor chart a restricted field.

        :param name: dashboard name.
        :param picks: list of ``{model, dimension_column, measure_column, title}``.
        :returns: ``{dashboard_id, name, chart_count}``.
        """
        if not name or not picks:
            raise ValidationError(_("A name and at least one chart are required."))
        Config = self.env["dashboard.config"]
        Sheet = self.env["dashboard.sheet"]
        # Creating a dashboard needs create rights on both models (admins only).
        if not (Config.check_access_rights("create", raise_exception=False)
                and Sheet.check_access_rights("create", raise_exception=False)):
            raise AccessError(_("You do not have permission to create dashboards."))

        company_id = self.env.company.id
        # Cache the per-model field maps + metadata so picks sharing a model are
        # validated/built without re-enumerating each time.
        model_cache = {}

        def _ctx_for(model_name):
            if model_name not in model_cache:
                ctx = None
                if model_name and model_name in self.env:
                    model = self.env[model_name]
                    if model.check_access_rights("read", raise_exception=False):
                        dims, meas = self._enumerate_table_fields(model)
                        ctx = {
                            "model": model,
                            "dim_by_col": {d["column"]: d for d in dims},
                            "meas_by_col": {m["column"]: m for m in meas},
                            "ir_model": self.env["ir.model"]._get(model_name),
                        }
                model_cache[model_name] = ctx
            return model_cache[model_name]

        sheets = Sheet
        for pick in picks:
            ctx = _ctx_for((pick or {}).get("model"))
            if not ctx:
                continue  # unknown / inaccessible model -> skip
            dim = ctx["dim_by_col"].get(pick.get("dimension_column"))
            measure = ctx["meas_by_col"].get(pick.get("measure_column"))
            if not dim or not measure:
                continue  # outside the accessible field set -> never trust the client
            resolved = self._resolve_dimension_display(dim)
            if resolved is None:
                continue  # relation with no usable name column
            # Chart type: honour an explicit pick if it is valid for this
            # dimension's kind (constrained set, never a misleading type);
            # otherwise fall back to the deterministic default.
            default_type = self._suggest_chart_type(resolved.get("field_type"))[0]
            requested = (pick.get("chart_type") or "").strip()
            allowed = self._allowed_chart_types(resolved.get("field_type"))
            chart_type = requested if requested in allowed else default_type
            vals = self._build_quick_sheet_vals(
                pick, resolved, measure, ctx["model"], ctx["ir_model"],
                company_id, chart_type)
            sheets |= Sheet.create(vals)

        if not sheets:
            raise ValidationError(
                _("None of the selected charts could be built from accessible fields."))

        config = Config.create({"name": (name or "AI Dashboard")[:32]})
        config.write({
            "sheet_ids": [fields.Command.link(s.id) for s in sheets],
            # The config defaults to admin-only visibility; make sure the creator
            # can see their own dashboard.
            "user_ids": [fields.Command.link(self.env.uid)],
        })
        return {"dashboard_id": config.id, "name": config.name,
                "chart_count": len(sheets)}

    def _build_quick_sheet_vals(self, pick, dim, measure, model, ir_model,
                                company_id, chart_type):
        """Build ``create()`` vals for one chart: tables + dimension/measure axes
        + type. The SQL itself is computed by ``_compute_query`` from these — the
        measure carries ``SUM(...)`` so it aggregates and groups by the dimension.
        Relational dimensions become the related record's display name + a join,
        so charts show names, never ids.
        """
        main_table = model._table
        has_currency = bool(
            model._fields.get("currency_id") and model._fields["currency_id"].store)
        sheet_type = self.env["dashboard.sheet.type"].search(
            [("ttype", "=", chart_type)], limit=1)

        relational = dim.get("field_type") == "many2one" and dim.get("display_field")
        if relational:
            dim_col = f'{dim["rel_table"]}.{dim["display_field"]}'
            dim_type = dim.get("display_field_type")
            dim_json = bool(dim.get("display_field_is_json"))
        else:
            dim_col = dim["column"]
            dim_type = dim.get("field_type")
            dim_json = bool(dim.get("is_json"))
        dim_alias = dim_col.replace(".", "_")
        dim_expr = self._ai_col_expr(
            dim_col, dim_type, dim_json, main_table, has_currency, company_id)

        meas_col = measure["column"]
        meas_alias = meas_col.replace(".", "_")
        meas_expr = self._ai_col_expr(
            meas_col, measure.get("field_type"), bool(measure.get("is_json")),
            main_table, has_currency, company_id)

        axis_ids = [
            fields.Command.create({
                "type": "dimension", "value": dim.get("label"),
                "alias": dim_alias, "column": dim_col,
                "query": f"{dim_expr} AS {dim_alias}",
            }),
            fields.Command.create({
                "type": "measure", "value": measure.get("label"),
                "aggregate_func": "SUM", "alias": meas_alias, "column": meas_col,
                "query": f"SUM({meas_expr}) AS {meas_alias}",
                # The un-aggregated expression, mirroring the manual builder's
                # `buildFieldQuery`. The sheet builder needs it to show the
                # currency selector (gated on `hasMonetary`) and to re-apply a
                # changed aggregate — it rewrites an in-memory copy only, so the
                # stored `query` above keeps its SUM for `_compute_query`.
                "monetaryInBase": (
                    meas_expr if measure.get("field_type") == "monetary" else False),
            }),
        ]

        table_ids = [fields.Command.create({
            "name": model._description or ir_model.name, "model": model._name,
            "join": main_table, "linked": False, "field": False,
            "model_id": ir_model.id,
        })]
        if relational:
            fk = dim["name"]
            rel_table = dim["rel_table"]
            table_ids.append(fields.Command.create({
                "name": dim.get("rel_model_name"),
                "model": (dim.get("model") or {}).get("relation"),
                "join": f"JOIN {rel_table} ON {rel_table}.id = {main_table}.{fk}",
                "linked": True, "field": fk, "model_id": dim.get("rel_model_id"),
            }))

        return {
            "name": pick.get("title") or f'{measure.get("label")} by {dim.get("label")}',
            "type": chart_type,
            "sheet_type_id": sheet_type.id if sheet_type else False,
            "dimension_axis": "x",
            # The sheet builder assumes every sheet carries a display currency;
            # leaving it unset made `get_sheet_data` return [], which blanked the
            # builder's state and broke Save for every AI-generated sheet.
            "currency_id": self.env["res.company"].browse(
                company_id).currency_id.id,
            "axis_ids": axis_ids,
            "table_ids": table_ids,
        }

    def _ai_col_expr(self, column, field_type, is_json, main_table,
                     has_currency, company_id):
        """SQL column expression for one axis (no alias, no aggregate). Mirrors
        ``buildAxisEntry``: JSON-translatable -> ``->> 'en_US'``; monetary ->
        base-currency conversion (the ``{selectedCurrency}`` placeholder is
        resolved by ``sql_execute``); anything else -> the raw column.
        """
        if is_json:
            return f"{column} ->> 'en_US'"
        if field_type == "monetary":
            source_currency = (
                f"{main_table}.currency_id" if has_currency
                else f"(SELECT currency_id FROM res_company WHERE id = {company_id})")
            rate = (
                f"COALESCE((SELECT rate FROM res_currency_rate "
                f"WHERE currency_id = {source_currency} AND company_id = {company_id} "
                f"ORDER BY name DESC LIMIT 1), 1) * "
                f"COALESCE((SELECT rate FROM res_currency_rate "
                f"WHERE currency_id = {{selectedCurrency}} AND company_id = {company_id} "
                f"ORDER BY name DESC LIMIT 1), 1)")
            return f"ROUND({column} / {rate}, 2)"
        return column

    # -- live dashboard editing (edit a CREATED dashboard by chat) -----------
    #
    # These operate on real, persisted records (not the pre-create builder), so
    # "make the revenue chart a pie" / "drop the vendor one" / "add sales by
    # customer" change the dashboard the user is viewing. Every op re-checks
    # access server-side and is reversible (type flips back, a dropped chart is
    # UNLINKED not deleted — the sheet may live on other dashboards — and an
    # added chart can be dropped).

    def _sheet_dimension_field_type(self, sheet):
        """Best-effort field type of a sheet's dimension, to compute the chart
        types allowed for it. Maps the dimension axis column's table back to a
        model via the sheet's own tables. Returns None when it can't be told."""
        dim_axis = sheet.axis_ids.filtered(lambda a: a.type == "dimension")[:1]
        col = dim_axis.column or "" if dim_axis else ""
        if "." not in col:
            return None
        table, _, field = col.partition(".")
        for t in sheet.table_ids:
            if t.model and t.model in self.env and self.env[t.model]._table == table:
                f = self.env[t.model]._fields.get(field)
                if f is not None:
                    return f.type
        return None

    def _editable_meta(self, sheet):
        """Agent-facing metadata for one sheet on a live dashboard: id, name,
        current type, base model, and the chart types allowed for its data."""
        dim_type = self._sheet_dimension_field_type(sheet)
        allowed = (self._allowed_chart_types(dim_type) if dim_type
                   else ["bar", "pie", "doughnut", "line"])
        if sheet.type and sheet.type not in allowed:
            allowed = [sheet.type] + allowed
        base = sheet.table_ids.filtered(lambda t: not t.linked)[:1]
        return {
            "id": sheet.id,
            "name": sheet.name,
            "type": sheet.type,
            "model": (base.model if base else
                      (sheet.table_ids[:1].model if sheet.table_ids else "")),
            "allowed_chart_types": allowed,
        }

    @api.model
    def ai_dashboard_edit_context(self, config_id):
        """Editable snapshot of a CREATED dashboard for the chat: its sheets with
        id/name/type/allowed types. Read-gated on the config. Empty if the user
        can't read it."""
        if not config_id:
            return {}
        config = self.env["dashboard.config"].browse(int(config_id))
        if not config.exists() or not config.check_access_rights(
                "read", raise_exception=False):
            return {}
        try:
            config.check_access_rule("read")
        except Exception:
            return {}
        return {
            "config_id": config.id,
            "name": config.name,
            "sheets": [self._editable_meta(s) for s in config.sheet_ids],
        }

    def _live_sheet(self, config_id, sheet_id):
        """Resolve (config, sheet) for a live edit, or (config, None) / (None,
        None) — the sheet must actually be on that dashboard."""
        config = self.env["dashboard.config"].browse(int(config_id or 0))
        sheet = self.browse(int(sheet_id or 0))
        if not config.exists():
            return None, None
        if not sheet.exists() or sheet not in config.sheet_ids:
            return config, None
        return config, sheet

    @api.model
    def ai_dashboard_set_chart_type(self, config_id, sheet_id, chart_type):
        """Change a live sheet's chart type (constrained to its allowed set)."""
        config, sheet = self._live_sheet(config_id, sheet_id)
        if not sheet:
            return {"error": "That chart isn't on this dashboard."}
        if not sheet.check_access_rights("write", raise_exception=False):
            return {"error": "You don't have permission to edit this dashboard."}
        dim_type = self._sheet_dimension_field_type(sheet)
        allowed = self._allowed_chart_types(dim_type) if dim_type else None
        if allowed and chart_type not in allowed:
            return {"error": f"\"{chart_type}\" isn't available for "
                             f"\"{sheet.name}\". Options: {', '.join(allowed)}."}
        sheet_type = self.env["dashboard.sheet.type"].search(
            [("ttype", "=", chart_type)], limit=1)
        if not sheet_type:
            return {"error": f"Unknown chart type \"{chart_type}\"."}
        sheet.write({"type": chart_type, "sheet_type_id": sheet_type.id})
        return {"ok": True, "sheet_id": sheet.id, "title": sheet.name,
                "chart_type": chart_type}

    @api.model
    def ai_dashboard_drop_chart(self, config_id, sheet_id):
        """Remove a chart from THIS dashboard (unlink only — never deletes the
        sheet, which may be shared with other dashboards)."""
        config, sheet = self._live_sheet(config_id, sheet_id)
        if not sheet:
            return {"error": "That chart isn't on this dashboard."}
        if not config.check_access_rights("write", raise_exception=False):
            return {"error": "You don't have permission to edit this dashboard."}
        title = sheet.name
        config.write({"sheet_ids": [fields.Command.unlink(sheet.id)]})
        return {"ok": True, "sheet_id": int(sheet_id), "title": title}

    @api.model
    def ai_dashboard_rename(self, config_id, name):
        """Rename a live dashboard."""
        config = self.env["dashboard.config"].browse(int(config_id or 0))
        if not config.exists():
            return {"error": "Dashboard not found."}
        if not config.check_access_rights("write", raise_exception=False):
            return {"error": "You don't have permission to rename this dashboard."}
        if not (name or "").strip():
            return {"error": "A name is required."}
        config.write({"name": name.strip()[:32]})
        return {"ok": True, "name": config.name}

    @api.model
    def ai_dashboard_add_chart(self, config_id, table, focus=None, chart_type=None):
        """Add ONE chart to a live dashboard: resolve the table, suggest+shape a
        chart (reusing the quick-dashboard build path — single-table, access- and
        field-validated), create the sheet, and link it. Returns the new sheet."""
        config = self.env["dashboard.config"].browse(int(config_id or 0))
        if not config.exists():
            return {"error": "Dashboard not found."}
        if not (config.check_access_rights("write", raise_exception=False)
                and self.check_access_rights("create", raise_exception=False)):
            return {"error": "You don't have permission to add charts."}
        resolved = self.resolve_analytics_models([table])
        if not resolved:
            return {"error": f"I couldn't find a table matching \"{table}\"."}
        model_name = resolved[0]["model"]
        cards = self.suggest_charts_for_table(model_name, focus=focus)
        if not cards:
            return {"error": f"No chartable fields found for "
                             f"{resolved[0]['name']}."}
        card = cards[0]
        dim, measure = card["dimension"], card["measure"]
        allowed = self._allowed_chart_types(dim.get("field_type"))
        ctype = (chart_type if chart_type in allowed
                 else (card.get("chart_type")
                       or self._suggest_chart_type(dim.get("field_type"))[0]))
        vals = self._build_quick_sheet_vals(
            {"title": card.get("title")}, dim, measure, self.env[model_name],
            self.env["ir.model"]._get(model_name), self.env.company.id, ctype)
        sheet = self.create(vals)
        config.write({"sheet_ids": [fields.Command.link(sheet.id)]})
        return {"ok": True, "sheet_id": sheet.id, "title": sheet.name}

    def build_chart_suggestion(self, dimension_column, measure_column,
                               chart_type, dimensions, measures):
        """Build ONE apply-ready suggestion for an explicit (dimension, measure,
        chart_type) — used by the 'edit the current chart' tool. Both columns
        must be in the given available lists; returns None otherwise."""
        dims = [d for d in (dimensions or []) if d.get("column")]
        meas = [m for m in (measures or []) if m.get("column")]
        dim = next((d for d in dims if d["column"] == dimension_column), None)
        measure = next((m for m in meas if m["column"] == measure_column), None)
        if not dim or not measure:
            return None
        return self._assemble_suggestion(dim, measure, chart_type=chart_type)

    def _assemble_suggestion(self, dim, measure, title=None, question=None,
                             chart_type=None):
        """Resolve one (dimension, measure) into an apply-ready suggestion.

        Relational (many2one) dimensions group by the FK id and would show
        numbers — resolve them to the related record's display name (with a
        join); a relation with no usable name column returns None. ``chart_type``
        forces the type (edits); otherwise it's chosen from the dimension kind.
        """
        resolved = self._resolve_dimension_display(dim)
        if resolved is None:
            return None
        auto_type, reason = self._suggest_chart_type(resolved.get("field_type"))
        chosen = chart_type or auto_type
        allowed = self._allowed_chart_types(resolved.get("field_type"))
        # Keep the chosen type selectable even if it came from an edit that sits
        # just outside the default set for the kind.
        if chosen not in allowed:
            allowed = [chosen] + allowed
        return {
            "title": title or f"{measure['label']} by {dim['label']}",
            "question": question or "",
            "dimension": resolved,
            "measure": measure,
            "chart_type": chosen,
            "allowed_chart_types": allowed,
            "reason": reason,
        }

    # -- relational dimension -> display name --------------------------------

    def _resolve_dimension_display(self, dim):
        """Mark a many2one dimension with the related model's display field.

        Non-relational dimensions pass through unchanged. For a many2one we
        resolve the related model's stored display field (``_rec_name`` /
        ``name``) and the related-model metadata, and return the dimension
        annotated with them. The FRONTEND then applies it through the sheet's
        own relational-field path (``_applyRelationalSelection``) — so the join
        and column are built by the same tested code the manual wizard uses.

        Returns ``None`` when a relation has no stored name column, so the
        caller drops the suggestion instead of charting foreign-key ids.
        """
        if dim.get("field_type") != "many2one":
            return dim
        relation = (dim.get("model") or {}).get("relation")
        if not relation or relation not in self.env:
            return None
        rel_model = self.env[relation]
        name_field = None
        for candidate in (rel_model._rec_name, "name", "display_name"):
            if not candidate:
                continue
            f = rel_model._fields.get(candidate)
            if f is not None and f.store and f.type in ("char", "text"):
                name_field = candidate
                break
        if not name_field:
            return None
        f = rel_model._fields[name_field]
        ir_model = self.env["ir.model"]._get(relation)
        base_label = dim.get("label", dim["column"])
        return {
            **dim,  # keep column (fk), name (fk field), model.relation, field_type=many2one
            "label": f'{base_label} > {f.string or name_field}',
            "base_label": base_label,
            "display_field": name_field,
            "display_field_label": f.string or name_field,
            "display_field_type": f.type,
            "display_field_is_json": bool(f.translate),
            "rel_table": rel_model._table,
            "rel_model_id": ir_model.id,
            "rel_model_name": rel_model._description or ir_model.name,
        }

    # -- chart type (deterministic; pie deferred) ---------------------------

    @staticmethod
    def _suggest_chart_type(dim_field_type):
        """Pick a chart type from the dimension's kind. Returns (type, reason)."""
        if dim_field_type in _TIME_TYPES:
            return "line", "the dimension is a time period, so a line shows the trend"
        if dim_field_type in _NUMERIC_TYPES:
            return "scatter", "a numeric dimension reads as a distribution"
        return "bar", "a categorical dimension compares clearest as bars"

    @staticmethod
    def _allowed_chart_types(dim_field_type):
        """Chart types that make VISUAL sense for a dimension of this kind — the
        constrained set the user (or the chat) may switch between. Keeps the
        auto-picked default first and never offers a type that would misrepresent
        the data (e.g. a pie over a time series). All values are real
        ``dashboard.sheet.type`` ttypes."""
        if dim_field_type in _TIME_TYPES:
            return ["line", "bar", "scatter"]
        if dim_field_type in _NUMERIC_TYPES:
            return ["scatter", "bar", "line"]
        # categorical (char / selection / many2one / boolean)
        return ["bar", "pie", "doughnut", "radar", "funnel"]

    # -- LLM selection (with a deterministic fallback) ----------------------

    def _ai_pick_chart_pairs(self, dims, meas, focus=None):
        """Ask the LLM to select meaningful (dimension, measure) pairs from the
        given lists and phrase a title/question. ``focus`` is an optional
        free-text hint that steers the picks. Falls back to a deterministic
        pairing when no LLM is configured or the response can't be parsed."""
        client = LLMClient(self.env)
        if not client.is_configured():
            return self._fallback_pairs(dims, meas)
        prompt = self._build_pairs_prompt(dims, meas, focus)
        try:
            raw = client.complete(prompt)
            cleaned = raw.strip()
            # Strip ```json fences if present.
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
            picks = json.loads(cleaned)
            if isinstance(picks, dict):
                picks = picks.get("suggestions") or picks.get("charts") or []
            if isinstance(picks, list) and picks:
                return picks
        except Exception as e:
            _logger.info("[cyllo_ai_analytics] chart-pair LLM parse failed: %s", e)
        return self._fallback_pairs(dims, meas)

    @staticmethod
    def _build_pairs_prompt(dims, meas, focus=None):
        dim_lines = "\n".join(
            f'- column="{d["column"]}" label="{d.get("label", d["column"])}" '
            f'type={d.get("field_type")}' for d in dims)
        meas_lines = "\n".join(
            f'- column="{m["column"]}" label="{m.get("label", m["column"])}" '
            f'type={m.get("field_type")}' for m in meas)
        focus_line = ""
        if focus:
            focus_line = (
                f'\nThe user specifically asked for: "{focus}". Prioritise '
                "pairings that answer this; only fall back to general picks if "
                "nothing fits. Still use ONLY the columns listed above.\n")
        return f"""
You suggest the most useful charts for an analytics sheet.

Available DIMENSIONS (group-by candidates):
{dim_lines}

Available MEASURES (numeric values to aggregate):
{meas_lines}
{focus_line}
Propose up to {MAX_SUGGESTIONS} meaningful charts. For each, pick ONE dimension
and ONE measure — using ONLY the "column" values listed above, verbatim. Prefer
business-meaningful combinations (e.g. revenue by a category) over technical or
audit fields (create/write user or date, ids). Give a short title and a one-line
business question the chart answers.

Return ONLY a JSON array, no prose:
[
  {{"title": "...", "question": "...", "dimension_column": "<a dimension column>",
    "measure_column": "<a measure column>"}}
]
"""

    @staticmethod
    def _fallback_pairs(dims, meas):
        """No-LLM fallback: pair the first measure with each dimension."""
        measure = meas[0]
        return [{
            "title": f'{measure.get("label", measure["column"])} by {d.get("label", d["column"])}',
            "question": "",
            "dimension_column": d["column"],
            "measure_column": measure["column"],
        } for d in dims[:MAX_SUGGESTIONS]]
