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
Result capping — bound the size of a tool result before it enters the model's
context (the "cap-and-spill" pillar, refuse-with-hint variant).

A single analytics/query tool can return tens of thousands of rows; injected
verbatim into the conversation that inflates cost and latency and can overflow
the context window — and the whole result also rides along in history for the
following turns. This module bounds each result: list-shaped results are
truncated to a preview carrying the TRUE total plus a hint to narrow the query;
anything still too large falls back to a bounded character preview.

Nothing is silently dropped — the model is always told the result was capped
(``_truncated`` / ``_hint``) and how to get the rest (narrow the query), so it
never mistakes a preview for the whole answer. We prefer refuse-with-hint over
paging: for analytics, narrowing the query beats reading tens of rows at a time
back through the model.

Pure — no Odoo env — so it is unit-testable in isolation and reused at the one
orchestrator chokepoint every tool result flows through.
"""
import json


def _truncate_dict_lists(out, preview_rows):
    """Return a copy of ``out`` with over-long top-level lists truncated to
    ``preview_rows`` items, annotated with the true total so the model knows
    data was withheld."""
    result = {}
    truncated_any = False
    for key, value in out.items():
        if isinstance(value, list) and len(value) > preview_rows:
            result[key] = value[:preview_rows]
            result[f"_{key}_total"] = len(value)
            result[f"_{key}_shown"] = preview_rows
            truncated_any = True
        else:
            result[key] = value
    if truncated_any:
        result["_truncated"] = True
        result["_hint"] = (
            "Lists were truncated to a preview. This is NOT the full result — "
            "narrow the query (add filters, a smaller date range, or an "
            "aggregation) to get complete, specific data.")
    return result


def cap_result(out, max_chars, preview_rows, preview_chars):
    """Bound a tool result for the model's context.

    :param out: the tool's raw return — a str, or a JSON-able dict/list. Tools
        that pre-serialize their result to a JSON string are handled too: the
        string is parsed back so list-shaped results can be truncated by row.
    :param max_chars: serialized results at or under this size pass through
        unchanged; larger ones are capped.
    :param preview_rows: how many items of an over-long list to keep.
    :param preview_chars: hard cap for the character-preview fallback.
    :returns: ``(content_str, was_capped)`` — ``content_str`` is what to store
        as the tool message; ``was_capped`` is True if anything was withheld.
    """
    # Recover structure from tools that return a pre-serialized JSON string.
    structured = out
    if isinstance(out, str):
        head = out.lstrip()[:1]
        if head in ('{', '['):
            try:
                structured = json.loads(out)
            except (ValueError, TypeError):
                structured = out

    content = out if isinstance(out, str) else json.dumps(out, default=str)
    if len(content) <= max_chars:
        return content, False

    # Structure-aware: keep the shape, trim the big lists, keep the totals.
    if isinstance(structured, dict):
        capped = _truncate_dict_lists(structured, preview_rows)
        trimmed = json.dumps(capped, default=str)
        if len(trimmed) <= max_chars:
            return trimmed, True
        content = trimmed  # still too big -> fall through to a char preview

    # Fallback: a bounded character preview with an explicit hint.
    return json.dumps({
        "_truncated": True,
        "_total_chars": len(content),
        "_preview": content[:preview_chars],
        "_hint": ("Result too large to include in full. This is a partial "
                  "preview — narrow the query (filters, smaller date range, or "
                  "aggregation) to get complete, specific data."),
    }, default=str), True
