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
"""Tests for the functional-assistant tools (Phase 3 Tier-1):
find_menu / find_setting / describe_feature."""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.tools.builtins import build_default_registry


class TestFunctionalTools(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tools = self.env["chatbot.tools"]

    # -- find_menu ------------------------------------------------------------

    def test_find_menu_returns_existing_paths(self):
        out = self.env["chatbot.tools"].with_user(
            self.env.ref("base.user_admin")).find_menu("settings")
        self.assertIn("menus", out)
        self.assertTrue(out["menus"], "admin must see a Settings-related menu")
        for item in out["menus"]:
            self.assertIn("path", item)
            if "link" in item:
                self.assertRegex(item["link"], r"^/web#action=\d+$")

    def test_find_menu_requires_query(self):
        self.assertIn("error", self.tools.find_menu(""))
        self.assertIn("error", self.tools.find_menu(None))

    def test_find_menu_no_match_is_honest(self):
        out = self.tools.find_menu("zzyzx quux nonexistent")
        self.assertEqual(out["menus"], [])
        self.assertIn("message", out)

    def test_find_menu_respects_group_visibility(self):
        # a menu gated to group_system must not be returned for a basic user
        group_system = self.env.ref("base.group_system")
        menu = self.env["ir.ui.menu"].create({
            "name": "Zzyzx Hidden Feature",
            "groups_id": [(6, 0, [group_system.id])],
        })
        self.assertTrue(menu)
        basic = self.env["res.users"].create({
            "name": "Basic Functional User",
            "login": "basic_functional_user",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.env.registry.clear_cache()  # _visible_menu_ids is ormcached
        admin_out = self.env["chatbot.tools"].with_user(
            self.env.ref("base.user_admin")).find_menu("zzyzx hidden")
        basic_out = self.env["chatbot.tools"].with_user(basic).find_menu("zzyzx hidden")
        self.assertTrue(any("Zzyzx" in m["path"] for m in admin_out["menus"]),
                        "admin (group_system) must see the gated menu")
        self.assertFalse(any("Zzyzx" in m["path"] for m in basic_out.get("menus", [])),
                         "group-gated menu must be hidden from a basic user")

    # -- find_setting -----------------------------------------------------------

    def test_find_setting_structure(self):
        out = self.tools.find_setting("company")
        self.assertIn("settings", out)
        for item in out["settings"]:
            self.assertIn("label", item)
            self.assertIn("technical_name", item)
            self.assertIn("kind", item)

    def test_find_setting_no_match_is_honest(self):
        out = self.tools.find_setting("zzyzx quux nonexistent")
        self.assertEqual(out["settings"], [])
        self.assertIn("message", out)

    def test_find_setting_requires_query(self):
        self.assertIn("error", self.tools.find_setting(""))

    def test_find_setting_works_for_basic_user(self):
        # regression: ir.model.fields is admin-only; fields_get() must be used
        # so non-admin employees can still ask "how do I enable X"
        basic = self.env["res.users"].create({
            "name": "Basic Settings User",
            "login": "basic_settings_user",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        out = self.env["chatbot.tools"].with_user(basic).find_setting("company")
        self.assertNotIn("error", out, "must not raise AccessError for employees")
        self.assertIn("settings", out)

    # -- describe_feature -------------------------------------------------------

    def test_describe_feature_aggregates(self):
        out = self.tools.describe_feature("currency")
        for key in ("menus", "settings", "models"):
            self.assertIn(key, out)
        # 'currency' must hit at least the res.currency model
        self.assertTrue(any(h["model"] == "res.currency" for h in out["models"]))
        self.assertNotIn("message", out, "matches found -> no not-found message")

    def test_describe_feature_not_found_message(self):
        out = self.tools.describe_feature("zzyzx quux nonexistent")
        self.assertIn("message", out)
        self.assertIn("not found", out["message"])

    # -- registration -----------------------------------------------------------

    def test_tools_registered(self):
        names = [t.name for t in build_default_registry().tools()]
        for expected in ("describe_feature", "find_menu", "find_setting"):
            self.assertIn(expected, names)
