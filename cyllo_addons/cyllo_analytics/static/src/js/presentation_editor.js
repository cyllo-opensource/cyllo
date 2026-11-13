/** @odoo-module **/
/**
 * The presentation editor: slides on the left, a grid canvas on the right.
 *
 * Charts, saved notes and free text are all the same thing here - a box with
 * a position - which is what lets one GridStack instance drag and resize all
 * three. Notes kept in their own structure would mean two layout systems that
 * have to agree with each other, and they would eventually stop agreeing.
 *
 * The grid setup deliberately mirrors edit_dashboard.js, down to the
 * moveNode cycle-breaker: the same collision recursion bites here, and a
 * second, subtly different copy of that fix would be worse than an obvious
 * one.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { StackItem, StackKpiItem, StackTableItem } from "./stack_item";
import { resolveMeasures } from "./chart_maker";
import { _t } from "@web/core/l10n/translation";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { KPI_SHEET_FIELDS, kpiSettingsFromSheet, fetchSheetStyling } from "@cyllo_analytics/js/utils";

const { Component, useState, useRef, onMounted, onWillUnmount, status, markup } = owl;

const COLUMNS = 12;
const ROWS = 12;
const SLIDE_RATIO = 9 / 16;
const EDITOR_SESSION_KEY = "cy_presentation_editor";

export class PresentationEditor extends Component {
    static template = "cyllo_analytics.PresentationEditor";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.canvasRef = useRef("canvas");
        this.railRef = useRef("rail");
        this.saveContext = useSaveContext();
        useSortable({
            ref: this.railRef,
            elements: ".cy-pe-slide",
            cursor: "grabbing",
            placeholderClasses: ["cy-pe-slide-ghost"],
            onDrop: ({ element, previous }) => this.onSlideDropped(
                Number(element.dataset.slideId),
                previous ? Number(previous.dataset.slideId) : false,
            ),
        });

        const params = this.props.action?.context || this.props.action?.params || {};
        this.deckId = params.deck_id || false;
        this.dashboardId = params.dashboard_id || false;
        this.strayDashboardId = params.active_id || false;


        this.stackItems = {};
        this.state = useState({
            loading: true,
            deckName: "",
            slides: [],
            sourceCount: 0,
            activeSlideId: false,
            items: [],
            sheets: [],
            notes: [],
            dirty: false,
            picker: false,
            headingOn: false,
        });

        onMounted(() => this.load());
        onWillUnmount(() => {
            this.flushActiveText();
            this.teardownGrid();
        });
    }

    /**
     * Narrow a list of ids to the ones that really exist and this user may
     * read. The editor is opened with ids out of an action context, and a
     * refresh rebuilds that context from the URL — what comes back can be
     * stale, can belong to another model (active_id), or can be gone.
     */
    async _existingIds(model, ids) {
        const wanted = (Array.isArray(ids) ? ids : [ids]).filter(Boolean);
        if (!wanted.length) {
            return [];
        }
        try {
            return await this.orm.search(model, [["id", "in", wanted]]);
        } catch (err) {
            return [];
        }
    }

    /**
     * Decide which deck this editor is opening, before anything is created.
     *
     * Refreshing restores the client action without the context it was opened
     * with, so the deck id is gone and whatever `active_id` the URL carries
     * arrives in its place. Trusting that id and creating a deck against it
     * wrote a link row pointing at a dashboard that does not exist, which
     * Postgres refused on presentation_deck_dashboard_rel_config_id_fkey and
     * the user saw as a raw constraint dialog. Nothing here is taken on
     * trust: every id is confirmed against the database first.
     */
    async _resolveDeck() {
        [this.deckId] = await this._existingIds(
            "dashboard.presentation.deck", this.deckId);
        if (this.deckId) {
            return true;
        }
        [this.dashboardId] = await this._existingIds(
            "dashboard.config", this.dashboardId);
        if (this.dashboardId) {
            return true;
        }
        const remembered = this.saveContext.getKeyValue(EDITOR_SESSION_KEY) || {};
        [this.deckId] = await this._existingIds(
            "dashboard.presentation.deck", remembered.deck_id);
        if (this.deckId) {
            return true;
        }
        [this.dashboardId] = await this._existingIds(
            "dashboard.config", [remembered.dashboard_id, this.strayDashboardId]);
        return Boolean(this.dashboardId);
    }

    async load() {
        this.state.loading = true;
        try {
            if (!(await this._resolveDeck())) {
                this.notification.add(
                    _t("Open this from a dashboard: a presentation needs one to draw its charts from."),
                    { type: "warning" });
                return;
            }
            if (!this.deckId) {
                this.deckId = await this.orm.create("dashboard.presentation.deck", [{
                    name: _t("Untitled Presentation"),
                    dashboard_config_ids: [[6, 0, [this.dashboardId]]],
                }]).then((ids) => ids[0]);
            }
            const [deck] = await this.orm.read(
                "dashboard.presentation.deck", [this.deckId],
                ["name", "dashboard_config_ids", "slide_ids"]);
            this.state.deckName = deck.name;
            this.dashboardId = deck.dashboard_config_ids?.[0] || this.dashboardId;
            this.saveContext.saveToSession(
                EDITOR_SESSION_KEY,
                { deck_id: this.deckId, dashboard_id: this.dashboardId },
                true);

            await this.loadSlides();
            await this.loadSources();
            if (!this.state.slides.length) {
                await this.addSlide();
            } else {
                await this.selectSlide(this.state.slides[0].id);
            }
        } catch (err) {
            this.notification.add(
                _t("The presentation could not be opened."), { type: "danger" });
            throw err;
        } finally {
            this.state.loading = false;
        }
    }

    async loadSlides() {
        this.state.slides = await this.orm.searchRead(
            "dashboard.presentation.slide",
            [["deck_id", "=", this.deckId]],
            ["name", "sequence", "heading", "subheading",
             "heading_align", "heading_color", "subheading_color"],
            { order: "sequence, id" });
    }

    /**
     * What can be put on a slide: the charts and notes of every dashboard
     * this deck draws from.
     *
     * Asked of the deck rather than assembled here, because "which
     * dashboards" is no longer one id - a deck can be pointed at several,
     * and the record that knows them should answer for them. A deck being
     * started has no record yet, so the dashboard it was started from is
     * sent instead.
     *
     * Failures are surfaced, not swallowed. An empty picker that means "the
     * query broke" looks exactly like one that means "there is nothing here",
     * and the first is a bug nobody would report.
     */
    async loadSources() {
        this.state.sheets = [];
        this.state.notes = [];
        this.state.sourceCount = 0;
        this.state.sourcesLoaded = false;
        try {
            const sources = await this.orm.call(
                "dashboard.presentation.deck", "presentation_sources",
                [this.deckId || false, this.dashboardId || false]);
            this.state.sheets = sources.sheets || [];
            this.state.notes = sources.notes || [];
            this.state.sourceCount = sources.source_count || 0;
            this.state.sourcesLoaded = true;
        } catch (err) {
            this.notification.add(
                _t("The charts and notes for this deck could not be loaded."),
                { type: "danger" });
            console.error("presentation editor: sources failed", err);
        }
    }

    async addSlide() {
        const id = await this.orm.call(
            "dashboard.presentation.deck", "action_add_slide", [this.deckId]);
        await this.loadSlides();
        await this.selectSlide(id);
    }

    async deleteSlide(slideId) {
        if (this.state.slides.length <= 1) {
            this.notification.add(
                _t("A presentation needs at least one slide."), { type: "warning" });
            return;
        }
        await this.orm.unlink("dashboard.presentation.slide", [slideId]);
        await this.loadSlides();
        await this.selectSlide(this.state.slides[0].id);
    }

    /**
     * A slide dragged to a new place in the rail.
     *
     * The drop tells us what it landed after, which is the only thing that
     * survives the drag reliably - an index would be read from a list the
     * drag itself has already rearranged in the DOM. Rebuilding the order
     * from ids and sending the whole sequence keeps the server the single
     * authority on it.
     */
    async onSlideDropped(slideId, afterId) {
        const order = this.state.slides.map((s) => s.id);
        const from = order.indexOf(slideId);
        if (from < 0) {
            return;
        }
        order.splice(from, 1);
        const to = afterId ? order.indexOf(afterId) + 1 : 0;
        order.splice(to, 0, slideId);
        await this.applySlideOrder(order);
    }

    async applySlideOrder(order) {
        await this.orm.call(
            "dashboard.presentation.item", "reorder_slides",
            [this.deckId, order]);
        await this.loadSlides();
    }

    async selectSlide(slideId) {
        this.state.activeSlideId = slideId;
        const items = await this.orm.searchRead(
            "dashboard.presentation.item",
            [["slide_id", "=", slideId]],
            ["item_type", "sheet_id", "note_id", "content_html",
             "image_fit", "text_align", "text_color", "x", "y", "w", "h",
             "use_dashboard_filters", "config_id"],
            { order: "y, x, id" });
        const available = new Set((this.state.sheets || []).map((s) => s.id));
        this.state.items = this.state.sourcesLoaded
            ? items.filter((item) => item.item_type !== "chart"
                || (item.sheet_id && available.has(item.sheet_id[0])))
            : items;
        await this.renderGrid();
    }

    /** Whether this slide shows heading fields at all. */
    get showHeading() {
        const slide = this.activeSlide;
        if (!slide) {
            return false;
        }
        return Boolean(slide.heading || slide.subheading
                       || this.state.headingOn === slide.id);
    }

    /**
     * Add a heading to this slide.
     *
     * A heading is a property of the slide rather than a box on the grid -
     * it sits above the boxes when presented, and letting it be dragged
     * among them would make "the title" just another rectangle that could
     * end up in the middle of the slide. So it is added like the others,
     * and behaves like a title.
     */
    addHeading() {
        if (!this.state.activeSlideId) {
            return;
        }
        this.state.picker = false;
        this.state.headingOn = this.state.activeSlideId;
    }

    /** Take the heading off this slide again. */
    async removeHeading() {
        const slide = this.activeSlide;
        this.state.headingOn = false;
        if (!slide || !(slide.heading || slide.subheading)) {
            return;
        }
        slide.heading = "";
        slide.subheading = "";
        await this.orm.write("dashboard.presentation.slide", [slide.id], {
            heading: "", subheading: "",
        });
    }

    /** Cycle the heading block's alignment. */
    async cycleHeadingAlign() {
        const slide = this.activeSlide;
        if (!slide) {
            return;
        }
        const modes = ["left", "center", "right"];
        const next = modes[(modes.indexOf(slide.heading_align || "left") + 1)
                           % modes.length];
        slide.heading_align = next;
        await this.orm.write("dashboard.presentation.slide", [slide.id],
                             { heading_align: next });
    }

    async setHeadingColor(field, ev) {
        const slide = this.activeSlide;
        if (!slide) {
            return;
        }
        const value = ev.target.value;
        slide[field] = value;
        await this.orm.write("dashboard.presentation.slide", [slide.id],
                             { [field]: value });
    }

    headingAlignIcon() {
        const map = { left: "ri-align-left", center: "ri-align-center",
                      right: "ri-align-right" };
        return map[this.activeSlide?.heading_align || "left"];
    }

    /** Heading and sub-heading are what the audience reads, so they are
     *  edited on the slide itself rather than buried in a side panel. */
    async saveSlideField(field, ev) {
        const slide = this.activeSlide;
        if (!slide) {
            return;
        }
        const value = ev.target.value.trim();
        if (value === (slide[field] || "")) {
            return;
        }
        slide[field] = value;
        await this.orm.write("dashboard.presentation.slide",
                             [slide.id], { [field]: value });
    }

    get activeSlide() {
        return this.state.slides.find((s) => s.id === this.state.activeSlideId);
    }

    togglePicker(kind) {
        this.state.picker = this.state.picker === kind ? false : kind;
    }

    getOccupiedItems() {
        if (this.stack?.engine?.nodes?.length) {
            return this.stack.engine.nodes.map((n) => ({
                id: n.id || (n.el ? Number(n.el.id.replace("pitem_", "")) : 0),
                x: n.x ?? 0,
                y: n.y ?? 0,
                w: n.w ?? 1,
                h: n.h ?? 1,
            }));
        }
        if (this.canvasRef?.el) {
            const live = [];
            this.canvasRef.el.querySelectorAll(".cy-pe-item").forEach((el) => {
                const node = el.gridstackNode;
                const id = Number(el.id.replace("pitem_", ""));
                if (node) {
                    live.push({
                        id,
                        x: node.x !== undefined ? node.x : (Number(el.getAttribute("gs-x")) || 0),
                        y: node.y !== undefined ? node.y : (Number(el.getAttribute("gs-y")) || 0),
                        w: node.w !== undefined ? node.w : (Number(el.getAttribute("gs-w")) || 1),
                        h: node.h !== undefined ? node.h : (Number(el.getAttribute("gs-h")) || 1),
                    });
                }
            });
            if (live.length) return live;
        }
        return this.state.items || [];
    }

    /**
     * Find the first free slot on the slide (left-to-right, top-to-bottom)
     * that fits a w×h box without overlapping any existing item.
     *
     * Inspects live GridStack nodes so any recent resizing or dragging
     * is accounted for even if the database has not finished persisting.
     */
    findFreeSlot(w, h) {
        const items = this.getOccupiedItems();
        // Clamp the box to fit within the 12×12 board.
        const bw = Math.min(w, COLUMNS);
        const bh = Math.min(h, ROWS);

        // Build an occupancy set: every (col, row) cell that is already taken.
        const occupied = new Set();
        for (const item of items) {
            const ix = item.x || 0;
            const iy = item.y || 0;
            const iw = item.w || 1;
            const ih = item.h || 1;
            for (let r = iy; r < iy + ih; r++) {
                for (let c = ix; c < ix + iw; c++) {
                    occupied.add(`${c},${r}`);
                }
            }
        }
        for (let row = 0; row <= ROWS - bh; row++) {
            for (let col = 0; col <= COLUMNS - bw; col++) {
                let fits = true;
                outer:
                for (let r = row; r < row + bh; r++) {
                    for (let c = col; c < col + bw; c++) {
                        if (occupied.has(`${c},${r}`)) {
                            fits = false;
                            break outer;
                        }
                    }
                }
                if (fits) {
                    return { x: col, y: row, w: bw, h: bh, fits: true };
                }
            }
        }
        return { x: 0, y: 0, w: bw, h: bh, fits: false };
    }

    /**
     * Where a new box goes: the first free position for the requested size,
     * else the largest smaller box (at least 2×2) that fits. Returns false
     * when nothing fits, because the slide grid cannot overlap boxes and
     * would push an existing one off the slide.
     */
    nextSlot(w, h) {
        const slot = this.findFreeSlot(w, h);
        if (slot.fits) {
            return { x: slot.x, y: slot.y, w: slot.w, h: slot.h };
        }
        const sizes = [];
        for (let sw = Math.min(w, COLUMNS); sw >= 2; sw--) {
            for (let sh = Math.min(h, ROWS); sh >= 2; sh--) {
                sizes.push([sw, sh]);
            }
        }
        sizes.sort((a, b) => b[0] * b[1] - a[0] * a[1]);
        for (const [sw, sh] of sizes) {
            const smaller = this.findFreeSlot(sw, sh);
            if (smaller.fits) {
                this.notification.add(
                    _t("There is not enough space for the full size, so the box was added smaller."),
                    { type: "warning" }
                );
                return { x: smaller.x, y: smaller.y, w: smaller.w, h: smaller.h };
            }
        }
        this.notification.add(
            _t("There is no space left on the slide. Move or resize a box, or add a new slide."),
            { type: "warning" }
        );
        return false;
    }

    async addChart(sheetId, dashboardId = false) {
        if (this.state.dirty) {
            await this.saveLayout();
        }
        const slot = this.nextSlot(6, 4);
        if (!slot) {
            this.state.picker = false;
            return;
        }
        await this.orm.create("dashboard.presentation.item", [{
            slide_id: this.state.activeSlideId,
            item_type: "chart",
            sheet_id: sheetId,
            config_id: dashboardId || false,
            use_dashboard_filters: false,
            ...slot,
        }]);
        this.state.picker = false;
        await this.selectSlide(this.state.activeSlideId);
    }

    async addNote(noteId) {
        if (this.state.dirty) {
            await this.saveLayout();
        }
        const slot = this.nextSlot(4, 4);
        if (!slot) {
            this.state.picker = false;
            return;
        }
        await this.orm.create("dashboard.presentation.item", [{
            slide_id: this.state.activeSlideId,
            item_type: "note",
            note_id: noteId,
            ...slot,
        }]);
        this.state.picker = false;
        await this.selectSlide(this.state.activeSlideId);
    }

    async addText() {
        if (this.state.dirty) {
            await this.saveLayout();
        }
        const slot = this.nextSlot(4, 3);
        if (!slot) {
            return;
        }
        await this.orm.create("dashboard.presentation.item", [{
            slide_id: this.state.activeSlideId,
            item_type: "text",
            content_html: "",
            ...slot,
        }]);
        this.state.picker = false;
        await this.selectSlide(this.state.activeSlideId);
    }

    /**
     * Add a picture from the machine. Read as a data URL and stored on the
     * item, which is what lets it be served back by URL afterwards.
     */
    addImage() {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "image/*";
        input.addEventListener("change", async () => {
            const file = input.files && input.files[0];
            if (!file) {
                return;
            }
            const base64 = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(
                    String(reader.result).split(",")[1] || "");
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            if (this.state.dirty) {
                await this.saveLayout();
            }
            const slot = this.nextSlot(6, 4);
            if (!slot) {
                return;
            }
            try {
                await this.orm.create("dashboard.presentation.item", [{
                    slide_id: this.state.activeSlideId,
                    item_type: "image",
                    image: base64,
                    ...slot,
                }]);
            } catch (err) {
                this.notification.add(
                    _t("That image could not be added."), { type: "danger" });
                throw err;
            }
            this.state.picker = false;
            await this.selectSlide(this.state.activeSlideId);
        });
        input.click();
    }

    async removeItem(itemId) {
        await this.orm.unlink("dashboard.presentation.item", [itemId]);
        await this.selectSlide(this.state.activeSlideId);
    }

    flushActiveText() {
        if (!this.canvasRef.el) return;
        const editables = this.canvasRef.el.querySelectorAll(".cy-pe-editable");
        editables.forEach((box) => {
            const itemEl = box.closest(".cy-pe-item");
            const itemId = itemEl && Number(itemEl.id?.replace("pitem_", ""));
            const item = this.state.items.find((it) => it.id === itemId);
            if (item) {
                if (!box.textContent.trim()) {
                    box.innerHTML = "";
                }
                this.flushText(item, box);
            }
        });
    }

    teardownGrid() {
        Object.values(this.stackItems).forEach((item) => {
            if (item.resizeObserver) item.resizeObserver.disconnect();
        });
        this.stackItems = {};
        if (this.stack) {
            this.stack.destroy(false);
            this.stack = null;
        }
    }

    async renderGrid() {
        const containerEl = this.canvasRef.el;
        if (!containerEl) return;
        this.teardownGrid();
        containerEl.innerHTML = "";

        const width = containerEl.clientWidth || containerEl.offsetWidth || 960;
        const cell = Math.max(Math.round((width * SLIDE_RATIO) / ROWS), 24);
        this.pixelSize = cell;
        const MARGIN = 4;
        containerEl.style.height = `${cell * ROWS}px`;
        this.stack = GridStack.init(
            {
                float: true,
                cellHeight: cell,
                column: COLUMNS,
                margin: MARGIN,
                minRow: ROWS,
                maxRow: ROWS,
                row: ROWS,
                animate: false,
                draggable: { handle: ".cy-pe-head" },
            },
            containerEl);

        ["top", "right", "bottom", "left"].forEach((side) =>
            containerEl.style.setProperty(`--gs-item-margin-${side}`, `${MARGIN}px`));
        const engine = this.stack.engine;
        const origMoveNode = engine.moveNode;
        const moving = new Set();
        engine.moveNode = function (node, opts) {
            const id = node._id;
            if (moving.has(id)) return false;
            moving.add(id);
            try {
                return origMoveNode.apply(this, [node, opts]);
            } finally {
                moving.delete(id);
            }
        };

        const chartItems = this.state.items.filter((i) => i.item_type === "chart");
        let dataBySheet = {};
        if (chartItems.length) {
            try {
                dataBySheet = await this.orm.call(
                    "dashboard.sheet", "fetch_sheet_data",
                    [chartItems.map((i) => i.sheet_id[0]),
                     this.chartFilterPayload(chartItems)]);
            } catch (err) {
                console.error("presentation editor: chart data failed", err);
            }
        }
        const sheetConfig = chartItems.length
            ? await this.orm.read(
                "dashboard.sheet", chartItems.map((i) => i.sheet_id[0]),

                ["name", "type", "measure", "dimension", "dimension_axis",
                 ...KPI_SHEET_FIELDS]
              ).catch((err) => {
                  console.error("presentation editor: sheet config failed", err);
                  return [];
              })
            : [];
        const styling = await fetchSheetStyling(
            this.orm, sheetConfig.map((s) => s.id)).catch(() => ({}));
        sheetConfig.forEach((s) => Object.assign(s, styling[s.id] || {}));
        if (chartItems.length && !this.themeColors) {
            const configData = await this.orm.call(
                "dashboard.sheet", "get_config_data", []).catch(() => ({}));
            this.themeColors = configData.theme_color_ids || [];
        }
        const configById = Object.fromEntries(sheetConfig.map((s) => [s.id, s]));

        if (status(this) === "destroyed") return;

        this.state.items.forEach((item) => {
            const el = document.createElement("div");
            el.id = `pitem_${item.id}`;
            el.classList.add("cy-pe-item");
            const content = document.createElement("div");
            content.className = "grid-stack-item-content";
            el.appendChild(content);
            const head = document.createElement("div");
            head.className = "cy-pe-head";
            head.title = _t("Drag to move");
            const label = document.createElement("span");
            label.className = "cy-pe-head-label";
            label.textContent = this.itemLabel(item);
            head.appendChild(label);
            if (item.item_type === "text") {
                head.appendChild(this.textToolbar(item));
            }
            if (item.item_type === "image") {
                head.appendChild(this.imageToolbar(item));
            }
            if (item.item_type === "chart" && this.configIdFor(item)) {
                head.appendChild(this.chartToolbar(item));
            }

            const remove = document.createElement("button");
            remove.className = "cy-pe-remove";
            remove.title = _t("Remove from slide");
            remove.innerHTML = '<i class="ri-close-line"></i>';
            remove.addEventListener("click", (ev) => {
                ev.stopPropagation();
                this.removeItem(item.id);
            });
            head.appendChild(remove);
            content.appendChild(head);

            this.stack.makeWidget(el, {
                x: item.x || 0, y: item.y || 0,
                w: Math.max(item.w || 1, 1), h: Math.max(item.h || 1, 1),
            });

            const body = document.createElement("div");
            body.className = "cy-pe-body-box";
            content.appendChild(body);

            if (item.item_type === "chart") {
                this.mountChart(body, item, configById[item.sheet_id[0]],
                                dataBySheet[item.sheet_id[0]] ?? []);
            } else if (item.item_type === "image") {
                this.mountImage(body, item);
            } else {
                this.mountText(body, item);
            }
        });

        this.stack.on("change", () => {
            this.state.dirty = true;
            this.saveLayout();
        });
        this.stack.on("dragstop", () => {
            if (this.hasOverlap()) {
                this.notification.add(
                    _t("Items are overlapping in the slide."),
                    { type: "warning" }
                );
            }
        });
        this.stack.on("resizestop", () => {
            Object.values(this.stackItems).forEach((si) => {
                if (si.eChart) si.eChart.resize();
            });
            if (this.hasOverlap()) {
                this.notification.add(
                    _t("Items are overlapping in the slide."),
                    { type: "warning" }
                );
            }
        });
    }

    mountChart(contentEl, item, config, data) {
        if (!config) {
            contentEl.innerHTML =
                `<div class="cy-pe-missing">${_t("This chart is no longer available.")}</div>`;
            return;
        }
        let measures;
        try {
            measures = eval(config.measure);
        } catch (e) {
            measures = [];
        }
        measures = resolveMeasures(
            data, config.dimension, measures,
            config.series_dimension, config.series_labels);

        const props = {
            data, name: config.name, measures,
            dimension: config.dimension,
            dimension_axis: config.dimension_axis,
            type: config.type, id: config.id,
            // StackKpiItem passes this straight to KpiSheetChart.
            kpi: config.type === "kpi" ? kpiSettingsFromSheet(config) : false,
        };
        const opts = {
            unit: this.pixelSize || 20,
            graph_height: item.h,
            themeColor: this.themeColors || [],
            lineMeasure: config.line_measure,
            color_mappings: config.color_mappings || [],
            annotations: config.annotations || [],
        };
        const key = `pitem_${item.id}`;
        if (config.type === "kpi") {
            this.stackItems[key] = new StackKpiItem(contentEl, props, this.env, opts);
        } else if (config.type === "table") {
            this.stackItems[key] = new StackTableItem(contentEl, props, this.env, opts);
        } else {
            this.stackItems[key] = new StackItem(contentEl, props, null, opts);
        }
    }

    /**
     * Notes and free text share this: both are HTML in a box. A note is shown
     * read-only because it belongs to the chart it was written against -
     * editing it here would quietly rewrite what the dashboard shows.
     */
    /**
     * Bold, italic, bullets, heading. execCommand is deprecated on paper and
     * still the only thing every browser implements for contentEditable; the
     * alternative is a rich-text engine, which this box does not warrant.
     */
    textToolbar(item) {
        const bar = document.createElement("span");
        bar.className = "cy-pe-fmt";
        const buttons = [
            ["bold", "ri-bold", _t("Bold")],
            ["italic", "ri-italic", _t("Italic")],
            ["insertUnorderedList", "ri-list-unordered", _t("Bullets")],
        ];
        // Alignment cycles through the same three the heading offers, so the
        // control means one thing everywhere on the slide.
        const alignBtn = document.createElement("button");
        alignBtn.className = "cy-pe-fmt-btn";
        const alignIcons = { left: "ri-align-left", center: "ri-align-center",
                             right: "ri-align-right" };
        const paintAlign = () => {
            const mode = item.text_align || "left";
            alignBtn.innerHTML = `<i class="${alignIcons[mode]}"></i>`;
            alignBtn.title = _t("Alignment");
            const box = this.canvasRef.el?.querySelector(
                `#pitem_${item.id} .cy-pe-editable`);
            if (box) {
                box.style.textAlign = mode;
            }
        };
        alignBtn.addEventListener("mousedown", async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const modes = ["left", "center", "right"];
            item.text_align = modes[
                (modes.indexOf(item.text_align || "left") + 1) % modes.length];
            paintAlign();
            await this.orm.write("dashboard.presentation.item", [item.id],
                                 { text_align: item.text_align });
        });
        bar.appendChild(alignBtn);
        setTimeout(paintAlign, 0);
        const colour = document.createElement("input");
        colour.type = "color";
        colour.className = "cy-pe-colour";
        colour.title = _t("Text colour");
        colour.value = item.text_color || "#000000";
        colour.addEventListener("mousedown", (ev) => ev.stopPropagation());
        colour.addEventListener("change", async () => {
            const box = this.canvasRef.el?.querySelector(
                `#pitem_${item.id} .cy-pe-editable`);
            if (!box) {
                return;
            }
            const selection = window.getSelection();
            const inside = selection && selection.rangeCount
                && box.contains(selection.anchorNode)
                && !selection.isCollapsed;
            if (inside) {
                document.execCommand("foreColor", false, colour.value);
            } else {
                box.style.color = colour.value;
                item.text_color = colour.value;
                await this.orm.write("dashboard.presentation.item", [item.id],
                                     { text_color: colour.value });
            }
            await this.flushText(item);
        });
        bar.appendChild(colour);

        buttons.forEach(([command, icon, title]) => {
            const b = document.createElement("button");
            b.className = "cy-pe-fmt-btn";
            b.title = title;
            b.innerHTML = `<i class="${icon}"></i>`;
            b.addEventListener("mousedown", (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                document.execCommand(command, false, null);
                this.flushText(item);
            });
            bar.appendChild(b);
        });
        return bar;
    }

    /** Persist a text box's current HTML. */
    async flushText(item, targetBox = null) {
        if (status(this) === "destroyed") {
            return;
        }
        const box = targetBox || this.canvasRef.el?.querySelector(
            `#pitem_${item.id} .cy-pe-editable`);
        if (!box) {
            return;
        }
        const html = box.textContent.trim() ? box.innerHTML : "";
        if (html === (item.content_html || "")) {
            return;
        }
        item.content_html = html;
        const orm = this.env?.services?.orm || this.orm;
        if (!orm) {
            return;
        }
        try {
            await orm.write("dashboard.presentation.item", [item.id], {
                content_html: html,
            });
        } catch (err) {
            if (status(this) === "destroyed" || err?.message === "Component is destroyed") {
                return;
            }
            throw err;
        }
    }

    itemLabel(item) {
        if (item.item_type === "chart") {
            return item.sheet_id?.[1] || _t("Chart");
        }
        if (item.item_type === "note") {
            return _t("Note");
        }
        if (item.item_type === "image") {
            return _t("Image");
        }
        return _t("Text");
    }

    /**
     * Fit / Fill / Stretch, cycled from the box's own handle.
     *
     * A picture almost never has the proportions of the box it lands in, so
     * "Fit" leaves bars at the sides. Which trade is right is a judgement
     * about that picture - a logo must not be cropped, a photograph usually
     * can be - so it is offered rather than decided here.
     */
    /**
     * The dashboard's global filter values, as the dashboard itself holds
     * them.
     *
     * The dashboard keeps these in session storage rather than on the
     * record, so this reads the same key rather than inventing a second
     * source that could disagree with what the dashboard is showing. The
     * date pair is stored under date_0/date_1 but applied under the
     * 'start-date'/'end-date' codes, so it is translated here; every other
     * filter is keyed by its own code already, holding records from which
     * only the ids are wanted.
     *
     * An empty object is the honest answer when the dashboard has not been
     * opened in this session: the chart then draws unfiltered rather than
     * against filters nobody chose.
     */
    dashboardFilterValues() {
        const stored = this.saveContext?.getKeyValue?.("defaultFilter");
        if (!stored || typeof stored !== "object") {
            return {};
        }
        const values = {};
        if (stored.date_0) {
            values["start-date"] = stored.date_0;
        }
        if (stored.date_1) {
            values["end-date"] = stored.date_1;
        }
        for (const [code, value] of Object.entries(stored)) {
            if (["date_0", "date_1", "selected"].includes(code)) {
                continue;
            }
            if (Array.isArray(value) && value.length) {
                const ids = value
                    .map((rec) => (rec && typeof rec === "object" ? rec.id : rec))
                    .filter((id) => typeof id === "number");
                if (ids.length) {
                    values[code] = ids;
                }
            }
        }
        return values;
    }

    /**
     * The `filters` argument for fetch_sheet_data: only the boxes asking to
     * be shown the way the dashboard shows them.
     */
    chartFilterPayload(chartItems) {
        const toggled = chartItems.filter(
            (i) => i.use_dashboard_filters && this.configIdFor(i));
        if (!toggled.length) {
            return {};
        }
        const values = this.dashboardFilterValues();
        if (!Object.keys(values).length) {
            return {};
        }
        const payload = {};
        for (const item of toggled) {
            payload[String(item.sheet_id[0])] = {
                config_id: this.configIdFor(item),
                values,
            };
        }
        return payload;
    }

    /**
     * The chart box's own control: draw this from the sheet, or the way the
     * dashboard draws it.
     *
     * Sits in the box header beside the text box's formatting controls, and
     * like them belongs to arranging the deck - the player never renders it,
     * so an audience sees the chosen chart and no switch.
     */
    /**
     * The dashboard whose filters this box may be shown through: the one it
     * was added from, or failing that the one its sheet lives on. A deck with
     * no dashboards of its own leaves config_id empty, and without this
     * fallback such a box could never be shown the way the dashboard shows it.
     */
    configIdFor(item) {
        if (item.config_id) {
            return item.config_id[0];
        }
        if (!item.sheet_id) {
            return false;
        }
        const sheet = (this.state.sheets || []).find(
            (s) => s.id === item.sheet_id[0]);
        return (sheet && sheet.dashboard_id) || false;
    }

    chartToolbar(item) {
        const bar = document.createElement("span");
        bar.className = "cy-pe-fmt";
        const button = document.createElement("button");
        button.className = "cy-pe-fmt-btn cy-pe-source-btn";
        const paint = () => {
            const on = !!item.use_dashboard_filters;
            button.textContent = on ? _t("Dashboard") : _t("Sheet");
            button.classList.toggle("active", on);
            button.title = on
                ? _t("Showing this chart as the dashboard shows it, with the dashboard's filters applied. Click to show the sheet itself instead.")
                : _t("Showing the sheet itself, unfiltered. Click to show it as the dashboard shows it.");
        };
        paint();
        button.addEventListener("mousedown", async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            item.use_dashboard_filters = !item.use_dashboard_filters;
            paint();
            const values = {
                use_dashboard_filters: item.use_dashboard_filters,
            };
            if (!item.config_id) {
                const configId = this.configIdFor(item);
                if (configId) {
                    values.config_id = configId;
                    item.config_id = [configId, ""];
                }
            }
            await this.orm.write(
                "dashboard.presentation.item", [item.id], values);
            await this.renderGrid();
        });
        bar.appendChild(button);
        return bar;
    }

    imageToolbar(item) {
        const modes = ["contain", "cover", "fill"];
        const labels = { contain: _t("Fit"), cover: _t("Fill"), fill: _t("Stretch") };
        const bar = document.createElement("span");
        bar.className = "cy-pe-fmt";
        const button = document.createElement("button");
        button.className = "cy-pe-fmt-btn cy-pe-fit-btn";
        const paint = () => {
            const mode = item.image_fit || "contain";
            button.textContent = labels[mode];
            button.title = _t("Change how the picture fills its box");
            const img = this.canvasRef.el?.querySelector(
                `#pitem_${item.id} .cy-pe-image`);
            if (img) {
                img.style.objectFit = mode;
            }
        };
        button.addEventListener("mousedown", async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const next = modes[(modes.indexOf(item.image_fit || "contain") + 1)
                               % modes.length];
            item.image_fit = next;
            paint();
            await this.orm.write("dashboard.presentation.item", [item.id], {
                image_fit: next,
            });
        });
        bar.appendChild(button);
        // Painted after the image exists, so the first render matches.
        setTimeout(paint, 0);
        return bar;
    }

    mountImage(contentEl, item) {
        const img = document.createElement("img");
        img.className = "cy-pe-image";
        img.style.objectFit = item.image_fit || "contain";
        // Served by id rather than embedded, so a large picture does not ride
        // along in every read of the slide.
        img.src = `/web/image/dashboard.presentation.item/${item.id}/image`;
        img.alt = "";
        contentEl.appendChild(img);
    }

    mountText(contentEl, item) {
        const box = document.createElement("div");
        box.className = "cy-pe-text";
        const source = item.item_type === "note"
            ? (this.state.notes.find((n) => n.id === item.note_id?.[0])?.note_html || "")
            : (item.content_html || "");
        box.innerHTML = source;

        if (item.item_type === "text") {
            box.contentEditable = "true";
            box.classList.add("cy-pe-editable");
            box.dataset.placeholder = _t("Write here…");
            box.style.textAlign = item.text_align || "left";
            if (item.text_color) {
                box.style.color = item.text_color;
            }
            box.addEventListener("blur", async () => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (!box.textContent.trim()) {
                    box.innerHTML = "";
                }
                await this.flushText(item, box);
            });
        } else {
            box.classList.add("cy-pe-note");
        }
        contentEl.appendChild(box);
    }

    hasOverlap() {
        const nodes = this.stack?.engine?.nodes || [];
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const a = nodes[i];
                const b = nodes[j];
                const ax = a.x ?? 0, ay = a.y ?? 0, aw = a.w ?? 1, ah = a.h ?? 1;
                const bx = b.x ?? 0, by = b.y ?? 0, bw = b.w ?? 1, bh = b.h ?? 1;
                if (!(ax + aw <= bx || bx + bw <= ax || ay + ah <= by || by + bh <= ay)) {
                    return true;
                }
            }
        }
        return false;
    }

    async saveLayout() {
        if (!this.stack || !this.canvasRef.el || status(this) === "destroyed") return;
        const payload = [];
        this.canvasRef.el.querySelectorAll(".cy-pe-item").forEach((el) => {
            const node = el.gridstackNode;
            if (!node) return;
            const id = Number(el.id.replace("pitem_", ""));
            const x = node.x ?? 0;
            const y = node.y ?? 0;
            const w = node.w ?? 1;
            const h = node.h ?? 1;
            payload.push({ id, x, y, w, h });
            const item = (this.state.items || []).find((it) => it.id === id);
            if (item) {
                item.x = x;
                item.y = y;
                item.w = w;
                item.h = h;
            }
        });
        try {
            await this.orm.call("dashboard.presentation.item", "save_layout",
                                [this.state.activeSlideId, payload]);
            this.state.dirty = false;
        } catch (err) {
            this.notification.add(
                _t("The new arrangement could not be saved."), { type: "danger" });
            throw err;
        }
    }

    /**
     * Leave the editor for the list of presentations.
     *
     * A plain history.back() would land wherever the editor happened to be
     * opened from - and after a Present it lands back in the deck, which is
     * not "back" in any useful sense. The list is always the right place.
     */
    async goBack() {
        await this.action.doAction(
            "cyllo_analytics.action_presentation_deck", { clearBreadcrumbs: true });
    }

    async renameDeck(ev) {
        const name = ev.target.value.trim();
        if (!name || name === this.state.deckName) return;
        await this.orm.write("dashboard.presentation.deck", [this.deckId], { name });
        this.state.deckName = name;
    }

    noteLabel(note) {
        const text = (note.note_html || "").replace(/<[^>]*>/g, " ").trim();
        return text.length > 60 ? `${text.slice(0, 60)}…` : (text || _t("(empty note)"));
    }

    markup(html) {
        return markup(html || "");
    }
}

registry.category("actions").add("cy_presentation_editor", PresentationEditor);
