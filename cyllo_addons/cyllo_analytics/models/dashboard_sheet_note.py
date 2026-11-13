# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_datetime

_logger = logging.getLogger(__name__)


class DashboardSheetNote(models.Model):
    """A note written against one chart, on one dashboard, under one set of filters.

    A note used to be a single field on the sheet, which made it say one thing
    forever. But a chart means different things through different filters: what
    is worth recording about June is not what is worth recording about the year,
    and the same chart reused on two dashboards is being read by two different
    audiences. Keying the note to the sheet, the dashboard and the filters in
    force lets each of those carry its own commentary.
    """
    _name = "dashboard.sheet.note"
    _description = "Dashboard Sheet Note"
    _order = "write_date desc, id desc"

    sheet_id = fields.Many2one(
        "dashboard.sheet", string="Sheet", required=True, ondelete="cascade",
        index=True)
    config_id = fields.Many2one(
        "dashboard.config", string="Dashboard", required=True, ondelete="cascade",
        index=True)

    # The fingerprint of the filters this note was written under. Stored rather
    # than recomputed so it can be indexed and matched with a plain search, and
    # kept beside the readable values because a fingerprint tells a person
    # nothing when they are looking at the note later.
    filter_key = fields.Char(
        string="Filter Fingerprint", required=True, default="", index=True)
    filter_values = fields.Text(
        string="Filters In Force",
        help="The global filters the note was written under, as they were.")

    note_html = fields.Html(string="Note", sanitize=True)
    note_ratio = fields.Integer(
        string="Note Split", default=60,
        help="How much of the slide width the chart takes when the note is shown "
             "beside it, as a percentage.")

    # write_date already records when a note was last saved; this exposes it
    # under a name the dashboard can show without explaining Odoo's plumbing.
    saved_on = fields.Datetime(
        string="Last Saved", compute="_compute_saved_on", store=False)

    _sql_constraints = [
        # One note per chart, per dashboard, per filter combination. Without
        # this a second save would silently make a duplicate and the reader
        # would see whichever happened to be found first.
        ("unique_note_per_context",
         "unique(sheet_id, config_id, filter_key)",
         "A note already exists for this chart on this dashboard under these filters."),
    ]

    @api.depends("write_date")
    def _compute_saved_on(self):
        for note in self:
            note.saved_on = note.write_date

    @api.constrains("note_ratio")
    def _check_note_ratio(self):
        """Keep the split usable: neither pane may be squeezed to nothing."""
        for note in self:
            if note.note_ratio and not 25 <= note.note_ratio <= 80:
                raise ValidationError(_(
                    "The chart must take between 25%% and 80%% of the slide."))

    def init(self):
        """Carry notes written before this model existed into it.

        A note used to live in dashboard.sheet.note_html, one per sheet. Those
        are filed here under the empty filter key - they were written with no
        particular filter in mind - once for each dashboard the sheet appears
        on, so nobody loses commentary to the upgrade. Runs on every module
        update and is deliberately idempotent: a sheet already carrying a note
        row is left alone, so re-running cannot duplicate or overwrite.
        """
        super().init()
        Sheet = self.env["dashboard.sheet"]
        if "note_html" not in Sheet._fields:
            return
        legacy = Sheet.sudo().search([("note_html", "!=", False)])
        if not legacy:
            return
        Config = self.env["dashboard.config"].sudo()
        values = []
        for sheet in legacy:
            for config in Config.search([("sheet_ids", "in", sheet.id)]):
                if self.sudo().search_count([
                        ("sheet_id", "=", sheet.id),
                        ("config_id", "=", config.id)]):
                    continue
                values.append({
                    "sheet_id": sheet.id,
                    "config_id": config.id,
                    "filter_key": "",
                    "note_html": sheet.note_html,
                    "note_ratio": sheet.note_ratio or 60,
                })
        if values:
            self.sudo().create(values)
            _logger.info(
                "cyllo_analytics: carried %s sheet note(s) into "
                "dashboard.sheet.note", len(values))

    # ------------------------------------------------------------------
    # Matching a note to what is on screen
    # ------------------------------------------------------------------
    @api.model
    def build_filter_key(self, filters):
        """A stable fingerprint for one set of global filter values.

        Two dashboards showing the same period must land on the same key, so the
        values are sorted and the empty ones dropped: a filter left blank is not
        a filter, and treating it as one would file the note under a context
        nobody can return to. JSON with fixed separators keeps the key identical
        across Python versions and across whatever order the client sent.
        """
        if not isinstance(filters, dict):
            return ""
        meaningful = {
            str(code): filters[code]
            for code in sorted(filters)
            if filters[code] not in (None, False, "", [])
        }
        if not meaningful:
            return ""
        return json.dumps(meaningful, separators=(",", ":"), sort_keys=True,
                          default=str)

    @api.model
    def note_for(self, sheet_id, config_id, filters=None):
        """The note written for this chart, dashboard and filter combination.

        Returns an empty dict when nothing has been written yet, which is what
        tells the dialog to open blank rather than showing somebody else's
        commentary against the wrong period.
        """
        if not sheet_id or not config_id:
            return {}
        note = self.search([
            ("sheet_id", "=", int(sheet_id)),
            ("config_id", "=", int(config_id)),
            ("filter_key", "=", self.build_filter_key(filters)),
        ], limit=1)
        if not note:
            return {}
        return {
            "id": note.id,
            "note_html": note.note_html or "",
            "note_ratio": note.note_ratio or 60,
            "saved_on": fields.Datetime.to_string(note.write_date),
            "filter_values": note.filter_values or "",
        }

    @api.model
    def notes_for(self, sheet_ids, config_id, filters=None):
        """Every note matching these charts under one dashboard and filter set.

        Returned keyed by sheet id so the presentation can build its slides in
        one call rather than one per chart, which on a dashboard of twenty
        charts is twenty round-trips before the deck can open.
        """
        if not sheet_ids or not config_id:
            return {}
        notes = self.search([
            ("sheet_id", "in", [int(sid) for sid in sheet_ids]),
            ("config_id", "=", int(config_id)),
            ("filter_key", "=", self.build_filter_key(filters)),
        ])
        return {
            str(note.sheet_id.id): {
                "note_html": note.note_html or "",
                "note_ratio": note.note_ratio or 60,
                "saved_on": fields.Datetime.to_string(note.write_date),
            }
            for note in notes
        }

    @api.model
    def _readable_filters(self, note):
        """The filters a note was written under, as a person would say them."""
        try:
            values = json.loads(note.filter_values or "{}")
        except (TypeError, ValueError):
            values = {}
        parts = ["%s: %s" % (code, values[code])
                 for code in sorted(values) if values[code]]
        return " \u00b7 ".join(parts) if parts else _("no filters applied")

    @api.model
    def notes_history(self, sheet_id, config_id=None, filters=None):
        """Every note written against one chart, newest first.

        A note is keyed to its dashboard and to the filters in force, so one
        chart accumulates several: what was worth saying about June, what was
        worth saying about the year, what the same chart means to the audience
        of another dashboard. Editing one of them shows only that one, and that
        is exactly the moment somebody wants to see the others - to avoid
        repeating a point, or to find what they wrote last quarter.

        Only notes on dashboards the reader may open are returned. The search
        on dashboard.config is what enforces that: record rules do the work, so
        this cannot drift out of step with them.
        """
        if not sheet_id:
            return []
        notes = self.search([("sheet_id", "=", int(sheet_id))])
        if not notes:
            return []
        readable = self.env["dashboard.config"].search(
            [("id", "in", notes.config_id.ids)])
        current_key = self.build_filter_key(filters)
        history = []
        for note in notes:
            if note.config_id not in readable:
                continue
            history.append({
                "id": note.id,
                "note_html": note.note_html or "",
                "filter_summary": self._readable_filters(note),
                "dashboard": note.config_id.name or "",
                # Both dates, because they answer different questions: when the
                # point was first made, and whether it has been revisited since.
                "added_on": format_datetime(self.env, note.create_date),
                "edited_on": (
                    format_datetime(self.env, note.write_date)
                    if note.write_date and note.create_date
                    and (note.write_date - note.create_date).total_seconds() > 60
                    else False),
                # Which of them is the one open in the editor, so the reader is
                # not left comparing a list against their own memory.
                "is_current": (
                    config_id and note.config_id.id == int(config_id)
                    and note.filter_key == current_key),
            })
        return history

    @api.model
    def _has_content(self, note_html):
        """Whether an editor's output holds anything a reader would see.

        An emptied editor yields "<p><br></p>", which is markup but not content.
        Storing it would keep drawing an empty note beside the chart for ever.
        """
        text = re.sub(r"<[^>]*>", "", note_html or "")
        return bool(text.replace("&nbsp;", "").strip())

    @api.model
    def save_ratio(self, sheet_id, config_id, filters, note_ratio):
        """Remember how the reader split a chart and its note.

        Written only onto a note that already exists: the split is a
        property of the commentary beside the chart, and without a note
        there is nothing to sit beside. Silently doing nothing is right
        here - the divider cannot be dragged on a slide that has no note,
        so reaching this with none means the note was deleted in another
        tab, and inventing an empty one to hold a ratio would put a blank
        note back on the dashboard.
        """
        if not sheet_id or not config_id:
            return False
        note = self.search([
            ("sheet_id", "=", int(sheet_id)),
            ("config_id", "=", int(config_id)),
            ("filter_key", "=", self.build_filter_key(filters)),
        ], limit=1)
        if not note:
            return False
        note.note_ratio = int(note_ratio)
        return True

    @api.model
    def save_note(self, sheet_id, config_id, filters, note_html, note_ratio=None):
        """Write the note for this context, replacing whatever was there.

        An emptied note deletes the row rather than storing blank markup: an
        editor left empty yields "<p><br></p>", which would otherwise read as
        content for ever and keep drawing an empty note beside every chart.
        """
        if not sheet_id or not config_id:
            return {}
        sheet = self.env["dashboard.sheet"].browse(int(sheet_id)).exists()
        config = self.env["dashboard.config"].browse(int(config_id)).exists()
        if not sheet or not config:
            return {}
        # Read through the normal rules first: someone who cannot reach the
        # dashboard must not be able to write notes onto it. Two calls on
        # this version: check_access_rights asks whether the model may be
        # read at all, check_access_rule whether this record may be - the
        # single check_access() that does both arrived later.
        config.check_access_rights("read")
        config.check_access_rule("read")

        key = self.build_filter_key(filters)
        existing = self.search([
            ("sheet_id", "=", sheet.id),
            ("config_id", "=", config.id),
            ("filter_key", "=", key),
        ], limit=1)

        if not self._has_content(note_html):
            existing.unlink()
            return {}

        values = {
            "note_html": note_html,
            "filter_values": json.dumps(filters or {}, default=str),
        }
        if note_ratio:
            values["note_ratio"] = note_ratio
        if existing:
            existing.write(values)
            note = existing
        else:
            note = self.create(dict(
                values, sheet_id=sheet.id, config_id=config.id, filter_key=key))
        return self.note_for(sheet.id, config.id, filters)
