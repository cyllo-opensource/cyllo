/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { useRef, onMounted, useState, onWillStart, Component, onWillDestroy,
        useEffect, markup } = owl;
import { _t } from "@web/core/l10n/translation";
import { GraphTile } from "./presentation/components/graph_tile"
import { browser } from "@web/core/browser/browser";
import { ThemeMaker } from "./theme_maker";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { Table } from "@cyllo_analytics/js/table/table";
import { KpiSheetChart } from "@cyllo_analytics/js/kpi_sheet_chart";
import { KPI_SHEET_FIELDS, kpiSettingsFromSheet, fetchSheetStyling } from "@cyllo_analytics/js/utils";
import { resolveMeasures } from "./chart_maker";

let isPlaying = false;

try {
    Reveal.configure({
        keyboard: {
            32: () => {
                const playbackElement = document.querySelector(".playback");
                if (playbackElement) {
                    const clickEvent = new Event('click');
                    isPlaying ? (isPlaying = false) : (isPlaying = true);
                    if (isPlaying) {
                        playbackElement.dispatchEvent(clickEvent);
                    }
                }
            }
        }
    });
} catch {
    console.warn("Internet connection is not available")
}

class PresentationMaker extends Component {
    /** Class for creating a presentation maker component. */
    setup() {
        this.actionService = useService("action")
        this.orm = useService("orm")
        const { type } = this.props.action.context;
        this.chartData = useState({ data: [], style: null, theme: null, themeData: {} });
        this.state = useState({
            exit: type ? false : true, warning: false, darkMode: false,
            deckSlides: [],
        })
        this.type = type;
        this.ref = useRef('root')
        this.saveContext = useSaveContext()
        this.id = this.saveContext?.id
        this._boundExitHandler = this.exitHandler.bind(this);
        this._rootStyleBefore = document.documentElement.style.cssText;

        onWillDestroy(() => {
            document.body.classList.remove('cy-presentation-active');
            document.body.classList.remove('reveal-viewport');
            document.documentElement.classList.remove('reveal-full-page');
            if (this.navBar) {
                this.navBar.style.display = 'flex';
            }
            if (this.actionWrapper) {
                this.actionWrapper.style.removeProperty('margin-left');
                this.actionWrapper.style.removeProperty('width');
            }
            if (document.fullscreenElement) {
                try {
                    document.exitFullscreen().catch(() => {});
                } catch (e) {}
            }

            // Remove fullscreen listeners added in onMounted so they don't
            // accumulate across multiple mounts of this component.
            document.removeEventListener('webkitfullscreenchange', this._boundExitHandler, false);
            document.removeEventListener('mozfullscreenchange', this._boundExitHandler, false);
            document.removeEventListener('fullscreenchange', this._boundExitHandler, false);
            document.removeEventListener('MSFullscreenChange', this._boundExitHandler, false);
            try {
                if (this.deck && typeof this.deck.removeEventListeners === "function") {
                    this.deck.removeEventListeners();
                }
            } catch (e) {}
            if (this._stageObserver) {
                this._stageObserver.disconnect();
                this._stageObserver = null;
            }
            this.deck = null;
            this.reveal = null;

            document.documentElement.style.cssText = this._rootStyleBefore;
        });
        onWillStart(async () => {
            this.state.darkMode = await this.orm.call('res.users', 'get_active', [])
            await this.fetchData()
            if (this.chartData.themeData && this.chartData.themeData.name) {
                var theme_maker = new ThemeMaker(this.chartData.themeData)
                theme_maker.getTheme()
            }
        })
        onMounted(async () => {
            await Promise.resolve();

            this.navBar = document.body.querySelector('.o_navbar');
            this.sideBar = document.body.querySelector('.cy-left-sidebar');
            this.sideBar2 = document.body.querySelector('.cy-submenu-box');
            const actionManager = document.querySelector('.o_action_manager');
            let el = this.ref.el;
            while (el && el.parentElement !== actionManager) {
                el = el.parentElement;
            }
            this.actionWrapper = el;

            document.addEventListener('webkitfullscreenchange', this._boundExitHandler, false);
            document.addEventListener('mozfullscreenchange', this._boundExitHandler, false);
            document.addEventListener('fullscreenchange', this._boundExitHandler, false);
            document.addEventListener('MSFullscreenChange', this._boundExitHandler, false);

            try {
                if (this.ref.el) {
                    this.deck = new Reveal(this.ref.el, {
                        controls: true,
                        progress: false,
                        // Reveal binds ESC (and O) to its slide overview:
                        //   27 !== i && 79 !== i || (... overview.toggle())
                        // The first ESC out of a presentation leaves full
                        // screen, so the second one reached that handler and
                        // opened the overview — which cannot lay out here,
                        // because the overrides in style.css and
                        // presentation_maker.css pin .slides to zoom:unset at
                        // 100%/100% and every section to top:0, leaving a lone
                        // slide adrift on an empty page. There is no way into
                        // the overview by design and no way back out of it by
                        // accident, so it is off.
                        overview: false,
                        hash: false,
                        transition: 'slide',
                        transitionSpeed: 'default',
                        autoSlide: (type || this.type) === 'play' ? this.autoSlideTime * 1000 : false,
                        keyboard: {
                            32: () => {
                                const playbackElement = document.querySelector(".playback");
                                if (playbackElement) {
                                    const clickEvent = new Event('click');
                                    isPlaying ? (isPlaying = false) : (isPlaying = true);
                                    if (isPlaying) {
                                        playbackElement.dispatchEvent(clickEvent);
                                    }
                                }
                            }
                        }
                    });
                    await this.deck.initialize();
                    this.reveal = this.deck;
                }
            } catch (e) {
                console.warn("Reveal.js could not initialize", e);
            }

            this.fullScreen = true;
            this.toggleSideAndHeader();
            this.observeDeckStages();
        })
    }

