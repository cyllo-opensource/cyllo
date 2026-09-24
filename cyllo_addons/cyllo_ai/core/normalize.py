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
Message-history hygiene — run before every LLM call.

Now that the engine owns the message loop (no framework), these invariants are
our responsibility:

- Every ``tool`` result must follow an assistant ``tool_call`` with the same id
  (providers reject orphan tool results).
- Stale tool FAILURES are scrubbed: an old crashed call (e.g. a period that
  once errored) otherwise lingers in context and teaches the model to avoid a
  perfectly valid parameter on later turns. Failures from the current and
  previous user turn are kept — the model needs those to self-correct.

Windowing the history can slice off the start of a tool sequence, leaving a
leading orphan tool result — this drops those.
"""
import json
from typing import List

from .session import Message

# tool failures within this many most-recent user turns are kept
RECENT_TURNS_KEEP_FAILURES = 2


def normalize(messages: List[Message]) -> List[Message]:
    """Return a cleaned copy of ``messages`` safe to send to the provider."""
    messages = _drop_stale_tool_failures(messages)
    messages = _remove_orphan_tool_results(messages)
    return _close_dangling_tool_calls(messages)


def _is_failure(m: Message) -> bool:
    """A tool result whose payload carries an ``error`` key."""
    if m.role != "tool" or not m.content:
        return False
    try:
        payload = json.loads(m.content)
    except (ValueError, TypeError):
        return False
    return isinstance(payload, dict) and bool(payload.get("error"))


def _drop_stale_tool_failures(messages: List[Message]) -> List[Message]:
    """
    Drop failed tool results older than the last ``RECENT_TURNS_KEEP_FAILURES``
    user turns, removing the matching entry from the assistant's ``tool_calls``
    so the call/result pairing stays valid. Assistant messages left with no
    content and no tool_calls are dropped too.
    """
    user_idx = [i for i, m in enumerate(messages) if m.role == "user"]
    if len(user_idx) <= RECENT_TURNS_KEEP_FAILURES:
        return messages
    boundary = user_idx[-RECENT_TURNS_KEEP_FAILURES]

    stale_ids = {
        m.tool_call_id
        for i, m in enumerate(messages)
        if i < boundary and m.tool_call_id and _is_failure(m)
    }
    if not stale_ids:
        return messages

    out: List[Message] = []
    for i, m in enumerate(messages):
        if i >= boundary:
            out.append(m)
            continue
        if m.role == "tool" and m.tool_call_id in stale_ids:
            continue
        if m.role == "assistant" and m.tool_calls:
            kept_calls = [tc for tc in m.tool_calls if tc.get("id") not in stale_ids]
            if kept_calls != m.tool_calls:
                if not kept_calls and not m.content:
                    continue
                m = Message(role=m.role, content=m.content,
                            tool_calls=kept_calls or None)
        out.append(m)
    return out


def _close_dangling_tool_calls(messages: List[Message]) -> List[Message]:
    """Synthesize a result for any assistant tool_call that never got one.

    The confirm flow defers a risky tool's result until the user decides; if
    the session was abandoned mid-confirm (or crashed), the dangling call
    stays in history and providers reject the whole request (400). The
    synthetic result tells the model the action never completed.
    """
    have_results = {m.tool_call_id for m in messages if m.role == "tool"}
    out: List[Message] = []
    for m in messages:
        out.append(m)
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                cid = tc.get("id")
                if cid and cid not in have_results:
                    out.append(Message(
                        role="tool",
                        content=json.dumps({"message": "No result — this action "
                                            "was interrupted and never completed."}),
                        tool_call_id=cid,
                        name=tc.get("name"),
                    ))
    return out


def _remove_orphan_tool_results(messages: List[Message]) -> List[Message]:
    """Drop ``tool`` messages whose tool_call_id has no preceding tool call."""
    seen_call_ids = set()
    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                if tc.get("id"):
                    seen_call_ids.add(tc["id"])
    return [
        m for m in messages
        if not (m.role == "tool" and m.tool_call_id not in seen_call_ids)
    ]
