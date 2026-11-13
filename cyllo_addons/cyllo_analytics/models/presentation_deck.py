# -*- coding: utf-8 -*-
"""An arranged presentation: slides, and what sits where on each one.

The existing ``dashboard.presentation`` is a TransientModel - right for
"generate a deck from this dashboard and show it now", wrong for a deck
somebody arranges once and reopens next month, because the vacuum deletes
transient records. These three models are the persistent side, and they
leave that quick-present path exactly as it is.

The layout is stored the way the dashboard already stores its own: x, y,
width and height per item, driven by GridStack. Reusing the shape rather
than inventing a second one means the editor can reuse the dashboard
editor's save/discard flow, and anyone who has read one screen can read
the other.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DashboardPresentationDeck(models.Model):
    """A saved, re-editable deck."""

    _name = "dashboard.presentation.deck"
    _description = "Presentation Deck"
    _order = "name, id"

    name = fields.Char(required=True, default="Untitled Presentation")
    dashboard_config_ids = fields.Many2many(
        "dashboard.config", "presentation_deck_dashboard_rel",
        "deck_id", "config_id", string="Dashboards",
        help="The dashboards this deck draws from. Every chart and every "
             "note on any of them can be put on a slide. A monthly pack "
             "rarely comes from one dashboard: sales, stock and cash each "
             "have their own, and the deck reporting on the month needs "
             "all three. The first is the one the deck takes its theme "
             "from. Left empty, every sheet is available.")
    user_id = fields.Many2one(
        "res.users", string="Owner", default=lambda self: self.env.user,
        ondelete="cascade")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True,
        index=True)

    slide_ids = fields.One2many(
        "dashboard.presentation.slide", "deck_id", string="Slides")
    slide_count = fields.Integer(compute="_compute_slide_count")

    theme = fields.Char()
    theme_json = fields.Json()
    style_json = fields.Json()
    auto_slide = fields.Boolean()
    auto_slide_time = fields.Integer(string="Auto Slide Duration")
    title_page = fields.Boolean()
    title_page_heading = fields.Char()
    title_page_subheading = fields.Char()

    def init(self):
        """Carry decks made before a deck could have several dashboards.

        The old column held one; Odoo leaves a dropped field's column in
        place, so it is still there to read from. Each deck that has no
        row in the new table yet gets one for the dashboard it had, and
        nobody loses a deck to the upgrade.

        Runs on every module update and is written to be idempotent: a
        deck already linked is skipped, so re-running cannot double a row
        or overwrite dashboards added since.
        """
        super().init()
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'dashboard_presentation_deck'
               AND column_name = 'dashboard_config_id'
        """)
        if not self.env.cr.fetchone():
            return
        self.env.cr.execute("""
            INSERT INTO presentation_deck_dashboard_rel (deck_id, config_id)
            SELECT deck.id, deck.dashboard_config_id
              FROM dashboard_presentation_deck deck
             WHERE deck.dashboard_config_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM presentation_deck_dashboard_rel rel
                    WHERE rel.deck_id = deck.id)
        """)
        if self.env.cr.rowcount:
            _logger.info(
                "cyllo_analytics: carried %s presentation deck(s) onto the "
                "dashboards field", self.env.cr.rowcount)

        self.env.cr.execute("""
            ALTER TABLE dashboard_presentation_deck
            ALTER COLUMN dashboard_config_id DROP NOT NULL
        """)

    def _primary_config(self):
        """The dashboard that answers when only one can.

        A theme is one theme and the editor opens against one dashboard,
        so the first of the list stands for the deck. Named rather than
        written inline twice, because "the first one" is a decision and
        the two places must not drift.
        """
        self.ensure_one()
        return self.dashboard_config_ids[:1]

    @api.model
    def decks_using_sheet(self, sheet_id):
        """Names of the decks that put this sheet on a slide.

        Read before hiding or deleting a sheet, so the confirmation can say
        which presentations lose a chart rather than leaving it to be found
        while presenting.
        """
        try:
            sheet_id = int(sheet_id)
        except (TypeError, ValueError):
            return []
        items = self.env["dashboard.presentation.item"].search([
            ("item_type", "=", "chart"),
            ("sheet_id", "=", sheet_id),
        ])
        return sorted(set(items.slide_id.deck_id.mapped("name")))

    @api.model
    def presentation_sources(self, deck_id=False, dashboard_id=False):
        """The charts and notes a deck may put on its slides.

        Answered here rather than by the editor reading dashboard.config
        itself, because "which dashboards" stopped being one id: a deck can
        now draw from several, and the union belongs on the record that
        knows about them. A deck being started has no record yet, so the
        dashboard it is being started from is accepted instead.

        Each chart carries the name of a dashboard holding it, so a picker
        listing several sources can say where a chart came from. A chart on
        two dashboards names one of them - which one is not worth
        establishing to label a row in a list.
        """
        Config = self.env["dashboard.config"]
        deck = self.browse(deck_id).exists() if deck_id else self.browse()
        configs = deck.dashboard_config_ids if deck else Config.browse(
            dashboard_id).exists()
        if not configs:
            all_sheets = self.env["dashboard.sheet"].search([])
            all_notes = self.env["dashboard.sheet.note"].search([], order="id desc")
            # A deck with no dashboard of its own still needs to know which
            # dashboard a sheet sits on, or its charts could never be shown
            # the way that dashboard shows them.
            home = {}
            for config in self.env["dashboard.config"].search([]):
                for sheet in config.sheet_ids:
                    home.setdefault(sheet.id, (config.id, config.name))
            return {
                "sheets": [{
                    "id": sheet.id,
                    "name": sheet.name,
                    "type": sheet.type,
                    "dashboard": home.get(sheet.id, (False, ""))[1],
                    "dashboard_id": home.get(sheet.id, (False, ""))[0],
                } for sheet in all_sheets],
                "notes": [{
                    "id": note.id,
                    "sheet_id": (note.sheet_id.id, note.sheet_id.name)
                                if note.sheet_id else False,
                    "note_html": note.note_html or "",
                } for note in all_notes],
                "source_count": 0,
            }

        owner = {}
        owner_id = {}
        for config in configs:
            for sheet in config.sheet_ids:
                owner.setdefault(sheet.id, config.name)
                owner_id.setdefault(sheet.id, config.id)

        sheets = configs.sheet_ids
        notes = self.env["dashboard.sheet.note"].search(
            [("config_id", "in", configs.ids)], order="id desc")
        return {
            "sheets": [{
                "id": sheet.id,
                "name": sheet.name,
                "type": sheet.type,
                "dashboard": owner.get(sheet.id, ""),
                "dashboard_id": owner_id.get(sheet.id, False),
            } for sheet in sheets],
            "notes": [{
                "id": note.id,
                "sheet_id": (note.sheet_id.id, note.sheet_id.name)
                            if note.sheet_id else False,
                "note_html": note.note_html or "",
            } for note in notes],
            "source_count": len(configs),
        }

    @api.depends("slide_ids")
    def _compute_slide_count(self):
        counts = dict(self.env["dashboard.presentation.slide"]._read_group(
            [("deck_id", "in", self.ids)], ["deck_id"], ["__count"]))
        for deck in self:
            deck.slide_count = counts.get(deck, 0)

    def action_open_editor(self):
        """Open this deck in the arranging editor."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_analytics.action_presentation_editor")
        action["context"] = {
            "deck_id": self.id,
            "dashboard_id": self._primary_config().id,
        }
        return action

    def get_presentation_slides(self):
        """The deck as the player needs it: slides in order, each with its
        boxes and where they sit.

        Chart data is deliberately NOT included. The player already fetches
        it through dashboard.sheet.fetch_sheet_data, and a second path that
        prepared it here would be a second thing to keep correct.
        """
        self.ensure_one()
        available_sheets = (set(self.dashboard_config_ids.sheet_ids.ids)
                            if self.dashboard_config_ids else None)
        slides = []
        for slide in self.slide_ids.sorted(lambda s: (s.sequence, s.id)):
            items = []
            for item in slide.item_ids.sorted(lambda i: (i.y, i.x, i.id)):
                if (item.item_type == "chart" and available_sheets is not None
                        and item.sheet_id.id not in available_sheets):
                    continue
                items.append({
                    "id": item.id,
                    "item_type": item.item_type,
                    "sheet_id": item.sheet_id.id or False,
                    "use_dashboard_filters": item.use_dashboard_filters,
                    "config_id": item.config_id.id or False,
                    "html": (item.note_id.note_html if item.item_type == "note"
                             else item.content_html) or "",
                    "has_image": bool(item.image),
                    "image_fit": item.image_fit or "contain",
                    "text_align": item.text_align or "left",
                    "text_color": item.text_color or "",
                    "x": item.x, "y": item.y,
                    "w": max(item.w, 1), "h": max(item.h, 1),
                })
            slides.append({
                "id": slide.id,
                "name": slide.name,
                "heading": slide.heading or "",
                "subheading": slide.subheading or "",
                "heading_align": slide.heading_align or "left",
                "heading_color": slide.heading_color or "",
                "subheading_color": slide.subheading_color or "",
                "items": items,
            })
        theme_json = self.theme_json or {}
        theme_name = self.theme
        if not theme_json.get("theme_color_ids"):
            theme = self._primary_config().theme_id
            if theme:
                theme_json = theme.read_theme()
                theme_name = theme_name or theme.name

        return {
            "name": self.name,
            "slides": slides,
            "theme": theme_name or False,
            "theme_json": theme_json,
            "auto_slide": self.auto_slide,
            "auto_slide_time": self.auto_slide_time,
            "title_page": self.title_page,
            "title_page_heading": self.title_page_heading or self.name,
            "title_page_subheading": self.title_page_subheading or "",
        }

    def action_present(self):
        """Play this deck, arranged as it was saved."""
        self.ensure_one()
        if not self.slide_ids.item_ids:
            raise UserError(_(
                "This presentation has nothing on it yet. Open the editor and "
                "add a chart or a note first."))
        return {
            "type": "ir.actions.client",
            "tag": "presentation_maker",
            "target": "current",
            "context": {"deck_id": self.id},
        }

    def action_add_slide(self):
        """A new empty slide at the end."""
        self.ensure_one()
        last = max(self.slide_ids.mapped("sequence"), default=0)
        return self.env["dashboard.presentation.slide"].create({
            "deck_id": self.id,
            "sequence": last + 10,
            "name": _("Slide %s", self.slide_count + 1),
        }).id


class DashboardPresentationSlide(models.Model):
    """One slide, and the order it appears in."""

    _name = "dashboard.presentation.slide"
    _description = "Presentation Slide"
    _order = "sequence, id"

    deck_id = fields.Many2one(
        "dashboard.presentation.deck", required=True, ondelete="cascade",
        index=True)
    sequence = fields.Integer(default=10, index=True)
    name = fields.Char(
        default="Slide",
        help="What this slide is called in the editor's slide list. Not shown "
             "to the audience - the heading below is.")
    heading = fields.Char(
        string="Heading",
        help="The title across the top of the slide, as the audience sees it.")
    subheading = fields.Char(
        string="Sub-heading",
        help="A line under the heading, for the period or the qualifier that "
             "the heading would be clumsy carrying.")
    heading_align = fields.Selection(
        [("left", "Left"), ("center", "Centre"), ("right", "Right")],
        default="left", required=True,
        help="Which way the heading and its sub-heading are set on the slide.")
    heading_color = fields.Char(
        help="Colour of the heading, as CSS. Empty means the theme's own "
             "text colour, which is what most slides should use.")
    subheading_color = fields.Char(
        help="Colour of the sub-heading. Empty follows the heading.")
    item_ids = fields.One2many(
        "dashboard.presentation.item", "slide_id", string="Items")

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals.setdefault("name", _("%s (copy)", self.name))
        return vals_list


class DashboardPresentationItem(models.Model):
    """A chart or a note, placed on a slide.

    Charts and notes are the same kind of thing here - a rectangle with a
    position - which is what lets one grid drag and resize both. Keeping
    notes in a separate structure would mean two layout systems that have
    to agree, and they would eventually stop agreeing.
    """

    _name = "dashboard.presentation.item"
    _description = "Presentation Item"
    _order = "slide_id, y, x, id"

    slide_id = fields.Many2one(
        "dashboard.presentation.slide", required=True, ondelete="cascade",
        index=True)
    item_type = fields.Selection(
        [("chart", "Chart"), ("note", "Note"), ("text", "Text"),
         ("image", "Image")],
        required=True, default="chart")

    sheet_id = fields.Many2one(
        "dashboard.sheet", string="Chart", ondelete="cascade",
        help="The chart shown in this box. Deliberately not restricted to "
             "the deck's own dashboard at the database level - a sheet may "
             "be moved between dashboards, and a deck that raised an error "
             "on open would be worse than one showing a chart from "
             "elsewhere.")
    use_dashboard_filters = fields.Boolean(
        string="As Shown On Dashboard", default=False,
        help="Off - the default - draws the chart from the sheet itself, "
             "exactly as the sheet editor shows it. On, the chart is drawn "
             "the way the dashboard shows it, with that dashboard's global "
             "filters applied. Chosen per box, because one slide may want "
             "the whole picture next to the filtered cut of it.")
    config_id = fields.Many2one(
        "dashboard.config", string="Filter Source", ondelete="set null",
        help="Which dashboard's global filters to pass the chart through "
             "when 'As Shown On Dashboard' is on. A sheet can sit on more "
             "than one dashboard and each carries its own filters, so the "
             "one the chart was picked from is recorded rather than guessed "
             "again later.")

    note_id = fields.Many2one(
        "dashboard.sheet.note", string="Saved Note", ondelete="set null",
        help="An existing note, so the deck shows what was actually written "
             "against that chart rather than a copy that drifts from it.")
    content_html = fields.Html(
        string="Text", sanitize=True,
        help="Free text written straight onto the slide, for the commentary "
             "that belongs to the deck rather than to any one chart.")

    image = fields.Image(
        string="Image",
        help="A picture placed straight on the slide - a logo, a photograph, "
             "or a table captured from elsewhere. Stored as an attachment, so "
             "it is served by URL rather than carried in every read of the "
             "slide.")

    text_align = fields.Selection(
        [("left", "Left"), ("center", "Centre"), ("right", "Right")],
        default="left", required=True,
        help="Which way a text box is set. Charts and images ignore it.")
    text_color = fields.Char(
        help="Colour of a text box, as CSS. Empty means the theme's own "
             "text colour.")

    image_fit = fields.Selection(
        [("contain", "Fit"), ("cover", "Fill"), ("fill", "Stretch")],
        default="contain", required=True,
        help="How the picture uses its box. Fit shows all of it and leaves "
             "space at the sides; Fill covers the box and crops the "
             "overflow; Stretch uses the whole box and distorts the picture. "
             "Fit is the default because losing the edges of a chart or a "
             "table captured from elsewhere is worse than empty space.")

    # GridStack's own units: columns across, rows down.
    x = fields.Integer(default=0)
    y = fields.Integer(default=0)
    w = fields.Integer(default=6)
    h = fields.Integer(default=4)

    @api.constrains("item_type", "sheet_id", "note_id", "content_html")
    def _check_item_has_content(self):
        """An empty box on a slide is a bug someone has to hunt for later."""
        for item in self:
            if item.item_type == "chart" and not item.sheet_id:
                raise ValidationError(_("A chart box needs a chart."))
            if item.item_type == "note" and not item.note_id:
                raise ValidationError(_("A note box needs a note."))
            if item.item_type == "image" and not item.image:
                raise ValidationError(_("An image box needs a picture."))

    @api.constrains("w", "h")
    def _check_size(self):
        for item in self:
            if item.w < 1 or item.h < 1:
                raise ValidationError(_("An item must be at least one cell."))

    @api.model
    def save_layout(self, slide_id, children):
        """Persist a slide's arrangement after a drag or a resize.

        Mirrors dashboard.config.save_position, including its hard-won
        detail: GridStack omits w and h from save() when they equal its
        internal default of 1, so a missing value means 1 - not "unset".
        Defaulting to anything larger silently grows every item somebody
        shrank to a single row.
        """
        slide = self.env["dashboard.presentation.slide"].browse(slide_id)
        slide.check_access_rights("write")
        slide.check_access_rule("write")
        items = {item.id: item for item in slide.item_ids}
        for child in children or []:
            item = items.get(int(child.get("id", 0)))
            if not item:
                continue
            item.write({
                "x": child.get("x") or 0,
                "y": child.get("y") or 0,
                "w": max(child.get("w") or 1, 1),
                "h": max(child.get("h") or 1, 1),
            })
        return True

    @api.model
    def reorder_slides(self, deck_id, slide_ids):
        """Renumber slides to the order they were dragged into."""
        deck = self.env["dashboard.presentation.deck"].browse(deck_id)
        deck.check_access_rights("write")
        deck.check_access_rule("write")
        Slide = self.env["dashboard.presentation.slide"]
        for position, slide_id in enumerate(slide_ids, start=1):
            slide = Slide.browse(slide_id)
            if slide.deck_id == deck:
                slide.sequence = position * 10
        return True
