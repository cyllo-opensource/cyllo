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
Session working state — dataclasses + a store that persists to Postgres.

This is the *engine's* working state (LLM-format messages including tool
calls/results, context baseline, token counts, pending confirmation),
distinct from the user-facing display transcript in ``chatbot.history``.

``SessionStore`` is the seam between the plain-Python engine and the
``chatbot.session`` Odoo model: the engine works with ``SessionState``
dataclasses; the store handles (de)serialization to the model's JSONB blob.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """One message in the engine's working history (provider-agnostic)."""
    role: str                                       # system|user|assistant|tool
    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None   # assistant: [{id,name,arguments}]
    tool_call_id: Optional[str] = None                  # tool result: which call
    name: Optional[str] = None                          # tool result: tool name

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )


@dataclass
class SessionState:
    """Everything the engine needs to continue a conversation."""
    messages: List[Message] = field(default_factory=list)
    baseline: Dict[str, Any] = field(default_factory=dict)   # context diff baseline (later)
    tokens: int = 0                                          # accounting (later)
    pending: Optional[Dict[str, Any]] = None                 # paused write awaiting confirm
    company_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [m.to_dict() for m in self.messages],
            "baseline": self.baseline,
            "tokens": self.tokens,
            "pending": self.pending,
            "company_ids": self.company_ids,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SessionState":
        data = data or {}
        return cls(
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            baseline=data.get("baseline", {}),
            tokens=data.get("tokens", 0),
            pending=data.get("pending"),
            company_ids=data.get("company_ids", []),
        )


class SessionStore:
    """Loads/saves :class:`SessionState` via the ``chatbot.session`` model."""

    def __init__(self, env):
        self.env = env

    def load(self, session_id: str) -> SessionState:
        record = self.env['chatbot.session'].get_or_create(session_id)
        return SessionState.from_dict(record.state or {})

    def save(self, session_id: str, state: SessionState) -> None:
        record = self.env['chatbot.session'].get_or_create(session_id)
        record.save_state(state.to_dict())