    /**
     * Keep every slide's board sized to the space it actually has.
     *
     * Everything is measured from the Reveal canvas, the one element in the
     * chain with a height of its own (100dvh, inline). The slide sections are
     * absolutely positioned and their heights never resolve to anything a
     * child can derive from, which is why leaving this to `aspect-ratio` and
     * flex-grow produced first an oversized board and then none at all.
     */
    observeDeckStages() {
        if (!this.ref.el) {
            return;
        }
        this.fitDeckBoards();
        if (typeof ResizeObserver !== "undefined") {
            this._stageObserver = new ResizeObserver(() => this.fitDeckBoards());
            this._stageObserver.observe(this.ref.el);
        }
        if (this.deck && typeof this.deck.on === "function") {
            this.deck.on("slidechanged", () => {
                requestAnimationFrame(() => this.fitDeckBoards());
            });
        }
    }

    /**
     * Fit each fixed 16:9 board into the canvas, less the control strip and
     * the slide's own heading. The board keeps its shape and its twelve-by-
     * twelve geometry; only its scale changes, so it is letterboxed rather
     * than cropped or stretched.
     */
    fitDeckBoards() {
        const canvas = this.ref.el;
        if (!canvas) {
            return;
        }
        const availW = canvas.clientWidth;
        const canvasH = canvas.clientHeight;
        if (!availW || !canvasH) {
            return;
        }
        for (const stage of canvas.querySelectorAll(".cy-deck-stage")) {
            const board = stage.querySelector(".cy-deck-grid");
            if (!board) {
                continue;
            }
            const slide = stage.closest(".cy-deck-slide");
            const heading = slide && slide.querySelector(".cy-deck-heading");
            // The control strip is reserved as padding on the section.
            const reserve = slide
                ? parseFloat(getComputedStyle(slide).paddingTop) || 0
                : 0;
            const availH = canvasH - reserve - (heading ? heading.offsetHeight : 0);
            if (availH <= 0) {
                continue;
            }
            stage.style.height = `${availH}px`;
            const width = Math.floor(Math.min(availW, (availH * 16) / 9));
            board.style.width = `${width}px`;
            board.style.height = `${Math.floor((width * 9) / 16)}px`;
        }
    }

    /**
     * Fetch data for the presentation.
     */
    async fetchData() {
        const deckId = this.props.action?.context?.deck_id || this.saveContext?.deck_id;
        if (deckId && (this.saveContext?.mode === "deck" || !this.props.action?.context?.rec_id)) {
            return this.fetchDeck(deckId);
        }
        var data = this.props.action?.context?.rec_id && this.props.action.context
        const recId = this.props.action?.context?.rec_id || this.saveContext?.id;
        if (!data) {
            if (!recId) {
                this.state.warning = true;
                return;
            }
            try {
                data = await this.orm.read("dashboard.presentation", [recId], [])
                if (!data.length) {
                    this.state.warning = true
                    return;
                }
            } catch {
                this.state.warning = true
                return;
            }
            data = data[0]
        }

        const {
            chart_data, style_json, type, theme, theme_json, auto_slide, auto_slide_time,
            title_page, title_page_heading, title_page_subheading
        } = data
        this.chartData.data = chart_data
        this.chartData.style = { ...(style_json || {}), height: '85vh', width: '85vw', 'margin-top': '0' }
        this.type = type
        this.autoSlideTime = auto_slide_time
        this.autoSlide = auto_slide
        this.titlePage = title_page
        this.heading = title_page_heading
        this.subheading = title_page_subheading
        this.chartData.theme = theme
        this.chartData.themeData = theme_json
    }

