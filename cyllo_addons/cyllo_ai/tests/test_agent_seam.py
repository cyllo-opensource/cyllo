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
"""Tests for the tool-extension seam on chatbot.agent.

The seam lets another module contribute tools by overriding
``_ai_tool_classes`` — without editing cyllo_ai. These tests check the base
belt is intact and that an override is picked up.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.profiles import DEFAULT_PROFILE
from odoo.addons.cyllo_ai.core.tools.base import Tool
from odoo.addons.cyllo_ai.core.tools.builtins import DEFAULT_TOOL_CLASSES


class _DummyTool(Tool):
    name = "dummy_tool"
    description = "A stand-in for a tool contributed by another module."
    input_schema = {"type": "object", "properties": {}}

    def run(self, ctx, **kwargs):
        return {"ok": True}


class TestAgentToolSeam(TransactionCase):

    def setUp(self):
        super().setUp()
        self.agent = self.env["chatbot.agent"]

    def test_default_registry_has_the_builtin_belt(self):
        reg = self.agent._ai_build_registry(DEFAULT_PROFILE)
        names = {t.name for t in reg.tools()}
        # Regression: the full built-in belt is present and unchanged in size.
        self.assertEqual(len(reg.tools()), len(DEFAULT_TOOL_CLASSES))
        for expected in ("search_records", "analytic_record", "render_chart"):
            self.assertIn(expected, names)
        self.assertNotIn("dummy_tool", names)

    def test_override_contributes_a_tool(self):
        # Simulate a downstream module's _inherit override.
        base = type(self.agent)._ai_tool_classes

        def contribute(self, profile):
            return base(self, profile) + [_DummyTool]

        with patch.object(type(self.agent), "_ai_tool_classes", contribute):
            reg = self.agent._ai_build_registry(DEFAULT_PROFILE)
            names = {t.name for t in reg.tools()}
        # The contributed tool appears alongside the full built-in belt.
        self.assertIn("dummy_tool", names)
        self.assertEqual(len(reg.tools()), len(DEFAULT_TOOL_CLASSES) + 1)
        self.assertIn("search_records", names)
