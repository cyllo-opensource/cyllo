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
Tool abstraction.

A Tool is a self-describing capability the agent can invoke. The
``is_read_only`` flag is the spine of both safety and parallelism:

- read-only tools (analytics, lookups) run without confirmation;
- write tools (CRUD execution) go through the preview/confirm sandbox.

Tools receive a :class:`ToolContext` at call time. It carries ``env`` (so ORM
access runs as the user and ``ir.rules`` apply — never ``sudo()``) plus
runtime-injected state the LLM must NOT control (company scope, the originating
user query). LLM-provided arguments arrive as ``**kwargs``.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolContext:
    """Runtime context handed to every tool invocation."""
    env: Any
    user_query: str = ""
    company_ids: List[int] = field(default_factory=list)
    session_id: str = ""
    # The (untrusted) client UI-context hint for this turn: where the user is
    # and any host-screen payload merged in (e.g. the analytics sheet's fields).
    # Tools that need screen context read it here; access is still ACL-checked.
    ui_context: Dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for an agent-invokable capability."""

    #: short, unique identifier used by the LLM to call the tool
    name: str = ""
    #: one-line description shown to the model (selection guidance)
    description: str = ""
    #: human-friendly activity label streamed to the UI ("Analyzing data")
    label: str = ""
    #: read-only tools skip the write-confirmation gate
    is_read_only: bool = True
    #: JSON-schema of the LLM-provided arguments
    input_schema: Dict[str, Any] = {}

    @abstractmethod
    def run(self, ctx: ToolContext, **kwargs) -> Any:
        """Execute the tool and return its result (str or JSON-able dict)."""
        raise NotImplementedError
