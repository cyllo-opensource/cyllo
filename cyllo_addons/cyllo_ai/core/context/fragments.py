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
Concrete context fragments.

Base scope: the two most useful ambient signals — who the user is and which
company scope they're in. More fragments (active screen/record, permissions,
locale) plug in here following the same pattern.
"""
import json
from datetime import date

from .fragment import ContextFragment

# Chart-explain context (dashboard "Explain with AI" flow) — bounded so the
# chart's data doesn't blow up the prompt on every follow-up turn.
CHART_MAX_ROWS = 40
CHART_MAX_CHARS = 3500

# Quick-dashboard builder context — the proposed-chart cards the user is
# curating in the chat, so the agent can reference and edit them by id.
QD_MAX_CARDS = 30

# Current-record snapshot tuning (Option D): a bounded, eager dump of the
# record's main field values so the agent can answer about "this record"
# without a tool round-trip. Deeper data (lines, related docs, omitted fields)
# is still read on demand.
SNAPSHOT_MAX_FIELDS = 25
SNAPSHOT_VALUE_CHARS = 150
# Audit/chatter/technical noise that adds tokens without helping answers.
SNAPSHOT_SKIP_FIELDS = frozenset({
    'id', 'display_name', 'create_uid', 'create_date', 'write_uid',
    'write_date', '__last_update', 'access_token', 'access_url',
})
SNAPSHOT_SKIP_PREFIXES = ('message_', 'activity_', '__')


class DateContextFragment(ContextFragment):
    """Today's date — without it the model dates 'current year/month' from its
    training data (e.g. 2023) when building domains."""

    marker = "cyllo_datetime"

    def __init__(self, env):
        self.env = env

    def body(self) -> str:
        today = date.today()
        return f"today: {today.isoformat()} ({today.strftime('%A')})"


class UserContextFragment(ContextFragment):
    """Identity of the requesting user."""

    marker = "cyllo_user_context"

    def __init__(self, env):
        self.env = env

    def body(self) -> str:
        user = self.env.user
        return (
            f"user_id: {user.id}\n"
            f"name: {user.name}\n"
            f"login: {user.login}\n"
            f"lang: {user.lang or 'en_US'}\n"
            f"tz: {user.tz or 'UTC'}"
        )


class CompanyContextFragment(ContextFragment):
    """Active company scope for multi-company data isolation."""

    marker = "cyllo_company_context"

    def __init__(self, env, company_ids=None):
        self.env = env
        self.company_ids = company_ids or env.company.ids

    def body(self) -> str:
        companies = self.env['res.company'].browse(self.company_ids)
        names = ", ".join(f"{c.id}:{c.name}" for c in companies if c.exists())
        return (
            f"allowed_company_ids: {self.company_ids}\n"
            f"companies: {names}\n"
            f"current_company: {self.env.company.id}:{self.env.company.name}"
        )


class UIContextFragment(ContextFragment):
    """
    Where the user currently is in the web client — resolves situated
    references ("this record", "here") and gives tool calls a default model.

    The ui_context dict comes from the client (untrusted): every value is
    validated before rendering — model against the registry, view_type
    against a whitelist, res_id as a positive int. The record name is read
    as the requesting user, so ir.rules apply.
    """

    marker = "cyllo_ui_context"

    VIEW_TYPES = {"form", "list", "tree", "kanban", "calendar", "pivot",
                  "graph", "activity", "map", "gantt"}

    def __init__(self, env, ui_context=None):
        self.env = env
        self.ui = ui_context if isinstance(ui_context, dict) else {}

    def body(self) -> str:
        lines = []
        model = self.ui.get("model")
        if isinstance(model, str) and model in self.env:
            desc = self.env[model]._description or model
            screen = f"current screen: {desc} ({model})"
            view = self.ui.get("view_type")
            if isinstance(view, str) and view in self.VIEW_TYPES:
                screen += f", {view} view"
            res_id = self.ui.get("res_id")
            snapshot = ""
            if isinstance(res_id, int) and res_id > 0:
                screen += f", record id {res_id}"
                try:
                    rec = self.env[model].browse(res_id)
                    if rec.exists():
                        screen += f' ("{rec.display_name[:80]}")'
                        snapshot = self._record_snapshot(rec)
                except Exception:
                    pass  # no access / no name — id alone is still useful
            lines.append(screen)
            if snapshot:
                lines.append(snapshot)
        if self.ui.get("studio"):
            lines.append("studio: active")
        return "\n".join(lines)

    def _record_snapshot(self, rec) -> str:
        """A compact, access-checked dump of the current record's main field
        values, so the agent can answer about it without a tool round-trip.

        Read as the requesting user (ir.rules and field-level security apply).
        Bounded in field count and value length; many2one shown as names,
        x2many as counts; binary/html/empty/technical fields are skipped.
        Anything not shown (other fields, line items, related records) is read
        on demand via the tools.
        """
        out = []
        for name, field in rec._fields.items():
            if len(out) >= SNAPSHOT_MAX_FIELDS:
                break
            if not field.store or field.type == 'binary':
                continue
            if name in SNAPSHOT_SKIP_FIELDS or name.startswith(SNAPSHOT_SKIP_PREFIXES):
                continue
            try:
                val = rec[name]
                if field.type == 'many2one':
                    sval = val.display_name if val else None
                elif field.type in ('one2many', 'many2many'):
                    n = len(val)
                    if not n:
                        continue
                    sval = f"{n} record(s) ({field.comodel_name})"
                elif field.type == 'html':
                    continue  # markup blob — not useful as plain context
                elif field.type == 'selection':
                    try:  # prefer the human label ("Sale Order"), else raw value
                        sval = dict(field._description_selection(self.env)).get(val, val)
                    except Exception:
                        sval = val
                else:
                    sval = val
            except Exception:
                continue  # no access to this field, or compute error — skip it
            if sval in (None, False, ''):
                continue
            sval = str(sval)
            if len(sval) > SNAPSHOT_VALUE_CHARS:
                sval = sval[:SNAPSHOT_VALUE_CHARS] + '…'
            out.append(f"- {name}: {sval}")
        if not out:
            return ""
        return ("record fields (current values; read other fields or related "
                "records such as line items with the tools if needed):\n"
                + "\n".join(out))


class MentionContextFragment(ContextFragment):
    """Screens the user explicitly @ mentioned in the composer — pulling in a
    model + its default view even from a completely unrelated screen, unlike
    UIContextFragment which only ever describes where the user currently is.

    The payload comes from the client (untrusted): each entry's model is
    checked against the registry and view_type against the same whitelist
    UIContextFragment uses, so nothing unvalidated reaches the prompt.
    """

    marker = "cyllo_mentions"

    #: Bounded so a chat full of mentions can't blow up every turn's prompt.
    MAX_ITEMS = 5

    def __init__(self, env, ui_context=None):
        self.env = env
        mentions = (ui_context or {}).get("mentions") if isinstance(ui_context, dict) else None
        self.mentions = mentions if isinstance(mentions, list) else []

    def body(self) -> str:
        lines = []
        for m in self.mentions[:self.MAX_ITEMS]:
            if not isinstance(m, dict):
                continue
            model = m.get("model")
            if not isinstance(model, str) or model not in self.env:
                continue
            desc = self.env[model]._description or model
            name = m.get("name") or desc
            entry = f'- "{name}" — {desc} ({model})'
            view_type = m.get("view_type")
            if isinstance(view_type, str) and view_type in UIContextFragment.VIEW_TYPES:
                entry += f", {view_type} view"
            res_id = m.get("res_id")
            if isinstance(res_id, int) and res_id > 0:
                # Re-read the name as the requesting user rather than trust
                # the client's label — same reasoning as UIContextFragment's
                # record name (ir.rules / field security must apply).
                try:
                    rec = self.env[model].browse(res_id)
                    if rec.exists():
                        entry += f', pinned to record id {res_id} ("{rec.display_name[:80]}")'
                except Exception:
                    pass  # no access — the model+view context above still stands
            lines.append(entry)
        if not lines:
            return ""
        return (
            "The user explicitly referenced these screens with @ in their "
            "message — they may be different from wherever the user currently "
            "is, and are the subject of the request, NOT ambient background. "
            "When a mention is pinned to a record id, that IS the record the "
            "user means for any follow-up field/detail question (e.g. \"email?\", "
            "\"phone?\") — call the read tool for that model/id directly instead "
            "of asking which record they meant:\n" + "\n".join(lines))


class ChartContextFragment(ContextFragment):
    """The chart the user is currently discussing (the dashboard "Explain with
    AI" flow) — its metadata and data rows, so the agent can explain it and
    answer follow-ups directly, without a tool round-trip.

    The payload comes from the client (untrusted); it is descriptive only and
    read as-is. Bounded in rows and length so it stays cheap across turns.
    """

    marker = "cyllo_chart"

    def __init__(self, env, ui_context=None):
        self.env = env
        chart = (ui_context or {}).get("chart") if isinstance(ui_context, dict) else None
        self.chart = chart if isinstance(chart, dict) else None

    def body(self) -> str:
        c = self.chart
        if not c:
            return ""
        lines = []
        title = c.get("title")
        if title:
            lines.append(f'title: "{title}"')
        ctype = c.get("chart_type") or c.get("type")
        if ctype:
            lines.append(f"chart type: {ctype}")
        columns = c.get("columns")
        if isinstance(columns, dict) and columns:
            cols = ", ".join(f"{k}={v}" for k, v in columns.items())
            lines.append(f"columns (key=label): {cols}")
        rows = c.get("rows")
        if isinstance(rows, list) and rows:
            capped = rows[:CHART_MAX_ROWS]
            dumped = json.dumps(capped, default=str)[:CHART_MAX_CHARS]
            lines.append(f"data ({len(capped)} of {len(rows)} rows): {dumped}")
        if not lines:
            return ""
        lines.append(
            "When the user asks about this chart, explain it directly from the "
            "data above — key trends, notable highs/lows, anomalies, and the "
            "main takeaways — in clear language for a non-technical audience. "
            "Do NOT call tools to re-fetch it.")
        return "\n".join(lines)


class QuickDashboardContextFragment(ContextFragment):
    """The quick-dashboard builder the user is curating in the chat — its picked
    tables, proposed chart cards (id, title, current type, the types allowed for
    that data, and whether each is kept), and the pending name.

    This lets the agent edit the builder conversationally ("make the customer
    chart a pie", "drop the vendor one") by referencing a card's id. Descriptive
    only; comes from the client and is bounded so it stays cheap across turns.
    """

    marker = "cyllo_quick_dashboard"

    def __init__(self, env, ui_context=None):
        self.env = env
        qd = (ui_context or {}).get("quick_dashboard") if isinstance(ui_context, dict) else None
        self.qd = qd if isinstance(qd, dict) else None

    def body(self) -> str:
        qd = self.qd
        if not qd:
            return ""
        lines = ["The user is building a dashboard in the chat (the card panel)."]
        tables = qd.get("tables") or []
        if tables:
            lines.append("tables: " + ", ".join(
                f'{t.get("name")} ({t.get("model")})' for t in tables if isinstance(t, dict)))
        name = qd.get("name")
        if name:
            lines.append(f'dashboard name: "{name}"')
        cards = qd.get("cards") or []
        if cards:
            lines.append("proposed charts — id: \"title\" [current type; allowed types] kept?:")
            for card in cards[:QD_MAX_CARDS]:
                if not isinstance(card, dict):
                    continue
                allowed = ", ".join(card.get("allowed_chart_types") or [])
                kept = "kept" if card.get("selected") else "dropped"
                lines.append(
                    f'- {card.get("id")}: "{card.get("title")}" '
                    f'[{card.get("chart_type")}; allowed: {allowed}] {kept}')
        lines.append(
            "To change ANY of this, call edit_quick_dashboard — set a chart's type "
            "(only to one of its allowed types), keep/drop a chart, add/remove a "
            "table, rename the dashboard, or create it. Reference a chart by its "
            "id, matched from the title the user names; if two titles are close, "
            "ASK which one rather than guessing.")
        return "\n".join(lines)


class LiveDashboardContextFragment(ContextFragment):
    """The CREATED dashboard the user is currently viewing — its saved charts
    (sheet id, name, current type, the types allowed for each). Lets the agent
    edit the live dashboard by chat: change a chart's type, drop a chart, add a
    chart, or rename it (via edit_dashboard). Distinct from the pre-create
    builder above. Descriptive only; comes from the client, bounded.
    """

    marker = "cyllo_live_dashboard"

    def __init__(self, env, ui_context=None):
        self.env = env
        d = (ui_context or {}).get("dashboard") if isinstance(ui_context, dict) else None
        self.d = d if isinstance(d, dict) else None

    def body(self) -> str:
        d = self.d
        if not d or not d.get("config_id"):
            return ""
        lines = [f'The user is viewing a saved dashboard (config id {d.get("config_id")}).']
        name = d.get("name")
        if name:
            lines.append(f'dashboard name: "{name}"')
        sheets = d.get("sheets") or []
        if sheets:
            lines.append('charts on it — sheet_id: "name" [current type; allowed types] (model):')
            for s in sheets[:QD_MAX_CARDS]:
                if not isinstance(s, dict):
                    continue
                allowed = ", ".join(s.get("allowed_chart_types") or [])
                lines.append(
                    f'- {s.get("id")}: "{s.get("name")}" '
                    f'[{s.get("type")}; allowed: {allowed}] ({s.get("model")})')
        lines.append(
            "To change THIS saved dashboard, call edit_dashboard — set a chart's "
            "type (only an allowed type), drop a chart, add a chart (name the "
            "table + what to chart), or rename it. Reference an existing chart by "
            "its sheet_id, matched from the name the user says; if two are close, "
            "ASK which one. Changes save and the dashboard refreshes immediately.")
        return "\n".join(lines)
