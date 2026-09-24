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
Business logic for the analytics AI tools (chart recommendation).

Mirrors cyllo_ai's ``chatbot.tools`` pattern: an AbstractModel holding the
method the pure ``Tool`` wrapper dispatches to. The chart *type* is chosen by
small deterministic rules here; the ECharts config is built by reusing
cyllo_ai's ``render_chart`` — so this module adds only the recommendation.
"""
from odoo import models

# Above this many slices a pie is unreadable — prefer a bar instead.
PIE_MAX_SLICES = 6


class CylloAiAnalyticsTools(models.AbstractModel):
    _name = "cyllo.ai.analytics.tools"
    _description = "Cyllo AI Analytics Tool Implementations"

    @staticmethod
    def _recommend_chart_type(categories, series, category_kind):
        """Pick a chart type from the data shape. Returns ``(type, reason)``."""
        n_series = len(series or [])
        n_cat = len(categories or [])
        kind = (category_kind or "category").lower()
        if kind == "time":
            return "line", "the x-axis is a time dimension, so a line shows the trend"
        if kind == "number":
            return "scatter", "both axes are numeric, so a scatter shows correlation"
        if n_series == 1 and 0 < n_cat <= PIE_MAX_SLICES:
            return "pie", ("a single series across a few categories reads as "
                           "parts of a whole")
        if n_series >= 2:
            return "bar", "several series across categories compare best as grouped bars"
        return "bar", "a categorical comparison reads clearest as bars"

    def recommend_chart(self, series, categories=None, title="",
                        category_kind="category"):
        """Choose the best chart type for the data and render it.

        Reuses ``chatbot.tools.render_chart`` to build the ECharts config, so
        the result carries a ``chart_config`` the orchestrator streams to the
        UI, plus a ``message`` explaining the choice (which the model relays).
        """
        series = series or []
        categories = categories or []
        if not series:
            return {"error": "No data series to chart."}
        chart_type, reason = self._recommend_chart_type(
            categories, series, category_kind)
        rendered = self.env["chatbot.tools"].render_chart(
            chart_type, title, categories, series)
        if isinstance(rendered, dict) and rendered.get("error"):
            return rendered
        return {
            "chart_config": rendered.get("chart_config"),
            "message": (f"Recommended a {chart_type} chart — {reason}. "
                        f"Rendered and shown to the user."),
        }
