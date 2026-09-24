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
"""Tests for the analytics AI bridge: chart recommendation + the seam proof."""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.profiles import DEFAULT_PROFILE


class TestRecommendChart(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tools = self.env["cyllo.ai.analytics.tools"]

    # -- the recommendation rules -------------------------------------------

    def test_time_dimension_recommends_line(self):
        t, _ = self.tools._recommend_chart_type(
            ["Jan", "Feb"], [{"data": [1, 2]}], "time")
        self.assertEqual(t, "line")

    def test_few_categories_single_series_recommends_pie(self):
        t, _ = self.tools._recommend_chart_type(
            ["A", "B", "C"], [{"data": [1, 2, 3]}], "category")
        self.assertEqual(t, "pie")

    def test_multiple_series_recommends_bar(self):
        t, _ = self.tools._recommend_chart_type(
            ["A", "B"], [{"data": [1, 2]}, {"data": [3, 4]}], "category")
        self.assertEqual(t, "bar")

    def test_numeric_axis_recommends_scatter(self):
        t, _ = self.tools._recommend_chart_type(
            ["1", "2"], [{"data": [1, 2]}], "number")
        self.assertEqual(t, "scatter")

    def test_many_categories_falls_back_to_bar(self):
        # More slices than a pie can carry -> bar.
        cats = [str(i) for i in range(10)]
        t, _ = self.tools._recommend_chart_type(
            cats, [{"data": list(range(10))}], "category")
        self.assertEqual(t, "bar")

    # -- end-to-end rendering (reuses cyllo_ai's render_chart) ---------------

    def test_recommend_chart_renders_and_explains(self):
        out = self.tools.recommend_chart(
            [{"name": "Sales", "data": [1, 2, 3]}], ["A", "B", "C"], "By region")
        self.assertIn("chart_config", out)
        self.assertIsNotNone(out["chart_config"])
        self.assertIn("pie", out["message"])  # 1 series, 3 categories -> pie

    def test_no_series_is_an_error(self):
        out = self.tools.recommend_chart([], [])
        self.assertIn("error", out)

    # -- the seam proof -----------------------------------------------------

    def test_tool_is_contributed_to_the_agent_belt(self):
        # With this module installed, the agent's registry gains recommend_chart
        # purely through the override — no cyllo_ai edits.
        reg = self.env["chatbot.agent"]._ai_build_registry(DEFAULT_PROFILE)
        names = {t.name for t in reg.tools()}
        self.assertIn("recommend_chart", names)
        # And the built-in belt is still there.
        self.assertIn("render_chart", names)
        self.assertIn("search_records", names)
