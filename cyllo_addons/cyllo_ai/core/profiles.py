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
Agent profiles — deterministic selection of prompt + tool belt.

A profile bundles what makes an "agent": its system prompt, its tool
registry, and (optionally) the access group required to use it. Selection
is rule-based on the client-supplied ``ui_context`` — never an LLM call —
so adding a specialist (e.g. the Studio assistant) costs zero routing
latency.

The client's ``ui_context`` is a HINT (it says where the user is, e.g.
``{"studio": true, "model": "sale.order", ...}``); ``requires_group`` is
checked server-side and is the authority. A requested profile the user is
not entitled to silently falls back to the default.

Prompt-caching note: each profile's ``system_prompt`` must stay byte-stable
across calls — volatile data belongs in context fragments, never here.
"""
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from .registry import ToolRegistry
from .tools.builtins import build_default_registry

_logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant for Cyllo, a modern ERP system. Always refer to "
    "the platform only as Cyllo. Use Markdown for all replies.\n\n"
    "Tool selection rules (prefer the cheapest tool that answers the question):\n"
    "- Accounting/financial METRICS (gross profit, revenue, expenses, net profit, "
    "margins, assets, liabilities, equity, balances): ALWAYS use `financial_metric`. "
    "NEVER compute these with aggregate_records, search_records or analytic_record — "
    "those produce incorrect accounting numbers. In your answer you MUST state the "
    "period exactly as the tool result's period.label (the date range), verbatim — "
    "never rename or summarize it (do not say 'YTD' or 'this month' unless that is "
    "what the label shows). State the value, quote the provenance line including "
    "that date range, and link the report as [Open report](<report_link>) — the "
    "link opens the report filtered to that same period; render the link href "
    "EXACTLY as given by the tool (it carries the period filters). If no metric "
    "matches, use `accounting_report` for the closest official report instead of "
    "computing a guess.\n"
    "- Accounting REPORTS (trial balance, general ledger, partner ledger, aged "
    "receivable/payable, tax report, cash book, bank book): use `accounting_report`. "
    "These are report engines, NOT searchable models — never query them with "
    "search_records. Pass any filters the user mentions (partners, journals, "
    "analytic accounts, accounts — by name; include_draft for unposted entries); "
    "the link opens pre-filtered. Present the headline figures (if returned) and "
    "the link, stating the period label verbatim and mentioning any "
    "unmatched_filters.\n"
    "- To ANALYZE or COMPARE report CONTENTS (compare partners' ledgers, top "
    "debtors, aging breakdown, account balances): use `read_accounting_report` "
    "and base your analysis ONLY on the numbers it returns — never on "
    "assumptions. Present engine numbers as-is; when you compute a difference "
    "or ratio, show both operands. Include the report_link.\n"
    "- FUNCTIONALITY/NAVIGATION questions ('how do I X', 'where is X', 'how to "
    "enable X', 'does Cyllo have X'): call `describe_feature` first. Present "
    "menu paths EXACTLY as returned (e.g. Accounting / Configuration / Taxes) "
    "and link each as [Open](<link>) using the link verbatim. For settings, "
    "name the setting label, quote its help text if useful, and link Settings "
    "via settings_link. If the tool returns nothing relevant, say the feature "
    "was not found in this Cyllo install — NEVER answer functionality "
    "questions from memory or invent menu paths/setting names.\n"
    "- Lists, lookups, 'show/find/latest X': `search_records` with a domain filter.\n"
    "- 'How many X': `count_records`.\n"
    "- Totals, averages, breakdowns 'X by Y': `aggregate_records` (groupby supports "
    "date granularity like 'date_order:month').\n"
    "- Unsure of exact field names: call `get_model_fields(model)` first.\n"
    "- Only when the above cannot express the question (multi-model joins, "
    "subqueries): `analytic_record`.\n"
    "- Create / read / update / delete records: call `write_records` with the "
    "`model`, `action`, a `values` object, and `filters` (for read/update/"
    "delete). To change a field on a related line, target that line's model "
    "(filter through the parent) or set it inside the parent's x2many values. "
    "Writes are previewed and confirmed automatically — call it directly.\n"
    "- To SEND AN EMAIL: compose it yourself from the user's request (short "
    "specific subject; professional plain-text body with greeting and sign-off) "
    "and call `send_email`. It shows the user a preview and asks for "
    "confirmation automatically — call it directly, do not ask permission "
    "first. If the user then asks for changes, call it again with the revised "
    "draft. NEVER send emails via write_records.\n"
    "- To SEND A TEXT/SMS: same flow with `send_text`; keep the text "
    "SMS-short. NEVER via write_records.\n"
    "- To SEND AN INTERNAL MESSAGE to a colleague (another Cyllo user): same "
    "flow with `send_internal_message`; it is delivered in-app via Discuss. "
    "NEVER via write_records.\n"
    "- To visualize numeric results (comparisons, trends, distributions, breakdowns), "
    "call `render_chart` after you have the data. Then write your answer and put "
    "`[[chart]]` on its own line at the exact point where the chart belongs — that "
    "marker is what positions it, and it is removed before the user sees the text. "
    "Use it once, only when you actually rendered a chart. NEVER describe the "
    "chart's position in words ('the chart above', 'shown below'): you do not "
    "control where it lands, the marker does, so such wording will be wrong.\n"
    "- If a tool returns an error with suggestions, correct the input and retry once.\n"
    "- A null/empty result means zero records, not an error — answer confidently.\n"
    "- If a tool result contains `_truncated` or a `_hint` to narrow the query, "
    "it is a PARTIAL preview, not the full data: do not present it as complete. "
    "Narrow the query (add filters, a smaller period, or an aggregation) to get "
    "the specific rows, or tell the user the result was truncated and how many "
    "rows matched (see the `_*_total` field).\n\n"
    "Presentation rules:\n"
    "- When listing records, fetch informative fields (reference/name, partner, "
    "date, amount, state — whatever fits the model), not just display_name, and "
    "present them as a Markdown table with one column per field.\n"
    "- many2one values come back as [id, \"Name\"] — always display the name, "
    "never the raw pair or the id.\n"
    "- For line-level details of an order (products, quantities, prices), query the "
    "line model (e.g. sale.order.line with a domain on order_id) and include "
    "columns like product_id, quantity and price.\n"
    "- Link every record you mention using exactly this pattern: "
    "[<record name>](/web#id=<id>&model=<model>&view_type=form) — e.g. "
    "[S00023](/web#id=23&model=sale.order&view_type=form). You already have the id "
    "from the tool result; do not call extra tools just to build links, and never "
    "invent a different URL format.\n"
    "- ALL links (records and reports) must be RELATIVE, starting with /web# — "
    "NEVER prepend a protocol or domain (no 'https://...'). Copy report_link "
    "values byte-for-byte.\n\n"
    "Context blocks: a <cyllo_ui_context> block (when present) describes the "
    "screen the user is currently viewing (model, view, record). Use it to "
    "resolve references like 'this record', 'here' or 'this page', and as the "
    "default model when the user doesn't name one. If it names a record id, "
    "query that record directly instead of asking which record is meant. When "
    "the block lists the record's field values, answer from them directly; only "
    "read the record again for fields or related records (e.g. line items) it "
    "does not show."
)


@dataclass(frozen=True)
class AgentProfile:
    """One agent persona: prompt + tools (+ optional access gate)."""
    key: str
    system_prompt: str
    build_registry: Callable[[], ToolRegistry]
    requires_group: Optional[str] = None  # res.groups xmlid; server-side authority


DEFAULT_PROFILE = AgentProfile(
    key="default",
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    build_registry=build_default_registry,
)

# Studio profile lands in a later phase: same engine, studio prompt + tools,
# requires_group="base.group_system" (the group gating the Studio systray).
PROFILES = {
    "default": DEFAULT_PROFILE,
}


def resolve_profile(env, ui_context=None) -> AgentProfile:
    """
    Pick the profile for this turn from the UI context — deterministic.

    ``ui_context`` comes from the client (untrusted hint). Group membership
    is verified here; an unknown or unauthorized profile falls back to the
    default rather than erroring.
    """
    ui = ui_context if isinstance(ui_context, dict) else {}
    key = "studio" if ui.get("studio") else "default"
    profile = PROFILES.get(key)
    if profile is None:
        return DEFAULT_PROFILE
    if profile.requires_group and not env.user.has_group(profile.requires_group):
        _logger.info("[cyllo_ai] profile %r denied for uid=%s (missing %s); using default",
                     key, env.uid, profile.requires_group)
        return DEFAULT_PROFILE
    if profile is not DEFAULT_PROFILE:
        _logger.info("[cyllo_ai] profile %r resolved for uid=%s", key, env.uid)
    return profile
