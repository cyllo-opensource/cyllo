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
"""Tests for the confirm/resume flow — proceed vs cancel vs edit (change request)."""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.orchestrator import Orchestrator
from odoo.addons.cyllo_ai.core.session import Message, SessionState


def _pending_state(name="send_email"):
    state = SessionState()
    state.messages = [
        Message(role="user", content="email Azure about the overdue invoice"),
        Message(role="assistant", content="",
                tool_calls=[{"id": "c1", "name": name, "arguments": {}}]),
    ]
    state.pending = {"tool_call_id": "c1", "name": name,
                     "query": "{}", "message": "Send it?"}
    return state


class TestResumePending(TransactionCase):

    def setUp(self):
        super().setUp()
        self.orch = Orchestrator(self.env)

    def test_cancel_word_aborts_without_replay(self):
        state = _pending_state()
        self.orch._resume_pending(state, "cancel")
        self.assertIsNone(state.pending)
        tool_msgs = [m for m in state.messages if m.role == "tool"]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("Cancellation confirmed", tool_msgs[0].content)
        self.assertEqual(state.messages[-1].role, "tool",
                         "no user message is replayed on a bare cancel")

    def test_edit_text_aborts_and_replays_as_user_message(self):
        state = _pending_state()
        self.orch._resume_pending(state, "make it shorter and mention the due date")
        self.assertIsNone(state.pending)
        tool_msgs = [m for m in state.messages if m.role == "tool"]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("requested changes", tool_msgs[0].content)
        self.assertEqual(state.messages[-1].role, "user",
                         "the edit text must be replayed so the agent revises")
        self.assertEqual(state.messages[-1].content,
                         "make it shorter and mention the due date")

    def test_abandoned_pending_is_closed_in_begin(self):
        # a NEW message (interrupted=False) while a confirm is pending must
        # close the dangling tool call before appending the user turn
        state = _pending_state()
        record = self.env["chatbot.session"].get_or_create("test_abandon_session")
        record.save_state(state.to_dict())
        new_state, _ctx = self.orch._begin(
            "test_abandon_session", "show me last 5 sale orders", None, False)
        self.assertIsNone(new_state.pending)
        roles = [m.role for m in new_state.messages]
        self.assertEqual(roles[-2:], ["tool", "user"],
                         "pending closed as tool result, then the new user turn")
        self.assertIn("moved on", new_state.messages[-2].content)

    def test_proceed_word_dispatches_by_tool_name(self):
        # send_email pending with an invalid payload: proves dispatch reached
        # execute_confirmed_email (returns its own error), not the CRUD executor
        state = _pending_state(name="send_email")
        state.pending["query"] = "not json"
        self.orch._resume_pending(state, "proceed")
        self.assertIsNone(state.pending)
        out = state.messages[-1]
        self.assertEqual(out.role, "tool")
        self.assertIn("Email send failed", out.content)
