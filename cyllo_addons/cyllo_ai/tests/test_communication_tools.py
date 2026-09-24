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
"""Tests for the communication tools: send_email / send_text preview+confirm."""
import json

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.tools.builtins import build_default_registry


class TestCommunicationTools(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tools = self.env["chatbot.tools"]
        self.partner = self.env["res.partner"].create({
            "name": "Comm Test Partner",
            "email": "comm.test@example.com",
            "mobile": "+10000000001",
        })
        self.no_contact = self.env["res.partner"].create({
            "name": "No Contact Partner",
        })

    # -- prepare_email ----------------------------------------------------------

    def test_prepare_email_pauses_with_preview(self):
        out = self.tools.prepare_email("Hello,\nYour order shipped.\nThanks",
                                       partner_id=self.partner.id,
                                       subject="Order update")
        self.assertTrue(out.get("__interrupt__"), "must pause for confirmation")
        self.assertIn("comm.test@example.com", out["message"])
        self.assertIn("Order update", out["message"])
        payload = json.loads(out["pending_query"])
        self.assertEqual(payload["kind"], "send_email")
        self.assertEqual(payload["partner_id"], self.partner.id)
        self.assertEqual(payload["body"], "Hello,\nYour order shipped.\nThanks")

    def test_prepare_email_resolves_by_name(self):
        out = self.tools.prepare_email("hi", partner="Comm Test Partner")
        self.assertTrue(out.get("__interrupt__"))
        self.assertEqual(json.loads(out["pending_query"])["partner_id"], self.partner.id)

    def test_prepare_email_default_subject(self):
        out = self.tools.prepare_email("hi", partner_id=self.partner.id)
        payload = json.loads(out["pending_query"])
        self.assertTrue(payload["subject"], "a default subject must be set")

    def test_prepare_email_errors(self):
        self.assertIn("error", self.tools.prepare_email("", partner_id=self.partner.id))
        self.assertIn("error", self.tools.prepare_email("hi"))  # no recipient
        self.assertIn("error", self.tools.prepare_email("hi", partner="Zzyzx Nobody"))
        out = self.tools.prepare_email("hi", partner_id=self.no_contact.id)
        self.assertIn("error", out)
        self.assertIn("email", out["error"])

    # -- execute_confirmed_email -------------------------------------------------

    def test_execute_confirmed_email_posts_message(self):
        before = len(self.partner.message_ids)
        query = json.dumps({"kind": "send_email", "partner_id": self.partner.id,
                            "subject": "Test subject", "body": "line1\nline2"})
        out = self.tools.execute_confirmed_email(query)
        self.assertIn("message", out)
        self.assertIn("✅", out["message"])
        self.partner.invalidate_recordset()
        msgs = self.partner.message_ids
        self.assertEqual(len(msgs), before + 1)
        self.assertEqual(msgs[0].subject, "Test subject")
        self.assertIn("line1", msgs[0].body)
        self.assertIn(self.partner, msgs[0].partner_ids)

    def test_execute_confirmed_email_bad_payload(self):
        self.assertIn("error", self.tools.execute_confirmed_email("not json"))

    # -- prepare_text_message ------------------------------------------------------

    def test_prepare_text_requires_message(self):
        self.assertIn("error", self.tools.prepare_text_message(""))

    def test_prepare_text_gateway_paths(self):
        out = self.tools.prepare_text_message("ping", partner_id=self.partner.id)
        if 'send.sms' not in self.env:
            self.assertIn("not installed", out["error"])
        elif not self.env['sms.gateway.config'].search([('is_active', '=', True)], limit=1):
            self.assertIn("gateway", out["error"])
        else:
            self.assertTrue(out.get("__interrupt__"))
            payload = json.loads(out["pending_query"])
            self.assertEqual(payload["kind"], "send_text")
            self.assertEqual(payload["number"], self.partner.mobile)

    def test_prepare_text_no_number(self):
        if 'send.sms' not in self.env:
            self.skipTest("sms gateway module not installed")
        if not self.env['sms.gateway.config'].search([('is_active', '=', True)], limit=1):
            self.skipTest("no active sms gateway")
        out = self.tools.prepare_text_message("ping", partner_id=self.no_contact.id)
        self.assertIn("error", out)
        self.assertIn("phone", out["error"])

    # -- registration -------------------------------------------------------------

    def test_tools_registered_as_write_tools(self):
        reg = build_default_registry()
        for name in ("send_email", "send_text"):
            tool = reg.get(name)
            self.assertFalse(tool.is_read_only, f"{name} must be a write tool")
            self.assertEqual(tool.input_schema["required"], ["message"])