    /**
     * Toggle the visibility of the sidebar and header in full-screen mode.
     */
    toggleSideAndHeader() {
        let val = this.fullScreen ? 'none' : 'block';
        if (this.navBar) {
            this.navBar.style.display = this.fullScreen ? 'none' : 'flex';
        }
        if (this.fullScreen) {
            document.body.classList.add('cy-presentation-active');
        } else {
            document.body.classList.remove('cy-presentation-active');
        }
        if (this.actionWrapper) {
            if (this.fullScreen) {
                this.actionWrapper.style.setProperty('margin-left', '0', 'important');
                this.actionWrapper.style.setProperty('width', '100%', 'important');
            } else {
                this.actionWrapper.style.removeProperty('margin-left');
                this.actionWrapper.style.removeProperty('width');
            }
        }
    }

    /**
     * Handle the exit from full-screen mode.
     */
    exitHandler() {
        const stillFullScreen = !!(
            document.fullscreenElement
            || document.webkitFullscreenElement
            || document.mozFullScreenElement
            || document.msFullscreenElement
        );
        if (stillFullScreen) {
            return;
        }
        this.state.exit = true;
        this.fullScreen = false;
        this.toggleSideAndHeader();
        this.exitPresentation();
    }

    /**
     * Exit the presentation mode and navigate to the original dashboard.
     */
    /**
     * Load a saved deck: its slides, and the chart data each box needs.
     *
     * Charts go through the same query path the dashboard uses, so a deck
     * shows what the dashboard shows - not a copy taken when the deck was
     * arranged.
     */
    async fetchDeck(deckId) {
        let payload;
        try {
            payload = await this.orm.call(
                "dashboard.presentation.deck", "get_presentation_slides",
                [deckId]);
        } catch (err) {
            this.state.warning = true;
            console.error("presentation: deck could not be read", err);
            return;
        }

        const sheetIds = [...new Set(
            payload.slides.flatMap(slide => slide.items
                .filter(item => item.item_type === "chart" && item.sheet_id)
                .map(item => item.sheet_id)))];

        let dataBySheet = {};
        let configs = [];
        if (sheetIds.length) {
            try {
                dataBySheet = await this.orm.call(
                    "dashboard.sheet", "fetch_sheet_data",
                    [sheetIds, this.deckFilterPayload(payload.slides)]);
                configs = await this.orm.read("dashboard.sheet", sheetIds, [
                    "name", "type", "measure", "dimension", "dimension_axis",
                    ...KPI_SHEET_FIELDS,
                ]);
                const styling = await fetchSheetStyling(this.orm, sheetIds);
                configs.forEach(c => Object.assign(c, styling[c.id] || {}));
            } catch (err) {
                console.error("presentation: deck chart data failed", err);
            }
        }
        const configById = Object.fromEntries(configs.map(c => [c.id, c]));

        this.state.deckSlides = payload.slides.map(slide => ({
            ...slide,
            items: slide.items.map(item => ({
                ...item,
                chart: item.item_type === "chart"
                    ? this.deckChartValue(item, configById[item.sheet_id],
                                          dataBySheet[item.sheet_id] ?? [])
                    : null,
            })),
        }));

        this.chartData.data = [];
        this.chartData.style = { height: "100%", width: "100%", "margin-top": "0" };
        this.chartData.theme = payload.theme;
        this.chartData.themeData = payload.theme_json || {};
        this.autoSlide = payload.auto_slide;
        this.autoSlideTime = payload.auto_slide_time;
        this.titlePage = payload.title_page;
        this.heading = payload.title_page_heading;
        this.subheading = payload.title_page_subheading;
    }

    /** One box's chart, in the shape GraphTile expects. */
    /**
     * The `filters` argument for fetch_sheet_data, for the boxes the deck
     * was arranged to show the way their dashboard shows them.
     *
     * The editor decided this per box and stored it; presenting only
     * carries the decision out, so a chart looks on the screen the way it
     * looked while the deck was being put together. Values come from the
     * dashboard's session state, the same place the dashboard reads them.
     */
    deckFilterPayload(slides) {
        const toggled = (slides || []).flatMap((slide) => slide.items.filter(
            (item) => item.item_type === "chart" && item.sheet_id
                      && item.use_dashboard_filters && item.config_id));
        if (!toggled.length) {
            return {};
        }
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
        if (!Object.keys(values).length) {
            return {};
        }
        const payload = {};
        for (const item of toggled) {
            payload[String(item.sheet_id)] = {
                config_id: item.config_id,
                values,
            };
        }
        return payload;
    }

