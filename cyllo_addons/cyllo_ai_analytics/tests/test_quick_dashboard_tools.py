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
"""Tests for the conversational quick-dashboard tools: open + edit.

These drive the builder from chat — open_quick_dashboard renders the widget
(optionally seeded), edit_quick_dashboard emits validated patches the live
widget applies. Both re-check their inputs against the builder's own state /
the user's access, so a bogus chat request can't do anything unsafe.
"""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.profiles import DEFAULT_PROFILE
from odoo.addons.cyllo_ai.core.tools.base import ToolContext
from odoo.addons.cyllo_ai_analytics.core.tools import (
    OpenQuickDashboardTool,
    EditQuickDashboardTool,
    EditLiveDashboardTool,
)


class TestQuickDashboardTools(TransactionCase):

    def setUp(self):
        super().setUp()
        self.open_tool = OpenQuickDashboardTool()
        self.edit_tool = EditQuickDashboardTool()
        self.live_tool = EditLiveDashboardTool()

    def _ctx(self, ui_context=None):
        return ToolContext(
            env=self.env, user_query="", company_ids=self.env.company.ids,
            session_id="t", ui_context=ui_context or {})

    # -- the seam proof: both tools are on the belt -------------------------

    def test_tools_contributed_to_agent_belt(self):
        reg = self.env["chatbot.agent"]._ai_build_registry(DEFAULT_PROFILE)
        names = {t.name for t in reg.tools()}
        self.assertIn("open_quick_dashboard", names)
        self.assertIn("edit_quick_dashboard", names)
        self.assertIn("edit_dashboard", names)

    # -- open ---------------------------------------------------------------

    def test_open_without_tables_opens_empty_picker(self):
        out = self.open_tool.run(self._ctx())
        self.assertEqual(out["widget"]["key"], "quick_dashboard")
        self.assertEqual(out["widget"]["props"]["seed_models"], [])
        self.assertFalse(out["widget"]["props"]["auto_generate"])

    def test_open_with_tables_seeds_and_autogenerates(self):
        out = self.open_tool.run(self._ctx(), tables=["res.partner"])
        props = out["widget"]["props"]
        self.assertTrue(props["auto_generate"])
        self.assertIn("res.partner", [m["model"] for m in props["seed_models"]])

    # -- edit: set chart type (constrained) ---------------------------------

    def _builder_ctx(self):
        # A minimal published builder state (as the widget would publish it).
        return self._ctx({"quick_dashboard": {
            "name": "Sales DB",
            "tables": [{"model": "sale.order", "name": "Sales Order"}],
            "cards": [{
                "id": "c1", "title": "Sales by Customer",
                "chart_type": "bar",
                "allowed_chart_types": ["bar", "pie", "doughnut"],
                "selected": True,
            }],
        }})

    def test_edit_set_valid_chart_type(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="set_chart_type",
            card_id="c1", chart_type="pie")
        self.assertEqual(out["apply_qd"],
                         {"action": "set_chart_type", "card_id": "c1", "chart_type": "pie"})

    def test_edit_set_invalid_chart_type_is_refused(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="set_chart_type",
            card_id="c1", chart_type="gauge")
        self.assertNotIn("apply_qd", out)     # nothing applied
        self.assertIn("gauge", out["message"])

    def test_edit_unknown_card_asks_instead_of_guessing(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="set_chart_type",
            card_id="c999", chart_type="pie")
        self.assertNotIn("apply_qd", out)

    def test_edit_toggle_chart(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="toggle_chart", card_id="c1", selected=False)
        self.assertEqual(out["apply_qd"],
                         {"action": "toggle_chart", "card_id": "c1", "selected": False})

    def test_edit_add_table_resolves_model(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="add_table", table="res.partner")
        self.assertEqual(out["apply_qd"]["action"], "add_table")
        self.assertEqual(out["apply_qd"]["model"], "res.partner")

    def test_edit_add_unknown_table_reports(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="add_table", table="no.such.thing")
        self.assertNotIn("apply_qd", out)

    def test_edit_rename(self):
        out = self.edit_tool.run(
            self._builder_ctx(), action="rename", name="  Q3 Review  ")
        self.assertEqual(out["apply_qd"], {"action": "rename", "name": "Q3 Review"})

    def test_edit_create_requires_a_selection(self):
        ctx = self._ctx({"quick_dashboard": {
            "cards": [{"id": "c1", "title": "x", "selected": False,
                       "allowed_chart_types": ["bar"], "chart_type": "bar"}]}})
        out = self.edit_tool.run(ctx, action="create")
        self.assertNotIn("apply_qd", out)

    def test_edit_without_open_builder_reports(self):
        out = self.edit_tool.run(self._ctx(), action="create")
        self.assertNotIn("apply_qd", out)

    # -- live dashboard editing (edit_dashboard tool) -----------------------

    def _live_dashboard(self):
        pick = {"model": "ir.attachment",
                "dimension_column": "ir_attachment.type",
                "measure_column": "ir_attachment.file_size", "title": "By type"}
        res = self.env["dashboard.sheet"].create_quick_dashboard("Tool Live", [pick])
        config = self.env["dashboard.config"].browse(res["dashboard_id"])
        return config, config.sheet_ids[0]

    def test_live_edit_without_dashboard_reports(self):
        out = self.live_tool.run(
            self._ctx(), action="set_chart_type", sheet_id=1, chart_type="pie")
        self.assertNotIn("apply_dash", out)

    def test_live_edit_set_chart_type_writes_and_reloads(self):
        config, sheet = self._live_dashboard()
        ctx = self._ctx({"dashboard": {"config_id": config.id}})
        out = self.live_tool.run(
            ctx, action="set_chart_type", sheet_id=sheet.id, chart_type="pie")
        self.assertEqual(out["apply_dash"],
                         {"action": "reload", "config_id": config.id})
        self.assertEqual(sheet.type, "pie")   # actually written to the record

    def test_live_edit_invalid_type_no_reload(self):
        config, sheet = self._live_dashboard()
        ctx = self._ctx({"dashboard": {"config_id": config.id}})
        out = self.live_tool.run(
            ctx, action="set_chart_type", sheet_id=sheet.id, chart_type="gauge")
        self.assertNotIn("apply_dash", out)   # refused; nothing to reload

    def test_live_edit_drop_chart(self):
        config, sheet = self._live_dashboard()
        ctx = self._ctx({"dashboard": {"config_id": config.id}})
        out = self.live_tool.run(ctx, action="drop_chart", sheet_id=sheet.id)
        self.assertEqual(out["apply_dash"]["action"], "reload")
        self.assertNotIn(sheet, config.sheet_ids)
