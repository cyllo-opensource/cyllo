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
"""Tests for core/normalize.py — message-history hygiene."""
import json

from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.normalize import (
    _drop_stale_tool_failures,
    _remove_orphan_tool_results,
    normalize,
)
from odoo.addons.cyllo_ai.core.session import Message


def _turn(text):
    return Message(role="user", content=text)


def _call(call_id, name="search_records"):
    return Message(role="assistant", content="",
                   tool_calls=[{"id": call_id, "name": name, "arguments": {}}])


def _result(call_id, payload, name="search_records"):
    return Message(role="tool", content=json.dumps(payload),
                   tool_call_id=call_id, name=name)


class TestNormalize(TransactionCase):

    def test_orphan_tool_results_dropped(self):
        msgs = [
            _result("c0", {"records": []}),  # orphan (windowed off its call)
            _turn("hi"),
            _call("c1"),
            _result("c1", {"records": [1]}),
        ]
        out = _remove_orphan_tool_results(msgs)
        self.assertEqual(len(out), 3)
        self.assertNotIn("c0", [m.tool_call_id for m in out if m.role == "tool"])

    def test_stale_failure_scrubbed_with_its_call(self):
        msgs = [
            _turn("gross profit this month"),          # old turn
            _call("c1", "financial_metric"),
            _result("c1", {"error": "boom"}, "financial_metric"),
            _turn("and last month?"),                   # recent turn 1
            _call("c2", "financial_metric"),
            _result("c2", {"value": 5}, "financial_metric"),
            _turn("now this month again"),              # recent turn 2 (current)
        ]
        out = normalize(msgs)
        ids = [m.tool_call_id for m in out if m.role == "tool"]
        self.assertNotIn("c1", ids, "stale failure should be scrubbed")
        self.assertIn("c2", ids, "successful result must remain")
        # the failed call's assistant message (no content, no other calls) is gone
        for m in out:
            if m.role == "assistant" and m.tool_calls:
                self.assertNotIn("c1", [tc["id"] for tc in m.tool_calls])

    def test_recent_failure_kept(self):
        msgs = [
            _turn("old turn"),
            _call("c1"),
            _result("c1", {"records": []}),
            _turn("previous turn"),                     # recent turn 1
            _call("c2"),
            _result("c2", {"error": "bad domain"}),
            _turn("current turn"),                      # recent turn 2
        ]
        out = normalize(msgs)
        ids = [m.tool_call_id for m in out if m.role == "tool"]
        self.assertIn("c2", ids, "failures within the last 2 turns are kept for self-correction")

    def test_partial_batch_keeps_siblings(self):
        # one assistant message fired two calls; only the failed one is scrubbed
        msgs = [
            _turn("old turn"),
            Message(role="assistant", content="", tool_calls=[
                {"id": "a", "name": "count_records", "arguments": {}},
                {"id": "b", "name": "search_records", "arguments": {}},
            ]),
            _result("a", {"error": "x"}, "count_records"),
            _result("b", {"records": [1, 2]}, "search_records"),
            _turn("recent 1"),
            _turn("recent 2"),
        ]
        out = normalize(msgs)
        ids = [m.tool_call_id for m in out if m.role == "tool"]
        self.assertNotIn("a", ids)
        self.assertIn("b", ids)
        asst = next(m for m in out if m.role == "assistant" and m.tool_calls)
        self.assertEqual([tc["id"] for tc in asst.tool_calls], ["b"])

    def test_narration_preserved_when_all_calls_scrubbed(self):
        msgs = [
            _turn("old turn"),
            Message(role="assistant", content="Let me check that.",
                    tool_calls=[{"id": "a", "name": "count_records", "arguments": {}}]),
            _result("a", {"error": "x"}, "count_records"),
            _turn("recent 1"),
            _turn("recent 2"),
        ]
        out = normalize(msgs)
        asst = [m for m in out if m.role == "assistant"]
        self.assertEqual(len(asst), 1)
        self.assertEqual(asst[0].content, "Let me check that.")
        self.assertIsNone(asst[0].tool_calls, "emptied tool_calls collapses to None")

    def test_few_turns_untouched(self):
        msgs = [
            _turn("first"),
            _call("c1"),
            _result("c1", {"error": "x"}),
            _turn("second"),
        ]
        self.assertEqual(_drop_stale_tool_failures(msgs), msgs,
                         "with <= 2 user turns nothing is scrubbed")

    def test_dangling_tool_call_gets_synthetic_result(self):
        # abandoned confirm: assistant tool_call with no result -> providers
        # reject the request (400) unless a result is synthesized
        msgs = [
            _turn("email Azure"),
            _call("c1", "send_email"),          # paused, never resumed
            _turn("show me last 5 sale orders"),  # user moved on
        ]
        out = normalize(msgs)
        results = [m for m in out if m.role == "tool"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].tool_call_id, "c1")
        self.assertEqual(results[0].name, "send_email")
        self.assertIn("never completed", results[0].content)
        # synthetic result must directly follow its assistant message
        idx = next(i for i, m in enumerate(out) if m.role == "assistant")
        self.assertEqual(out[idx + 1].role, "tool")

    def test_no_synthesis_when_results_exist(self):
        msgs = [_turn("q"), _call("c1"), _result("c1", {"ok": 1}), _turn("next")]
        out = normalize(msgs)
        self.assertEqual(len([m for m in out if m.role == "tool"]), 1)

    def test_non_json_tool_content_is_not_failure(self):
        msgs = [
            _turn("old"),
            _call("c1"),
            Message(role="tool", content="plain text result",
                    tool_call_id="c1", name="get_url"),
            _turn("recent 1"),
            _turn("recent 2"),
        ]
        out = normalize(msgs)
        self.assertIn("c1", [m.tool_call_id for m in out if m.role == "tool"])
