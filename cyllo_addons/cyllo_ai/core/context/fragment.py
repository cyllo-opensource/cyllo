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
Context fragment base class.

Each injectable piece of ambient context (user, company, active screen,
permissions) is a typed fragment wrapped in XML-style markers. The markers let
the engine recognize and **diff** its own injected blocks across turns — the
prerequisite for diff-based injection (inject full once, then only deltas).

Base scope: ``render()`` (full block). ``diff()`` has a default full-render
fallback; real per-field diffing lands with the diff-injection phase.
"""
from abc import ABC, abstractmethod


class ContextFragment(ABC):
    """A self-identifying, renderable block of ambient context."""

    #: XML-ish marker tag, e.g. "cyllo_user_context"
    marker: str = "cyllo_context"

    @abstractmethod
    def body(self) -> str:
        """Render the inner text of this fragment."""
        raise NotImplementedError

    def render(self) -> str:
        """Full block wrapped in open/close markers; empty body → no block."""
        body = self.body()
        if not body:
            return ""
        return f"<{self.marker}>\n{body}\n</{self.marker}>"

    def diff(self, previous: "ContextFragment") -> str:
        """
        Return only what changed vs ``previous`` (same marker type).

        Base implementation re-renders fully if anything differs; the
        diff-injection phase replaces this with field-level deltas.
        """
        if previous is not None and previous.body() == self.body():
            return ""
        return self.render()
