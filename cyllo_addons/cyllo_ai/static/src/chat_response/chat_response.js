/** @odoo-module **/
import { Component, onWillStart, onMounted, useState, useRef, onPatched, onWillDestroy, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";

// SheetJS, vendored (0.20.3, Apache-2.0). Deliberately NOT in the asset bundle:
// it is ~930KB and only needed when someone clicks "download table". Loaded on
// demand instead, so it costs nothing on a normal page load. Point this at the
// CDN instead if you would rather not carry the file.
const XLSX_LIB = "/cyllo_ai/static/src/lib/xlsx/xlsx.full.min.js";

// Where the model asks for the chart to be placed within its answer. Matches the
// marker alone in its own paragraph (how markdown renders it on its own line) or
// bare, if the model inlined it.
const CHART_MARKER_RE = /<p>\s*\[\[chart\]\]\s*<\/p>|\[\[chart\]\]/i;
// Same pattern, global: used to sweep up any marker beyond the first.
const CHART_MARKER_RE_ALL = new RegExp(CHART_MARKER_RE.source, "gi");


export class ChatResponse extends Component {
    static props = {
        // Number for a persisted record; String for the temporary ids used
        // while a turn is in flight, and for history rows without one.
        id: { type: [Number, String], optional: true },
        text: { type: String, optional: true },
        html: { type: String, optional: true },
        chart_config: {
            validate: (value) => value === null || typeof value === 'object',
            optional: true
        },
        // A host-injected list of chart suggestions rendered as Apply cards.
        // Each: {title, question, reason, dimension:{label,...}, measure:{label,...}}.
        suggestions: {
            validate: (value) => value === null || Array.isArray(value),
            optional: true
        },
        // An opaque payload for a host-contributed chat-chart component (e.g.
        // analytics renders the sheet's own GraphTile from it). Rendered via the
        // "cyllo_ai.chat_chart" registry slot, so cyllo_ai stays chart-agnostic.
        chart: {
            validate: (value) => value === null || typeof value === 'object',
            optional: true
        },
        // A host-contributed interactive widget: { key, props }. Rendered from
        // the "cyllo_ai.chat_widgets" registry by key, so host modules can drop
        // in flows (e.g. the analytics "quick dashboard" builder) without
        // cyllo_ai knowing them.
        widget: {
            validate: (value) => value === null || typeof value === 'object',
            optional: true
        },
        usage: {
            validate: (value) => value === null || typeof value === 'object',
            optional: true
        },
        timestamp: { type: [String, Boolean], optional: true },
        streaming: { type: Boolean, optional: true },
        // Agent trajectory: the tools this answer used, and how long the tool
        // phase ran before the first answer token.
        steps: {
            validate: (value) => value === null || Array.isArray(value),
            optional: true
        },
        thinkingMs: { type: Number, optional: true },
        // The answer was produced but could not be written to chatbot.history,
        // so it will not survive a reload.
        unsaved: { type: Boolean, optional: true },
        isPlaying: { type: Boolean, optional: true },
        onPlay: { type: Function, optional: true },
        onStop: { type: Function, optional: true },
        interrupted: { type: Boolean, optional: true },
        onInterruptResponse: { type: Function, optional: true },
        onEditRequest: { type: Function, optional: true },
        onLoad: { type: Function, optional: true },
    };

    setup() {
        super.setup(...arguments);

        this.chartContainer = useRef("chartContainer");
        this.popupChartContainer = useRef("popupChartContainer");
        this.bubbleRef = useRef("bubble");
        this.bubbleAfterRef = useRef("bubbleAfter");
        this.state = useState({
            stepsOpen: false,
            hideButtons: false,
            copied: false,
            showChartOptions: false,
            chatSelectedType: "bar",
            popupSelectedType: "bar",
            validGraph: false,
            defaultChart: "",
            chartTypes: [
                { name: "default", label: "Default", icon: "/cyllo_ai/static/src/img/default-graph.svg" },
                { name: "bar", label: "Bar", icon: "/cyllo_ai/static/src/img/bar.svg" },
                { name: "line", label: "Line", icon: "/cyllo_ai/static/src/img/line.svg" },
                { name: "pie", label: "Pie", icon: "/cyllo_ai/static/src/img/pie.svg" },
                { name: "donut", label: "Donut", icon: "/cyllo_ai/static/src/img/donut.svg" },
                { name: "scatter", label: "Scatter", icon: "/cyllo_ai/static/src/img/scatter.svg" },
                // Add more types and their icons here
            ],
            chart_config: this.props.chart_config ? JSON.parse(JSON.stringify(this.props.chart_config)) : null,
            showGraphPopup: false,
            hasTable: false,
        })
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.resizeObserver = null;

        onMounted(() => {
            setTimeout(() => {
                this.initChart();
                this.resizeChart();
            }, 300);

            // Initialize ResizeObserver
            this.resizeObserver = new ResizeObserver(() => {
                this.resizeChart();
            });

            if (this.chartContainer.el) {
                this.resizeObserver.observe(this.chartContainer.el);
            }
            if (this.popupChartContainer.el) {
                this.resizeObserver.observe(this.popupChartContainer.el);
            }

            // Convert String object to primitive string and check for table tags
            const htmlContent = String(this.props.html || '');
            const hasTableTag = htmlContent.includes('<table');

            this.state.hasTable = hasTableTag;
        });

        onWillDestroy(() => {
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }
        });

        // Streaming turns mount this component BEFORE chart_config exists (the
        // marker/config arrives on a later "chart" SSE event, patched onto the
        // same message object). The chart container div is only in the template
        // when chart_config is truthy, so on first mount it isn't there yet, and
        // onMounted's initChart() never sees it. Re-run init whenever the config
        // changes so a chart that arrives after mount actually gets drawn.
        this._lastChartConfigJSON = this.props.chart_config ? JSON.stringify(this.props.chart_config) : null;
        onPatched(() => {
            const nextJSON = this.props.chart_config ? JSON.stringify(this.props.chart_config) : null;
            if (nextJSON !== this._lastChartConfigJSON) {
                this._lastChartConfigJSON = nextJSON;
                if (this.chartContainer.el && this.resizeObserver) {
                    this.resizeObserver.observe(this.chartContainer.el);
                }
                setTimeout(() => {
                    this.initChart();
                    this.resizeChart();
                }, 0);
            }
        });
    }

    async onWillStart() {
        this.baseChartConfig = this.props.chart_config ? JSON.parse(JSON.stringify(this.props.chart_config)) : null;
        this.state.chart_config = this.baseChartConfig;
    };

    /** Copy the visible response text to the clipboard, with brief feedback. */
    /** Both halves of the answer — it is split in two when a [[chart]] marker
     *  places the chart in the middle. */
    _answerEls() {
        return [this.bubbleRef?.el, this.bubbleAfterRef?.el].filter(Boolean);
    }

    async copyResponse() {
        let text = "";
        const els = this._answerEls();
        if (els.length) {
            text = els.map((e) => e.innerText || e.textContent || "").join("\n\n");
        }
        if (!text) {
            // Fallback: strip the rendered html, else the raw markdown.
            const html = this.props.html ? String(this.props.html) : "";
            if (html) {
                const tmp = document.createElement("div");
                tmp.innerHTML = html;
                text = tmp.innerText || tmp.textContent || "";
            } else {
                // Raw markdown still carries the marker — never copy it.
                text = (this.props.text || "").replace(CHART_MARKER_RE, "").trim();
            }
        }
        text = (text || "").trim();
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            this.state.copied = true;
            setTimeout(() => { this.state.copied = false; }, 1500);
        } catch (e) {
            console.error("copy failed", e);
        }
    }

    /**
     * Spoken-friendly prose of this response: the rendered bubble with tables,
     * code blocks and link URLs removed (keeps link text), collapsed whitespace.
     */
    spokenText() {
        const els = this._answerEls();
        const host = document.createElement("div");
        if (els.length) {
            els.forEach((e) => host.appendChild(e.cloneNode(true)));
        } else {
            host.innerHTML = String(this.props.html || "");
        }
        host.querySelectorAll("table, pre, code").forEach((n) => n.remove());
        const text = (host.innerText || host.textContent || "")
            .replace(/https?:\/\/\S+/g, "")   // drop bare URLs
            .replace(/\s+/g, " ")
            .trim();
        return text;
    }

    /** Toggle read-aloud for this response. */
    togglePlay() {
        if (this.props.isPlaying) {
            this.props.onStop?.();
        } else {
            const text = this.spokenText();
            if (text) this.props.onPlay?.(this.props.id, text);
        }
    }

    /** Apply a suggestion card — broadcast to whichever host screen listens
     *  (e.g. the analytics sheet applies it via CY_AI:APPLY_SUGGESTION). The
     *  chat itself stays decoupled from what "apply" means. */
    onApplySuggestion(suggestion) {
        this.env.bus.trigger("CY_AI:APPLY_SUGGESTION", { suggestion });
    }

    /** The chat-chart component a host module registered (or null). Lets the
     *  chat render a real host chart (e.g. the analytics GraphTile) without
     *  cyllo_ai importing it. */
    get chartComponent() {
        return registry.category("cyllo_ai.chat_chart").get("component", null);
    }

    /** The interactive widget component a host module registered under this
     *  message's widget key (or null) — e.g. the analytics quick-dashboard flow. */
    get widgetComponent() {
        const key = this.props.widget && this.props.widget.key;
        return key ? registry.category("cyllo_ai.chat_widgets").get(key, null) : null;
    }

    /** Compact token formatter: 463 → "463", 22240 → "22k", 1240 → "1.2k". */
    formatTokens(n) {
        n = n || 0;
        if (n < 1000) return String(n);
        if (n < 1000000) {
            const k = n / 1000;
            return (n < 10000 ? k.toFixed(1).replace(/\.0$/, "") : Math.round(k)) + "k";
        }
        return (n / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
    }

    /** Muted "tokens used" label for this response, or "" when unknown. */
    /** The chart's title, taken out of the ECharts option so it can be laid out
     *  in the DOM beside the toolbar icons instead of being painted inside the
     *  canvas (where nothing else can align with it). */
    get chartTitle() {
        return this.props.chart_config?.title?.text || "";
    }

    /** ECharts must not draw the title as well, or it appears twice and eats
     *  vertical space that belongs to the plot. `show: false` rather than
     *  deleting the key, so nothing depends on merge semantics. */
    _withoutTitle(config) {
        if (!config) return config;
        return { ...config, title: { ...(config.title || {}), show: false } };
    }

    /** Is there actually a chart to position? */
    get hasPlacedChart() {
        return !!(this.props.chart_config || (this.props.chart && this.chartComponent));
    }

    /** The answer, split at the model's [[chart]] marker into the part before the
     *  chart and the part after it.
     *
     *  No marker -> everything in `before`, chart falls to the end (unchanged
     *  behaviour). Marker but no chart (the tool failed, or a reloaded turn kept
     *  the text but not the config) -> the marker is stripped and the answer stays
     *  in one piece, so `[[chart]]` never leaks to the user. */
    get answerParts() {
        const raw = String(this.props.html || "");
        const m = raw.match(CHART_MARKER_RE);
        if (!m) {
            return { before: this.props.html || "", after: "" };
        }
        // Only the FIRST marker positions the chart. Any further ones are
        // stripped rather than left to render as literal "[[chart]]" text: the
        // prompt says to use it once, but models drift, and a stray marker in an
        // answer looks like a broken product.
        const strip = (s) => s.replace(CHART_MARKER_RE_ALL, "");
        const before = strip(raw.slice(0, m.index));
        const after = strip(raw.slice(m.index + m[0].length));
        if (!this.hasPlacedChart) {
            return { before: markup(before + after), after: "" };
        }
        return { before: markup(before), after: markup(after) };
    }

    get steps() {
        return this.props.steps || [];
    }

    /**
     * Structured view of an operation-preview turn, parsed out of the
     * markdown `_describe_operation` produces server-side (chatbot_tools.py).
     * Deliberately NOT gated on `props.interrupted`: that flag flips to false
     * once the turn is resolved (proceeded/cancelled) or the page is reloaded
     * from chatbot.history, but the card should keep its look either way —
     * only the action buttons underneath care whether it's still pending.
     * Returns null for any message that doesn't match the fixed shape, which
     * falls back to the plain bubble untouched.
     */
    get confirmCard() {
        const raw = String(this.props.text || "").replace(/\\n/g, "\n");
        const actionMatch = raw.match(/\*\*Action:\*\*\s*(\w+)\s*—\s*(.+?)\s*\(([\w.]+)\)/);
        if (!actionMatch) return null;
        const [, action, modelLabel, modelName] = actionMatch;

        const ICONS = {
            create: "ri-add-large-line",
            update: "ri-pencil-line",
            delete: "ri-delete-bin-line",
            read: "ri-search-line",
        };
        const matchLine = raw.match(/\*\*Match:\*\*\s*(.+)/);
        const valuesLine = raw.match(/\*\*Values:\*\*\s*(.+)/);
        // Split on ", " only where it precedes another "field = " pair — a
        // plain ", ".split would break on a value that itself contains a
        // comma (e.g. name = 'Doe, John').
        const splitPairs = (line) =>
            line ? line.split(/,\s+(?=[A-Za-z_][A-Za-z0-9_.]*\s=\s)/) : [];
        const values = splitPairs(valuesLine && valuesLine[1]).map((pair) => {
            const m = pair.match(/^([A-Za-z_][A-Za-z0-9_.]*)\s=\s([\s\S]*)$/);
            return m ? { key: m[1], value: m[2] } : { key: pair, value: "" };
        });

        // The Match line is "<filter> → <display names>" once the backend has
        // resolved the domain to actual records (_describe_operation). Split
        // the names back out so the header can read "Update Contact Cyllo"
        // instead of burying the record's name in the raw filter row.
        let match = matchLine ? matchLine[1] : "";
        let matchNames = "";
        const arrowAt = match.indexOf(" → ");
        if (arrowAt !== -1) {
            matchNames = match.slice(arrowAt + 3).trim();
            match = match.slice(0, arrowAt).trim();
        }
        const names = matchNames ? matchNames.split(", ").filter(Boolean) : [];
        const namesLabel = names.length > 2
            ? `${names.slice(0, 2).join(", ")} +${names.length - 2} more`
            : names.join(", ");

        return {
            action,
            icon: ICONS[action] || "ri-flashlight-line",
            modelLabel,
            modelName,
            subject: namesLabel ? `${modelLabel} ${namesLabel}` : modelLabel,
            values,
            match,
        };
    }

    /** Whatever the model said BEFORE deciding to call the tool (e.g. "Sure,
     *  I'll create that contact for you."), so it can render above the confirm
     *  card instead of being discarded when the card takes over. `null` when
     *  there is nothing but the card's own preview markdown to show — an empty
     *  bubble above the card would just be a blank pill. */
    get confirmLeadHtml() {
        if (!this.confirmCard) return null;
        const html = this.answerParts.before;
        const stripped = String(html || "").replace(/<[^>]*>/g, "").trim();
        return stripped ? html : null;
    }

    /** Whether this answer did enough work to be worth reporting.
     *
     *  Only the LABEL is conditional — the avatar beside it always renders.
     *  Those are two different things and conflating them was a mistake: a
     *  tool-free reply without any measured thinking time should lose its
     *  "Worked for 0s" noise, not its identity, or it appears as unattributed
     *  text next to responses that have an avatar. */
    get showWorked() {
        return this.steps.length > 0 || (this.props.thinkingMs || 0) > 0;
    }

    /** "Worked for 8s · 3 steps" — deliberately not "Thought for": these are
     *  tool calls against the ERP, not reasoning tokens. */
    get workedLabel() {
        const ms = this.props.thinkingMs || 0;
        const secs = ms >= 1000 ? `${Math.round(ms / 1000)}s` : `${ms}ms`;
        const n = this.steps.length;
        if (!n) return `Worked for ${secs}`;
        return `Worked for ${secs} · ${n} step${n === 1 ? "" : "s"}`;
    }

    /** While streaming, the head shows what the agent is doing right now. */
    get liveLabel() {
        const open = [...this.steps].reverse().find((s) => s.ok === null);
        if (open) return `${open.label}…`;
        return this.steps.length ? "Writing answer…" : "Working…";
    }

    toggleSteps() {
        if (this.steps.length) this.state.stepsOpen = !this.state.stepsOpen;
    }

    get tokenLabel() {
        const u = this.props.usage;
        if (!u || !u.total) return "";
        const f = (n) => this.formatTokens(n);
        return `${f(u.prompt)} in · ${f(u.completion)} out · ${f(u.total)} tokens`;
    }

    /** Localized date+time for this response, or "" when unknown. Server
     * timestamps are UTC ("YYYY-MM-DD HH:MM:SS"); live ones are ISO with 'Z'.
     * Both are parsed as UTC and shown in the user's local timezone. */
    get timeLabel() {
        const ts = this.props.timestamp;
        if (!ts) return "";
        const s = String(ts);
        const d = new Date(s.includes("T") ? s : s.replace(" ", "T") + "Z");
        if (isNaN(d.getTime())) return s;
        return d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
    }

    initChart() {
        try {
            const { chart_config } = this.props;
            const popupRef = this.popupChartContainer?.el;
            const baseRef = this.chartContainer?.el;
            const container = popupRef || baseRef;
            if (!container || typeof echarts === "undefined" || !chart_config) return;

            // Dispose existing chart instance
            if (container.__echarts_instance__) echarts.dispose(container);

            // Deep clone config (avoid mutating props)
            let config = JSON.parse(JSON.stringify(chart_config));
            // ---- Title tweaks ----
            if (config.title) {
                const titles = Array.isArray(config.title) ? config.title : [config.title];
                titles.forEach(title => {
                    title.top ??= 10;
                    title.textStyle ??= {};
                    title.textStyle.fontSize ??= 16;
                    title.textStyle.fontWeight ??= "bold";
                });
                config.title = titles.length === 1 ? titles[0] : titles;
            }

            // ---- Legend tweaks ----
            // top was 40: room for the title this chart used to draw ON the
            // canvas. The title is now DOM (see _withoutTitle/chartTitle above,
            // shown in .cy-ai-chart-head), so that reserved band is dead space
            // above the legend now — drop it close to the canvas top instead.
            if (config.legend) {
                const legends = Array.isArray(config.legend) ? config.legend : [config.legend];
                legends.forEach(legend => {
                    legend.top ??= 8;
                    legend.left ??= "center";
                });
                config.legend = legends.length === 1 ? legends[0] : legends;
            }

            // ---- Grid tweaks ----
            // Left unset, echarts' own default grid.top assumes a title bar
            // above it (another leftover from the in-canvas title) and adds
            // extra padding on top of the legend's own space — same dead-space
            // problem as the legend. Pin it to just clear the legend.
            if (config.grid) {
                const grids = Array.isArray(config.grid) ? config.grid : [config.grid];
                grids.forEach(grid => {
                    grid.top ??= config.legend ? 36 : 12;
                });
                config.grid = grids.length === 1 ? grids[0] : grids;
            }

            // ---- X Axis tweaks ----
            if (config.xAxis) {
                const xAxis = Array.isArray(config.xAxis) ? config.xAxis : [config.xAxis];
                xAxis.forEach(axis => {
                    axis.axisLabel ??= {};
                    axis.axisLabel.hideOverlap ??= true;
                    axis.axisLabel.rotate ??= 45;
                    axis.axisLabel.margin ??= 10;
                    const formatterValue = axis.axisLabel.formatter
                    if (formatterValue) {
                        axis.axisLabel.formatter = function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                    else {
                        axis.axisLabel.formatter ??= function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                });
                config.xAxis = xAxis.length === 1 ? xAxis[0] : xAxis;
            }

            if (config.yAxis) {
                const yAxisArr = Array.isArray(config.yAxis) ? config.yAxis : [config.yAxis];
                yAxisArr.forEach(axis => {
                    axis.axisLabel ??= {};
                    axis.axisLabel.interval = 0;    // Show all y-axis labels
                    axis.axisLabel.hideOverlap = false;
                    const formatterValue = axis.axisLabel.formatter
                    if (formatterValue) {
                        axis.axisLabel.formatter = function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                    else {
                        axis.axisLabel.formatter ??= function (value) {
                            if (typeof (value) == 'number') {
                                if (value >= 1000000) return (value / 1000000) + 'M';
                                if (value >= 1000) return (value / 1000) + 'k';
                            }
                            else {
                                if (value.length > 10) {
                                    const parts = value.trim().split(/\s+/)
                                    if (parts.length == 2) {
                                        return `${parts[0][0]} ${parts[1]}`
                                    }
                                    else {
                                        return `${parts[0][0]} ${parts[parts.length - 1]}`
                                    }
                                }
                                return value;
                            }
                        }
                    }
                });
                config.yAxis = yAxisArr.length === 1 ? yAxisArr[0] : yAxisArr;
            }
            // ---- Convert to pie chart if required ----
            if (config.series?.[0]?.type === "pie") {
                config = this.convertToPie(config);
            }

            // ---- Add data zoom ----
            config.dataZoom = [
                { type: "inside", yAxisIndex: 0, start: 0, end: 100 },
                { type: "inside", xAxisIndex: 0, start: 0, end: 100 }
            ];

            // ---- Initialize chart ----
            const chart = echarts.init(container);
            chart.setOption(this._withoutTitle(config), {
                notMerge: true,
                replaceMerge: ["xAxis", "yAxis", "series", "grid", "legend"]
            });

            // ---- Set default graph + resize ----
            this.setDefaultGraph(config);
            requestAnimationFrame(() => chart.resize());

        } catch (err) {
            console.error("ECharts init error:", err);
        }
    }


    setDefaultGraph(chartConfig) {
        this.state.defaultChart = chartConfig;
    }

    resizeChart() {
        let container = this.chartContainer.el;
        if (this.popupChartContainer.el) {
            container = this.popupChartContainer.el;
        }
        if (!container || typeof echarts === "undefined") return;
        const chartInstance = echarts.getInstanceByDom(container);
        if (!chartInstance) return;
        try {
            chartInstance.resize();
        }
        catch (e) {
            console.warn("chart was not resized", e);
        }
    }

    onExpandGraph() {
        this.state.showGraphPopup = !this.state.showGraphPopup;
        this.state.popupSelectedType = "bar";
        setTimeout(() => {
            const container = this.state.showGraphPopup
                ? this.__owl__.refs.popupChartContainer
                : this.__owl__.refs.chartContainer;
            if (container) {
                this.initChart();
            }
        }, 100);
    }

    handleCancel() {
        // 'cancel' goes through the normal resume path, which both aborts the
        // pending operation and clears the history flag — no extra RPC needed
        // (the old /chatbot/set_interrupt call here was broken AND redundant).
        this.state.hideButtons = true;
        this.props.onInterruptResponse?.('cancel');
    }

    handleProceed() {
        this.state.hideButtons = true;
        this.props.onInterruptResponse?.('proceed');
    }

    handleEdit() {
        // No message is sent — the draft body is placed in the input box so
        // the user edits it directly; what they send is treated as a change
        // request (revised draft, new preview). Buttons stay visible.
        this.props.onEditRequest?.(this.extractDraftContent());
    }

    /**
     * Pull the draft body out of a preview message — the content between the
     * first and last `---` fences (the exact format prepare_email /
     * prepare_text_message produce). Prefers the raw markdown; falls back to
     * splitting the rendered html on <hr>. Returns "" when not parseable.
     */
    extractDraftContent() {
        const text = this.props.text || "";
        if (text) {
            const lines = text.replace(/\\n/g, "\n").split("\n");
            const fences = lines.reduce((acc, l, i) => {
                if (l.trim() === "---") acc.push(i);
                return acc;
            }, []);
            if (fences.length >= 2) {
                return lines.slice(fences[0] + 1, fences[fences.length - 1])
                    .join("\n").trim();
            }
        }
        const html = this.props.html ? String(this.props.html) : "";
        const parts = html.split(/<hr\s*\/?>/i);
        if (parts.length >= 3) {
            const tmp = document.createElement("div");
            tmp.innerHTML = parts.slice(1, -1).join("\n")
                .replace(/<br\s*\/?>/gi, "\n")
                .replace(/<\/p>/gi, "\n");
            return (tmp.textContent || "").replace(/\n{3,}/g, "\n\n").trim();
        }
        return "";
    }

    onGraphIconClick() {
        this.state.showChartOptions = !this.state.showChartOptions;
    }

    onChartTypeSelect = (type, isPopup = false) => {
        if (!isPopup) {
            this.state.chatSelectedType = type;
        }
        else {
            this.state.popupSelectedType = type;
        }
        this.state.showChartOptions = false;

        if (!this.props.chart_config) return;

        // Safely transform chart config based on type
        const updatedConfig = this.props.chart_config ? this.convertChartType(this.state.chart_config, type) : null;

        const container = this.state.showGraphPopup ? this.popupChartContainer.el : this.chartContainer.el;
        if (container && typeof echarts !== "undefined") {
            echarts.dispose(container);
            const chart = echarts.init(container);
            chart.clear();
            chart.setOption(this._withoutTitle(updatedConfig), {
                notMerge: true,
                replaceMerge: ['xAxis', 'yAxis', 'series', 'grid', 'legend']
            });
            setTimeout(() => chart.resize(), 300);
        }
    };

    // Utility function to deep clone config
    cloneConfig(config) {
        return JSON.parse(JSON.stringify(config));
    }

    extractChartData(config) {

        let labels = [];
        let values = [];

        // Try to find any series
        const series = Array.isArray(config.series) ? config.series[0] : config.series;

        if (!series) return { labels, values };

        // 1. Pie-like series → has name/value pairs
        if (Array.isArray(series.data) && series.data.length && series.data[0].name !== undefined) {
            labels = series.data.map(item => item.name);
            values = series.data.map(item => item.value);

            // 2. Axis-based chart → xAxis or yAxis data
        } else if (config.xAxis?.data && config.xAxis.data.length !== 0) {
            labels = config.xAxis.data;
            values = series.data || [];

        } else if (config.yAxis?.data?.length) {
            labels = config.yAxis.data;
            values = series.data || [];

            // 3. Scatter/bubble/other → look for object values
        } else if (Array.isArray(series.data)) {
            if (typeof series.data[0] === "object") {
                labels = series.data.map((_, idx) => `Point ${idx + 1}`);
                values = series.data.map(item => item.value || item[1] || 0);
            } else {
                // fallback simple array
                const configData = this.hasData(config)
                labels = configData;
                values = series.data;
            }
        }

        return { labels, values };
    }

    hasData(obj) {
        if (!obj || typeof obj !== 'object') return false;

        // If this object has a `data` array with length > 0
        if (Array.isArray(obj.data) && obj.data.length > 0) {
            return obj.data;
        }
        // Recursively check all properties
        for (let key in obj) {
            const found = this.hasData(obj[key]);
            if (found) return found;
        }
        return false;
    }

    convertToDefault(config) {
        const newConfig = this.state.defaultChart
        return newConfig
    }

    // Convert any chart to pie chart
    convertToPie(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);
        // Create pie chart data format
        const pieData = labels.map((name, index) => ({
            name: name,
            value: values[index] || 0
        }));
        // Remove incompatible properties
        delete newConfig.xAxis;
        delete newConfig.yAxis;
        delete newConfig.grid;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;


        // Configure pie chart specific properties
        newConfig.tooltip = {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
        };

        newConfig.legend = {
            orient: 'vertical',
            left: 'left',
            data: labels,
            top: 30,
        };

        newConfig.series = [{
            name: seriesName,
            type: 'pie',
            radius: '80%',
            center: ['50%', '60%'],
            label: {
                show: true ? this.state.showGraphPopup : false
            },
            labelLine: {
                show: true ? this.state.showGraphPopup : false
            },
            data: pieData,
            avoidLabelOverlap: true,
            left: 100,
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }];

        return newConfig;
    }

    // Convert any chart to horizontal bar chart
    convertToBar(config) {
        if (!config) return null;

        let newConfig = this.cloneConfig(config);
        // ✅ Skip if already a bar chart
        const isBar = Array.isArray(config.series) && config.series.some(s => s.type === "bar");
        if (isBar) {
            newConfig = this.state.defaultChart;
            return newConfig
        }
        // Extract relevant chart data
        const { labels = [], values = [], seriesName = "Series" } = this.extractChartData(config);
        //
        //  Clean up pie/polar-specific properties in one pass
        ["polar", "angleAxis", "radiusAxis", "legend", "tooltip", "toolbox"].forEach(key => delete newConfig[key]);

        // Define new bar chart layout

        if (newConfig.title) {
            const titles = Array.isArray(newConfig.title) ? newConfig.title : [newConfig.title];
            titles.forEach(title => {
                title.top ??= 10;
                title.textStyle ??= {};
                title.textStyle.fontSize ??= 16;
                title.textStyle.fontWeight ??= "bold";
            });
            newConfig.title = titles.length === 1 ? titles[0] : titles;
        }

        // ---- Legend tweaks ----
        if (newConfig.legend) {
            const legends = Array.isArray(newConfig.legend) ? newConfig.legend : [newConfig.legend];
            legends.forEach(legend => {
                legend.top ??= 40;
                legend.left ??= "center";
            });
            newConfig.legend = legends.length === 1 ? legends[0] : legends;
        }

        // ---- X Axis tweaks ----
        if (newConfig.xAxis) {
            const xAxis = Array.isArray(newConfig.xAxis) ? newConfig.xAxis : [newConfig.xAxis];
            xAxis.forEach(axis => {
                axis.axisLabel ??= {};
                axis.axisLabel.hideOverlap ??= true;
                axis.axisLabel.rotate ??= 45;
                axis.axisLabel.margin ??= 10;
                axis.axisLabel.formatter ??= function (value) {
                    if (value >= 1000000) return (value / 1000000) + 'M';
                    if (value >= 1000) return (value / 1000) + 'k';
                    return value
                }
            });
            newConfig.xAxis = xAxis.length === 1 ? xAxis[0] : xAxis;
        }

        if (newConfig.yAxis) {
            const yAxisArr = Array.isArray(newConfig.yAxis) ? newConfig.yAxis : [newConfig.yAxis];
            yAxisArr.forEach(axis => {
                axis.axisLabel ??= {};
                axis.axisLabel.interval = 0;    // Show all y-axis labels
                axis.axisLabel.hideOverlap = false;
                axis.axisLabel.formatter ??= function (value) {
                    if (value >= 1000000) return (value / 1000000) + 'M';
                    if (value >= 1000) return (value / 1000) + 'k';
                    return value
                }
            });
            newConfig.yAxis = yAxisArr.length === 1 ? yAxisArr[0] : yAxisArr;
        }


        // ---- Convert to pie chart if required ----
        if (newConfig.series?.[0]?.type === "pie") {
            newConfig = this.convertToPie(newConfig);
        }

        // ---- Add data zoom ----
        newConfig.dataZoom = [
            { type: "inside", yAxisIndex: 0, start: 0, end: 100 },
            { type: "inside", xAxisIndex: 0, start: 0, end: 100 }
        ];

        return newConfig;
    }

    // Convert any chart to line chart
    convertToLine(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);

        // Remove pie and bar specific properties
        delete newConfig.legend;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;

        newConfig.tooltip = {
            trigger: 'axis'
        };

        newConfig.grid = {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        };

        newConfig.xAxis = {
            type: 'category',
            data: labels,
            boundaryGap: false,
            axisLabel: {
                hideOverlap: true,
                rotate: 45,
                margin: 10
            }
        };

        newConfig.yAxis = {
            type: 'value',
            axisLabel: {
                hideOverlap: true,
                formatter: value => value >= 1000 ? value / 1000 + 'k' : value
            }
        };

        newConfig.series = [{
            name: seriesName,
            type: 'line',
            data: values,
            smooth: true
        }];

        newConfig.dataZoom = [
            {
                type: 'inside',
                yAxisIndex: 0,
                start: 0,
                end: 100
            },
            {
                type: 'inside',
                xAxisIndex: 0,
                start: 0,
                end: 100
            }
        ];
        return newConfig;
    }

    // Convert any chart to scatter plot
    convertToScatter(config) {
        const newConfig = this.cloneConfig(config);
        const { labels, values, seriesName } = this.extractChartData(config);

        // Create scatter plot data format [x, y] pairs
        // For single series data, use index as x-axis and value as y-axis
        const scatterData = values.map((value, index) => [index, value]);

        // Remove pie chart specific properties
        delete newConfig.legend;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;

        // Configure scatter plot properties
        newConfig.tooltip = {
            trigger: 'item',
            formatter: function (params) {
                const label = labels[params.data[0]] || `Point ${params.data[0]}`;
                return `${seriesName}<br/>${label}: ${params.data[1]}`;
            }
        };

        newConfig.grid = {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        };

        newConfig.xAxis = {
            type: 'value',
            scale: true,
            name: 'Category Index'
        };

        newConfig.yAxis = {
            type: 'value',
            scale: true,
            name: seriesName
        };

        newConfig.series = [{
            name: seriesName,
            type: 'scatter',
            data: scatterData,
            symbolSize: 8,
            emphasis: {
                focus: 'series'
            },
            itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(120, 36, 50, 0.5)',
                shadowOffsetY: 5,
                color: {
                    type: 'radial',
                    x: 0.4,
                    y: 0.3,
                    r: 1,
                    colorStops: [{
                        offset: 0,
                        color: 'rgb(251, 118, 123)'
                    }, {
                        offset: 1,
                        color: 'rgb(204, 46, 72)'
                    }]
                }
            }
        }];
        newConfig.dataZoom = [
            {
                type: 'inside',
                yAxisIndex: 0,
                start: 0,
                end: 100
            },
            {
                type: 'inside',
                xAxisIndex: 0,
                start: 0,
                end: 100
            }
        ];
        return newConfig;
    }

    // Convert any chart to donut chart
    convertToDonut(config) {
        const newConfig = this.convertToPie(config);
        delete newConfig.xAxis;
        delete newConfig.yAxis;
        delete newConfig.grid;
        delete newConfig.polar;
        delete newConfig.angleAxis;
        delete newConfig.radiusAxis;
        // Modify pie config for donut
        newConfig.series[0].radius = ['40%', '80%'];
        return newConfig;
    }
    // Main converter function using strategy pattern
    chartConverters() {
        return {
            default: this.convertToDefault.bind(this),
            pie: this.convertToPie.bind(this),
            bar: this.convertToBar.bind(this),
            line: this.convertToLine.bind(this),
            donut: this.convertToDonut.bind(this),
            scatter: this.convertToScatter.bind(this)
        }
    }

    convertChartType(config, targetType) {
        const converter = this.chartConverters()[targetType];
        if (!converter) {
            return config;
        }
        return converter(config);
    }

    async downloadTable() {
        // Get the HTML content
        const htmlContent = String(this.props.html || '');

        // Create a temporary div to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;

        // Find the table element
        const table = tempDiv.querySelector('table');

        if (!table) {
            console.error('No table found in the message');
            return;
        }

        // Fetch the spreadsheet library the first time it is actually needed.
        // loadJS de-duplicates, so repeated clicks reuse the loaded script.
        if (typeof window.XLSX === "undefined") {
            try {
                await loadJS(XLSX_LIB);
            } catch (err) {
                console.error("Cyllo AI: could not load the spreadsheet library", err);
            }
        }
        if (typeof window.XLSX?.utils?.table_to_book !== "function") {
            // Tell the user rather than failing silently under their click.
            this.notification.add(
                "The spreadsheet library could not be loaded, so this table "
                + "can't be exported right now.",
                { type: "warning" });
            return;
        }

        // Convert HTML table to workbook using SheetJS
        const workbook = window.XLSX.utils.table_to_book(table, {sheet: "Sheet1"});

        // Generate filename with timestamp
        const timestamp = new Date().toISOString().slice(0, 10);
        const filename = `chatbot_table_${timestamp}.xlsx`;

        // Trigger download
        window.XLSX.writeFile(workbook, filename);

    }
}
ChatResponse.template = "ChatResponse";
