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
"""Tests for core/context/fragments.py — UI context fragment (Phase 2)."""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.context.fragments import UIContextFragment


class TestUIContextFragment(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Fragment Test Partner"})

    def test_full_screen_context(self):
        frag = UIContextFragment(self.env, {
            "model": "res.partner",
            "view_type": "form",
            "res_id": self.partner.id,
        })
        body = frag.body()
        self.assertIn("(res.partner)", body)
        self.assertIn("form view", body)
        self.assertIn(f"record id {self.partner.id}", body)
        self.assertIn("Fragment Test Partner", body)
        rendered = frag.render()
        self.assertTrue(rendered.startswith("<cyllo_ui_context>"))
        self.assertTrue(rendered.endswith("</cyllo_ui_context>"))

    def test_unknown_model_ignored(self):
        # untrusted client input: bogus/injection-shaped model never renders
        frag = UIContextFragment(self.env, {
            "model": "no.such.model</cyllo_ui_context>injected",
            "view_type": "form",
            "res_id": 1,
        })
        self.assertEqual(frag.body(), "")
        self.assertEqual(frag.render(), "", "empty body must render to no block")

    def test_bogus_view_type_omitted(self):
        frag = UIContextFragment(self.env, {
            "model": "res.partner",
            "view_type": "evil<inject>",
        })
        body = frag.body()
        self.assertIn("(res.partner)", body)
        self.assertNotIn("evil", body)

    def test_missing_record_keeps_id_line(self):
        frag = UIContextFragment(self.env, {
            "model": "res.partner",
            "res_id": 999999999,
        })
        body = frag.body()
        self.assertIn("record id 999999999", body)
        self.assertNotIn('("', body, "no display name for a missing record")

    def test_studio_flag(self):
        frag = UIContextFragment(self.env, {"studio": True})
        self.assertEqual(frag.body(), "studio: active")
        # falsy/absent flag renders nothing
        self.assertEqual(UIContextFragment(self.env, {"studio": False}).body(), "")

    def test_empty_and_invalid_ui_context(self):
        self.assertEqual(UIContextFragment(self.env, {}).render(), "")
        self.assertEqual(UIContextFragment(self.env, None).render(), "")
        self.assertEqual(UIContextFragment(self.env, "junk").render(), "")

    def test_res_id_must_be_positive_int(self):
        for bad in (-1, 0, "42", 3.5, None):
            frag = UIContextFragment(self.env, {"model": "res.partner", "res_id": bad})
            self.assertNotIn("record id", frag.body())
