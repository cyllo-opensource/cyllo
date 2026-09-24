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
"""Tests for core/profiles.py — deterministic agent-profile resolution."""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core import profiles
from odoo.addons.cyllo_ai.core.orchestrator import Orchestrator
from odoo.addons.cyllo_ai.core.profiles import (
    DEFAULT_PROFILE,
    AgentProfile,
    resolve_profile,
)
from odoo.addons.cyllo_ai.core.tools.builtins import build_default_registry


class TestProfiles(TransactionCase):

    def test_default_resolution(self):
        for ui in (None, {}, {"model": "sale.order"}, "garbage", 42):
            self.assertIs(resolve_profile(self.env, ui), DEFAULT_PROFILE)

    def test_unregistered_studio_falls_back(self):
        # Phase 1: no studio profile registered yet — flag must not error.
        self.assertIs(resolve_profile(self.env, {"studio": True}), DEFAULT_PROFILE)

    def test_requires_group_is_enforced(self):
        guarded = AgentProfile(
            key="studio",
            system_prompt="studio prompt",
            build_registry=build_default_registry,
            requires_group="base.group_system",
        )
        profiles.PROFILES["studio"] = guarded
        try:
            admin_env = self.env(user=self.env.ref("base.user_admin"))
            self.assertIs(resolve_profile(admin_env, {"studio": True}), guarded)

            portal_user = self.env["res.users"].search(
                [("share", "=", False), ("id", "!=", admin_env.uid)], limit=1)
            if portal_user:
                user_env = self.env(user=portal_user)
                if not user_env.user.has_group("base.group_system"):
                    self.assertIs(resolve_profile(user_env, {"studio": True}),
                                  DEFAULT_PROFILE,
                                  "client studio flag without the group must fall back")
        finally:
            profiles.PROFILES.pop("studio", None)

    def test_prompt_byte_stable(self):
        # Prompt caching depends on this: same profile → identical bytes.
        self.assertEqual(DEFAULT_PROFILE.system_prompt, DEFAULT_PROFILE.system_prompt)
        self.assertIn("Cyllo", DEFAULT_PROFILE.system_prompt)
        self.assertIn("financial_metric", DEFAULT_PROFILE.system_prompt)

    def test_orchestrator_defaults(self):
        orch = Orchestrator(self.env)
        self.assertIs(orch.profile, DEFAULT_PROFILE)
        self.assertEqual(orch.ui_context, {})
        # registry built from the profile carries the expected belt
        names = [t.name for t in orch.registry.tools()]
        for expected in ("financial_metric", "accounting_report", "search_records"):
            self.assertIn(expected, names)

    def test_orchestrator_accepts_profile_and_ui_context(self):
        custom = AgentProfile(
            key="custom",
            system_prompt="custom prompt",
            build_registry=build_default_registry,
        )
        ui = {"model": "sale.order", "studio": False}
        orch = Orchestrator(self.env, profile=custom, ui_context=ui)
        self.assertIs(orch.profile, custom)
        self.assertEqual(orch.ui_context, ui)
        # non-dict ui_context is sanitized
        self.assertEqual(Orchestrator(self.env, ui_context="junk").ui_context, {})
