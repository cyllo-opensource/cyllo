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
"""Tests for the chart-request check: the LLM decides whether the user asked for a chart."""
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.chart_intent import CHART_REQUEST_HINT, user_asked_for_chart
from odoo.addons.cyllo_ai.core.llm_client import LLMClient
from odoo.addons.cyllo_ai.core.orchestrator import Orchestrator
from odoo.addons.cyllo_ai.core.tools.base import ToolContext


class TestChartIntent(TransactionCase):

    def _answer(self, reply):
        calls = []

        def complete(client, prompt, timeout=60):
            calls.append(prompt)
            if isinstance(reply, Exception):
                raise reply
            return reply
        return calls, patch.object(LLMClient, "complete", complete)

    def test_yes_means_asked_and_is_asked_once_per_turn(self):
        calls, mocked = self._answer("YES")
        ctx = ToolContext(env=self.env, user_query="plot my sales per customer")
        with mocked:
            self.assertTrue(user_asked_for_chart(ctx))
            self.assertTrue(user_asked_for_chart(ctx))
        self.assertEqual(len(calls), 1)
        self.assertIn("plot my sales per customer", calls[0])

    def test_no_or_failure_means_not_asked(self):
        _calls, mocked = self._answer("NO")
        with mocked:
            self.assertFalse(user_asked_for_chart(
                ToolContext(env=self.env, user_query="show me sales by customer")))
        _calls, mocked = self._answer(Exception("provider down"))
        with mocked:
            self.assertFalse(user_asked_for_chart(
                ToolContext(env=self.env, user_query="create a chart")))

    def test_requested_chart_adds_the_hint_to_the_turn(self):
        orch = Orchestrator(self.env)
        _calls, mocked = self._answer("YES")
        with mocked, patch("odoo.addons.cyllo_ai.core.orchestrator.is_installed",
                           return_value=True):
            state, _ctx, _terminal = orch._begin("chart-intent-test", "create a chart", [], False)
        self.assertIn(CHART_REQUEST_HINT, orch._assemble(state)[0].content)

    def test_unrequested_chart_adds_no_hint(self):
        orch = Orchestrator(self.env)
        _calls, mocked = self._answer("NO")
        with mocked, patch("odoo.addons.cyllo_ai.core.orchestrator.is_installed",
                           return_value=True):
            state, _ctx, _terminal = orch._begin("chart-intent-test", "show me sales", [], False)
        self.assertNotIn(CHART_REQUEST_HINT, orch._assemble(state)[0].content)
