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
"""Tests for suggest_charts_for_sheet — candidate validation, type rules, fallback."""
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSuggestCharts(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Sheet = self.env["dashboard.sheet"]
        self.dims = [
            {"column": "sale_order.date_order", "label": "Order > Date", "field_type": "datetime"},
            {"column": "res_partner.name", "label": "Customer > Name", "field_type": "char"},
            {"column": "sale_order.id", "label": "Order > ID", "field_type": "integer"},
        ]
        self.meas = [
            {"column": "sale_order.amount_total", "label": "Order > Total", "field_type": "monetary"},
        ]

    def _sheet(self):
        return self.Sheet.create({"name": "t"})

    # -- chart type rules ---------------------------------------------------

    def test_type_rules(self):
        rule = self.Sheet._suggest_chart_type
        self.assertEqual(rule("datetime")[0], "line")
        self.assertEqual(rule("char")[0], "bar")
        self.assertEqual(rule("monetary")[0], "scatter")

    # -- fallback (no LLM) --------------------------------------------------

    def test_fallback_pairs_when_no_llm(self):
        # LLMClient.is_configured() is False in a bare test env -> fallback path.
        out = self._sheet().suggest_charts_for_sheet(self.dims, self.meas)
        self.assertTrue(out)
        # Every suggestion pairs an available dimension with the measure.
        for s in out:
            self.assertIn(s["dimension"], self.dims)
            self.assertEqual(s["measure"], self.meas[0])
            self.assertIn(s["chart_type"], ("line", "bar", "scatter"))

    def test_datetime_dimension_gets_line(self):
        out = self._sheet().suggest_charts_for_sheet(self.dims, self.meas)
        line = [s for s in out if s["dimension"]["field_type"] == "datetime"]
        self.assertTrue(line and line[0]["chart_type"] == "line")

    # -- chart-type constraints (conversational chart-type editing) ---------

    def test_allowed_chart_types_per_kind(self):
        allowed = self.Sheet._allowed_chart_types
        # A category can become a pie/doughnut; a time series must not.
        self.assertIn("pie", allowed("char"))
        self.assertIn("bar", allowed("char"))
        self.assertNotIn("pie", allowed("datetime"))
        self.assertEqual(allowed("datetime")[0], "line")   # default first
        self.assertEqual(allowed("monetary")[0], "scatter")

    def test_suggestion_cards_carry_allowed_types(self):
        out = self._sheet().suggest_charts_for_sheet(self.dims, self.meas)
        self.assertTrue(out)
        for s in out:
            self.assertTrue(s.get("allowed_chart_types"))
            # The chosen type is always among the offered set.
            self.assertIn(s["chart_type"], s["allowed_chart_types"])

    # -- hallucination rejection -------------------------------------------

    def test_llm_pick_outside_candidate_set_is_dropped(self):
        # LLM returns a measure column that isn't in the candidate list -> dropped.
        bad = [{"title": "x", "question": "q",
                "dimension_column": "res_partner.name",
                "measure_column": "res_users.password"}]
        with patch.object(type(self._sheet()), "_ai_pick_chart_pairs", return_value=bad):
            out = self._sheet().suggest_charts_for_sheet(self.dims, self.meas)
        self.assertEqual(out, [])  # invalid measure column -> nothing survives

    def test_valid_llm_pick_is_kept(self):
        good = [{"title": "Sales by Customer", "question": "Who buys most?",
                 "dimension_column": "res_partner.name",
                 "measure_column": "sale_order.amount_total"}]
        with patch.object(type(self._sheet()), "_ai_pick_chart_pairs", return_value=good):
            out = self._sheet().suggest_charts_for_sheet(self.dims, self.meas)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Sales by Customer")
        self.assertEqual(out[0]["dimension"]["column"], "res_partner.name")
        self.assertEqual(out[0]["chart_type"], "bar")  # char dimension

    def test_empty_inputs(self):
        self.assertEqual(self._sheet().suggest_charts_for_sheet([], self.meas), [])
        self.assertEqual(self._sheet().suggest_charts_for_sheet(self.dims, []), [])

    # -- relational dimension -> display name --------------------------------

    def test_many2one_annotated_with_display_field(self):
        dim = {"column": "res_users.partner_id", "label": "User > Partner",
               "field_type": "many2one", "name": "partner_id",
               "model": {"relation": "res.partner"}}
        resolved = self._sheet()._resolve_dimension_display(dim)
        self.assertIsNotNone(resolved)
        # Stays a many2one (the frontend applies it via the relational path),
        # annotated with the related model's stored display field + metadata.
        self.assertEqual(resolved["field_type"], "many2one")
        self.assertEqual(resolved["column"], "res_users.partner_id")  # fk preserved
        self.assertEqual(resolved["base_label"], "User > Partner")
        self.assertTrue(resolved["display_field"])
        self.assertIn(resolved["display_field_type"], ("char", "text"))
        self.assertEqual(resolved["rel_table"], "res_partner")
        self.assertTrue(resolved["rel_model_id"])
        self.assertTrue(resolved["label"].startswith("User > Partner > "))

    def test_non_relational_dimension_passthrough(self):
        dim = {"column": "sale_order.state", "label": "Order > Status",
               "field_type": "selection", "name": "state", "model": {}}
        self.assertEqual(self._sheet()._resolve_dimension_display(dim), dim)

    def test_unknown_relation_dropped(self):
        dim = {"column": "x.y_id", "field_type": "many2one", "name": "y_id",
               "model": {"relation": "no.such.model.xyz"}}
        self.assertIsNone(self._sheet()._resolve_dimension_display(dim))

    # -- table enumeration (quick-dashboard proposal) -----------------------

    def test_enumerate_table_fields_shape_and_split(self):
        Model = self.env["ir.attachment"]  # always installed; has both kinds
        dims, meas = self._sheet()._enumerate_table_fields(Model)
        self.assertTrue(dims and meas, "attachment should yield both kinds")
        for cand in dims + meas:
            self.assertTrue(cand["column"].startswith(Model._table + "."))
            self.assertIn(cand["field_type"], (
                "integer", "float", "monetary",  # measures
                "char", "selection", "date", "datetime", "many2one", "boolean",
            ))
            self.assertTrue(cand.get("label") and cand.get("name"))
        # file_size is a stored integer -> a measure; name is a char -> dimension.
        self.assertIn("ir_attachment.file_size", [m["column"] for m in meas])
        self.assertIn("ir_attachment.name", [d["column"] for d in dims])

    def test_enumerate_skips_audit_and_nonstored(self):
        dims, meas = self._sheet()._enumerate_table_fields(self.env["res.partner"])
        cols = {c["column"] for c in dims + meas}
        for skipped in ("res_partner.create_uid", "res_partner.create_date",
                        "res_partner.write_date", "res_partner.id",
                        "res_partner.display_name"):
            self.assertNotIn(skipped, cols)

    def test_enumerate_many2one_carries_relation(self):
        dims, _ = self._sheet()._enumerate_table_fields(self.env["res.partner"])
        m2o = [d for d in dims if d["field_type"] == "many2one"]
        self.assertTrue(m2o, "res.partner has many2one fields")
        for d in m2o:
            self.assertTrue((d.get("model") or {}).get("relation"))

    def test_enumerate_excludes_sensitive_credential_fields(self):
        # Masked credential columns (no field groups for fields_get to filter on)
        # are dropped by the SENSITIVE_COLUMNS denylist.
        dims, meas = self._sheet()._enumerate_table_fields(self.env["res.users"])
        cols = {c["column"] for c in dims + meas}
        self.assertNotIn("res_users.password", cols)

    # -- quick dashboard creation (Stage 2) ---------------------------------

    def test_create_quick_dashboard_builds_config_and_charts(self):
        pick = {"model": "ir.attachment",
                "dimension_column": "ir_attachment.type",
                "measure_column": "ir_attachment.file_size",
                "title": "Attachments by type"}
        res = self.Sheet.create_quick_dashboard("Test AI DB", [pick])
        self.assertEqual(res["chart_count"], 1)
        config = self.env["dashboard.config"].browse(res["dashboard_id"])
        self.assertEqual(len(config.sheet_ids), 1)
        sheet = config.sheet_ids
        self.assertEqual(sheet.name, "Attachments by type")
        self.assertEqual(
            len(sheet.axis_ids.filtered(lambda a: a.type == "dimension")), 1)
        self.assertEqual(
            len(sheet.axis_ids.filtered(lambda a: a.type == "measure")), 1)
        # Query is computed from the axes/tables (query_gen empty): aggregated,
        # grouped, and scoped to the model's table.
        self.assertIn("SUM(", sheet.query)
        self.assertIn("GROUP BY", sheet.query)
        self.assertIn("FROM ir_attachment", sheet.query)

    def test_create_quick_dashboard_honors_valid_chart_type(self):
        # A valid explicit type for a categorical dimension (pie) is honoured;
        # the sheet is typed accordingly.
        pick = {"model": "ir.attachment",
                "dimension_column": "ir_attachment.type",
                "measure_column": "ir_attachment.file_size",
                "chart_type": "pie", "title": "Attachments by type"}
        res = self.Sheet.create_quick_dashboard("Typed DB", [pick])
        sheet = self.env["dashboard.config"].browse(res["dashboard_id"]).sheet_ids
        self.assertEqual(sheet.type, "pie")

    def test_create_quick_dashboard_rejects_invalid_chart_type(self):
        # A type that doesn't fit the dimension (pie over nothing categorical is
        # fine, but 'gauge' isn't in the allowed set) falls back to the default,
        # never a misleading/unsupported type.
        pick = {"model": "ir.attachment",
                "dimension_column": "ir_attachment.type",
                "measure_column": "ir_attachment.file_size",
                "chart_type": "gauge", "title": "By type"}
        res = self.Sheet.create_quick_dashboard("Fallback DB", [pick])
        sheet = self.env["dashboard.config"].browse(res["dashboard_id"]).sheet_ids
        self.assertIn(sheet.type, self.Sheet._allowed_chart_types("selection"))
        self.assertNotEqual(sheet.type, "gauge")

    # -- model resolution (conversational "for sales" -> sale.order) --------

    def test_resolve_analytics_models_exact_and_fuzzy(self):
        # Exact technical name resolves; a transient/abstract model never does.
        out = self.Sheet.resolve_analytics_models(["ir.attachment", "res.partner"])
        models = {m["model"] for m in out}
        self.assertIn("ir.attachment", models)
        self.assertIn("res.partner", models)
        for m in out:
            self.assertFalse(self.env[m["model"]]._transient)

    def test_resolve_analytics_models_skips_unknown(self):
        self.assertEqual(
            self.Sheet.resolve_analytics_models(["no.such.model.xyz", ""]), [])

    def test_create_quick_dashboard_spans_multiple_models(self):
        # Two independent single-table charts from two models on one dashboard.
        picks = [
            {"model": "ir.attachment", "dimension_column": "ir_attachment.type",
             "measure_column": "ir_attachment.file_size", "title": "By type"},
            {"model": "ir.attachment", "dimension_column": "ir_attachment.mimetype",
             "measure_column": "ir_attachment.file_size", "title": "By mimetype"},
        ]
        res = self.Sheet.create_quick_dashboard("Multi DB", picks)
        self.assertEqual(res["chart_count"], 2)
        config = self.env["dashboard.config"].browse(res["dashboard_id"])
        self.assertEqual(len(config.sheet_ids), 2)

    def test_create_quick_dashboard_rejects_inaccessible_columns(self):
        # A tampered pick pointing outside the accessible field set (password is
        # denylisted; id is a skipped audit field) is dropped — and with nothing
        # left, the call refuses rather than half-create.
        bad = {"model": "res.users",
               "dimension_column": "res_users.password",
               "measure_column": "res_users.id"}
        with self.assertRaises(ValidationError):
            self.Sheet.create_quick_dashboard("X", [bad])

    def test_create_quick_dashboard_validates_inputs(self):
        with self.assertRaises(ValidationError):
            self.Sheet.create_quick_dashboard("X", [])
        with self.assertRaises(ValidationError):
            self.Sheet.create_quick_dashboard(
                "X", [{"model": "no.such.model.xyz",
                       "dimension_column": "a.b", "measure_column": "a.c"}])

    # -- live dashboard editing (edit a CREATED dashboard) ------------------

    def _make_dashboard(self):
        pick = {"model": "ir.attachment",
                "dimension_column": "ir_attachment.type",
                "measure_column": "ir_attachment.file_size", "title": "By type"}
        res = self.Sheet.create_quick_dashboard("Live DB", [pick])
        config = self.env["dashboard.config"].browse(res["dashboard_id"])
        return config, config.sheet_ids[0]

    def test_ai_dashboard_edit_context(self):
        config, sheet = self._make_dashboard()
        ctx = self.Sheet.ai_dashboard_edit_context(config.id)
        self.assertEqual(ctx["config_id"], config.id)
        self.assertEqual(len(ctx["sheets"]), 1)
        meta = ctx["sheets"][0]
        self.assertEqual(meta["id"], sheet.id)
        self.assertEqual(meta["type"], sheet.type)
        # A selection dimension -> pie is offered.
        self.assertIn("pie", meta["allowed_chart_types"])

    def test_ai_dashboard_set_chart_type_valid(self):
        config, sheet = self._make_dashboard()
        res = self.Sheet.ai_dashboard_set_chart_type(config.id, sheet.id, "pie")
        self.assertTrue(res.get("ok"))
        self.assertEqual(sheet.type, "pie")

    def test_ai_dashboard_set_chart_type_invalid_is_refused(self):
        config, sheet = self._make_dashboard()
        before = sheet.type
        res = self.Sheet.ai_dashboard_set_chart_type(config.id, sheet.id, "gauge")
        self.assertIn("error", res)
        self.assertEqual(sheet.type, before)  # unchanged

    def test_ai_dashboard_set_chart_type_wrong_dashboard(self):
        _, sheet = self._make_dashboard()
        other = self.env["dashboard.config"].create({"name": "Other"})
        res = self.Sheet.ai_dashboard_set_chart_type(other.id, sheet.id, "pie")
        self.assertIn("error", res)   # sheet isn't on that dashboard

    def test_ai_dashboard_drop_chart_unlinks_not_deletes(self):
        config, sheet = self._make_dashboard()
        res = self.Sheet.ai_dashboard_drop_chart(config.id, sheet.id)
        self.assertTrue(res.get("ok"))
        self.assertNotIn(sheet, config.sheet_ids)
        self.assertTrue(sheet.exists())   # unlinked from this config, not deleted

    def test_ai_dashboard_add_chart(self):
        config, _ = self._make_dashboard()
        n = len(config.sheet_ids)
        res = self.Sheet.ai_dashboard_add_chart(config.id, "res.partner")
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(config.sheet_ids), n + 1)

    def test_ai_dashboard_rename(self):
        config, _ = self._make_dashboard()
        res = self.Sheet.ai_dashboard_rename(config.id, "Renamed DB")
        self.assertTrue(res.get("ok"))
        self.assertEqual(config.name, "Renamed DB")

    def test_suggest_charts_for_table_unknown_model(self):
        self.assertEqual(
            self._sheet().suggest_charts_for_table("no.such.model.xyz"), [])

    def test_suggest_charts_for_table_reuses_pipeline(self):
        # No LLM in the test env -> deterministic fallback pairing over the
        # enumerated fields; every card pairs an available dim with a measure.
        out = self._sheet().suggest_charts_for_table("ir.attachment")
        self.assertTrue(out)
        for s in out:
            self.assertIn(s["chart_type"], ("line", "bar", "scatter"))
            self.assertTrue(s["dimension"]["column"].startswith("ir_attachment."))
            self.assertTrue(s["measure"]["column"].startswith("ir_attachment."))