    deckChartValue(item, config, data) {
        if (!config) {
            return null;
        }
        let measuresList;
        try {
            measuresList = eval(config.measure);
        } catch (e) {
            measuresList = [];
        }
        const measureAliases = Array.isArray(measuresList)
            ? measuresList.map(m => typeof m === 'object' ? m.alias : m)
            : [];
        const measureNames = (Array.isArray(measuresList) ? measuresList : []).reduce((acc, m) => {
            if (typeof m === 'object' && (m.isPreset || m.value)) {
                acc[m.alias] = m.value;
            }
            return acc;
        }, {});
        const measures = resolveMeasures(
            data, config.dimension, measureAliases,
            config.series_dimension, config.series_labels);
        return {
            id: config.id,
            data,
            name: config.name,
            type: config.type,
            measures,
            measureNames,
            dimension: config.dimension,
            dimension_axis: config.dimension_axis,
            kpi: config.type === "kpi" ? kpiSettingsFromSheet(config) : false,
            color_mappings: config.color_mappings || [],
            annotations: config.annotations || [],
        };
    }

    /** A box's place on the slide, as CSS grid coordinates. */
    deckItemStyle(item) {
        return `grid-column: ${item.x + 1} / span ${item.w};` +
               `grid-row: ${item.y + 1} / span ${item.h};`;
    }

    /** A note or text box's HTML, as markup rather than escaped text. */
    deckItemMarkup(item) {
        return markup(item.html || "");
    }

    /**
     * The note as markup, so it renders as HTML rather than escaped text.
     *
     * An HTML field arrives over RPC as a plain string and t-out escapes
     * strings, so without this the slide would show the literal tags.
     * Trusting the value is sound because the field is sanitize=True:
     * scripts and event handlers are stripped when the note is written.
     */
    noteMarkup(data) {
        return markup(data.note_html || "");
    }

    /**
     * Card style for the chart on a note slide.
     *
     * The ordinary slide style is sized to the viewport; here the chart
     * lives in a grid column instead, so it fills its own box rather than
     * the screen. Passing the viewport style through is what would push the
     * note off the row and stack it underneath.
     */
    noteChartStyle(data) {
        return { ...this.chartData.style, width: "100%", height: "100%" };
    }

    /** The chart's share of a note slide, clamped to a usable range. */
    noteRatio(data) {
        const ratio = Number(data.note_ratio) || 60;
        return Math.min(80, Math.max(25, ratio));
    }

    /**
     * Drag the divider between a chart and its note.
     *
     * The column width follows the pointer by writing the inline style
     * directly: going through component state would re-render the slide on
     * every pointer move, and re-rendering a GraphTile mid-drag tears the
     * chart down and rebuilds it. The ratio is saved once, on release, and
     * a failure to save leaves the new split on screen - it is only the
     * remembering that failed.
     */
    startNoteDrag(ev, data) {
        ev.preventDefault();
        const split = ev.currentTarget.closest(".cy-note-split");
        if (!split) {
            return;
        }
        const bounds = split.getBoundingClientRect();
        const started = this.noteRatio(data);
        let ratio = started;

        const onMove = (moveEv) => {
            if (!bounds.width) {
                return;
            }
            const pct = ((moveEv.clientX - bounds.left) / bounds.width) * 100;
            ratio = Math.min(80, Math.max(25, Math.round(pct)));
            split.style.gridTemplateColumns = `${ratio}% 10px 1fr`;
        };

        const onUp = async () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
            if (ratio === started) {
                return;
            }
            data.note_ratio = ratio;
            const configId = this.props.action?.context?.rec_id;
            if (!configId) {
                return;
            }
            try {
                await this.orm.call("dashboard.sheet.note", "save_ratio",
                                    [data.id, configId, {}, ratio]);
            } catch (error) {
                this.notification?.add(
                    _t("The new split could not be saved."), { type: "danger" });
                throw error;
            }
        };

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    }

    async exitPresentation() {
        if (this._leaving) {
            return;
        }
        this._leaving = true;
        this.fullScreen = false;
        this.toggleSideAndHeader();
        if (document.fullscreenElement) {
            try {
                await document.exitFullscreen();
            } catch (e) {}
        }
        if (this.saveContext?.mode === "deck") {
            await this.actionService.doAction(
                "cyllo_analytics.action_presentation_deck", { clearBreadcrumbs: true });
        } else {
            browser.history.go(-1);
        }
    }

    /**
     * Trigger full-screen mode for the presentation.
     */
    triggerFullScreen() {
        document.documentElement.requestFullscreen();
        this.state.exit = false;
        this.fullScreen = true
        this.toggleSideAndHeader();
    }
}

PresentationMaker.template = "cyllo_analytics.PresentationMaker"
PresentationMaker.components = {
    GraphTile, Table, KpiSheetChart
}
registry.category("actions").add("presentation_maker", PresentationMaker);