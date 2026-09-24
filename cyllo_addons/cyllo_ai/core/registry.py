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
Capability registry — progressive disclosure for tools/agents.

Holds cheap ``{name, description, is_read_only}`` descriptors that are safe to
list in the prompt up front; the full input schema is fetched on demand only
when a capability is actually used. This keeps dozens of tool schemas out of
the base context window.

Base scope: register/list/get over in-memory :class:`Tool` instances.
Later: schema-on-demand loading, per-agent sub-registries, budgeted rendering.
"""
from typing import Dict, List

from .tools.base import Tool


class ToolRegistry:
    """In-memory registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def tools(self) -> List[Tool]:
        """All registered tools (used to build provider tool specs)."""
        return list(self._tools.values())

    def descriptors(self) -> List[dict]:
        """Cheap listing for the prompt — names + one-liners, no schemas."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_read_only": t.is_read_only,
            }
            for t in self._tools.values()
        ]

    def schema(self, name: str) -> dict:
        """Full input schema for a single tool (loaded on demand)."""
        return self._tools[name].input_schema
