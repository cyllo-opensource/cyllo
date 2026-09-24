/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ConfigurationDialog } from "./configuration_dialog";
import { MenuDialog } from "./menu_dialog_box";
import { DeleteDialog } from "./delete_dialog_box";
import { ThemeMaker } from "./theme_maker";
import { ExplainAIModal } from "./explain_with_ai/explain_with_ai_modal"
import { CyAnalyticMixin } from "@cyllo_analytics/js/mixin/cy_dashboard_mixin"
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { GraphTile } from "@cyllo_analytics/js/presentation/components/graph_tile";
import { useResize } from "@cyllo_base/js/hooks"
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { KpiSheet } from "@cyllo_analytics/js/KpiSheet";
import { Table } from "@cyllo_analytics/js/table/table";
import { KpiSheetChart } from "@cyllo_analytics/js/kpi_sheet_chart";
import { _t } from "@web/core/l10n/translation";
import { SheetDeleteDialog } from "./cyllo_sheet";
import { AlertConfigurationDialog } from "./alert_configuration_dialog";
const { Component, useRef, useState, onMounted, onWillStart, useEffect, status, useExternalListener, onWillUnmount } = owl;

export class CylloDashboard extends CyAnalyticMixin(Component) {
    /** Class for creating a dashboard component */
    setup() {
        super.setup();
        this._t = _t;  // expose for template-side translation of dynamic labels
        this.tourService = useService("tour_service");
        useResize("chart-container", this.resizeContainer.bind(this));
        this.filter_dropdown = useRef('filter_dropdown')
        this.graph = useRef('graph')
        this.container = useRef('chart-container')
        this.items = []
        this.dialogService = useService("dialog")
        this.notification = useService("notification")
        this.ui = useState(useService("ui"))
        this.vals = []
        this.chartImages = {}
        this.refreshObject = {
            refresh: false,
            currentLen: 0
        }
        useBus(this.env.bus, "SIDEBAR_MENU_TOGGLE", ({ detail: { isSidebarOn } }) => {
            /*
            * To Resize the charts when the menu is toggled
            * */
            if (!this.state.originalWidth) {
                this.state.originalWidth = this.state.width
            }
            const ref = this.__owl__.bdom.parentEl
            const { width } = ref.getBoundingClientRect()
            const adjWidth = (width * 0.95) / 12
            this.state.width = isSidebarOn ? this.state.originalWidth : adjWidth
            setTimeout(() => {
                if (status(this) !== "destroyed") {
                    this.env.bus.trigger("REFRESH_GRAPH") //Force Render
                }
            }, 100)
        })
        useEffect(() => {
            this.env.bus.trigger("REFRESH_GRAPH")
        }, () => [this.state.width, this.ui.size]);
        useEffect(() => {
            const bannerEl = this.dashboard.el.querySelector('.o_pj_dashboard');
            var root = document.querySelector(':root');
            if (this.bannerState.banner.length) {
                const {
                    image_1920
                } = this.bannerState.banner[0];
                if (!image_1920) {
                    return root?.style.setProperty('--banner-image-url', `url('')`);
                }
                const imageUri = `data:image/svg+xml;base64,${image_1920}`;
                fetch(imageUri)
                    .then(response => response.text())
                    .then(svgData => {
                        const parser = new DOMParser();
                        const svgDoc = parser.parseFromString(svgData, 'image/svg+xml');
                        var {
                            theme_color_ids: newColors, title
                        } = this.themeState.theme
                        newColors = newColors.slice(1, newColors.length - 1);
                        for (let i = 0; i <= 7; i++) {
                            const circles = svgDoc.querySelectorAll(`.st${i}`);
                            if (circles.length) {
                                circles.forEach((circle) => {
                                    var index = i >= newColors.length ? Math.floor(Math.random() * newColors.length) : i;
                                    var color = newColors[index] == title ? newColors[Math.floor(Math.random() * newColors.length)] : newColors[index]
                                    circle.style.fill = color;
                                });
                            }
                        }
                        const serializedSvg = new XMLSerializer().serializeToString(svgDoc);
                        const modifiedImageUri = `data:image/svg+xml;base64,${btoa(serializedSvg)}`;
                        root?.style.setProperty('--banner-image-url', `url(${modifiedImageUri})`);
                    })
                    .catch(error => {
                        console.error('Error fetching SVG data:', error);
                    });
            } else {
                root?.style.setProperty('--banner-image-url', `url('')`);
            }
        }, () => [this.bannerState.banner, this.themeState.theme?.theme_color_ids]);

        this.is_subAction = this.props.action.context.is_subAction || false;
        onMounted(async () => {
            this.state.globalFilters = await this.orm.searchRead('dashboard.global.filter', [
                ['dashboard_config_id', '=', this.id]
            ])
            if (!this.sortedItems.length && !this.is_subAction) {
                this.state.showInfo = true;
            }
            if (this.container.el) {

                const resolveWidth = () => {
                    const els = [this.container.el, this.graph.el, this.dashboard.el];
                    for (const el of els) {
                        const w = el?.clientWidth || el?.offsetWidth;
                        if (w) return w;
                    }
                    // Last resort: viewport minus the app sidebar (~250px).
                    return Math.max(window.innerWidth - 250, 320);
                };
                const setGridVars = (w) => {
                    const col = Math.round(w / 12);
                    this.container.el.style.setProperty('--cy-grid-col-px', `${col}px`);
                    this.container.el.style.setProperty('--cy-grid-row-px', `${col}px`);

                    if (this.state.width !== col) this.state.width = col;
                };

                setGridVars(resolveWidth());
                const updateGridVars = () => {
                    if (!this.container.el) return;
                    setGridVars(resolveWidth());
                    if (!this.state.gridReady) {
                        clearTimeout(this._gridReadyTimer);
                        this._gridReadyTimer = setTimeout(() => {
                            if (status(this) === 'destroyed') return;
                            setGridVars(resolveWidth());
                            this.state.gridReady = true;
                            // Hold the overlay (gridRevealed) until the charts have
                            // actually finished painting — see _armReveal/_tryReveal.
                            this._armReveal();
                        }, 100);
                    }
                };
                updateGridVars();
                this._containerResizeObs = new ResizeObserver(updateGridVars);
                this._containerResizeObs.observe(this.container.el);
                this._gridReadyFallback = setTimeout(() => {
                    if (status(this) !== 'destroyed' && !this.state.gridReady) {
                        setGridVars(resolveWidth());
                        this.state.gridReady = true;
                        this._armReveal();
                    }
                }, 2000);
                this._gridSettleTimer = setTimeout(() => {
                    if (status(this) !== 'destroyed') setGridVars(resolveWidth());
                }, 450);
            }
        })
        onWillUnmount(() => {
            if (this._containerResizeObs) {
                this._containerResizeObs.disconnect();
            }
            clearTimeout(this._gridReadyTimer);
            clearTimeout(this._gridReadyFallback);
            clearTimeout(this._gridSettleTimer);
            clearTimeout(this._chartSettleTimer);
            clearTimeout(this._revealCapTimer);
        })
        // A KPI finishing its fetch decrements kpiPending (mixin). Re-evaluate the
        // reveal so the overlay can lift once the last KPI/chart is done.
        useBus(this.env.bus, 'KPI_LOADED', () => this._tryReveal())
        onWillStart(async () => {
            this.state.sources = await this.orm.searchRead('dashboard.config', [])
        })
        this.positions = {
            x: 0,
            y: 0,
            w: 0,
            h: 0,
            ft: true,
            maxH: [],
            maxHVal: { 0: [0] },
            colFill: new Array(12).fill(0),
            cache: {}
        }
        this.firstLine = true
        useEffect(() => {
            this.dashboard.el.style.backgroundColor = this.themeState.theme.background
        }, () => [this.themeState.theme])

        // Auto-refresh heartbeat every 2 minutes
        useEffect(() => {
            const interval = setInterval(() => {
                if (status(this) !== "destroyed") {
                    this.env.bus.trigger("REFRESH_GRAPH", { type: "refresh_graph" });
                }
            }, 120000);
            return () => clearInterval(interval);
        }, () => []);

        useEffect(() => {
            if (!this.container.el) return;
            if (!this.state.gridRevealed || this.state.kpiPending > 0) return;
            const cards = this.container.el.querySelectorAll('.chart-container-absolute');
            if (!cards.length) return;
            let maxBottom = 0;
            cards.forEach(card => {
                maxBottom = Math.max(maxBottom, card.offsetTop + card.offsetHeight);
            });
            this.container.el.style.minHeight = `${maxBottom + 16}px`;
        });
    }

    closeFilterSidebar() {
        this.state.optionClass = 'collapse-filter'
        this.state.options = []
        this.state.currentItem = false
    }

    get opacityClass() {
        return this.state.showInfo ? "opacity-d" : "opacity-u";
    }

    /**
     * Inline style for the grid container. The --cy-grid-*-px vars MUST live in this
     * binding (not only via setProperty): t-att-style rewrites the element's whole
     * style attribute on every re-render, which would wipe any vars set imperatively
     * and drop every card to the 60px fallback (the congested layout). state.width
     * holds the resolved column px (see setGridVars / resizeContainer).
     */
    get cardContainerStyle() {
        const w = this.state.width || 60;
        const vars = `--cy-grid-col-px:${w}px;--cy-grid-row-px:${w}px;`;
        const loading = !this.state.gridRevealed || this.state.kpiPending > 0;
        return loading
            ? `position:relative;min-height:calc(100dvh - 120px);${vars}`
            : `position:relative;${vars}`;
    }

    resizeContainer(width) {
        if (!this.container.el) return;
        const w = this.container.el.clientWidth || this.container.el.offsetWidth || width;
        if (!w) return;
        const col = Math.round(w / 12);
        this.state.width = col;
        this.container.el.style.setProperty('--cy-grid-col-px', `${col}px`);
        this.container.el.style.setProperty('--cy-grid-row-px', `${col}px`);
    }

    getDate(key) {
        return this.timFrameState[`date_${key}`]
    }

    setCustomDate(id, value) {
        const date = moment(value).format(this.dateFormats.actual)
        var id_o = id === "date_0" ? "date_1" : "date_0"
        if ((id == "date_0" && date > this.timFrameState[id_o]) || (id == "date_1" && date < this.timFrameState[id_o])) {
            this.notification.add(_t("The start date cannot be greater than the end date"), {
                type: "warning",
            });
            return;
        }
        this.timFrameState[id] = date
        var key = id === "date_0" ? "start-date" : "end-date"
        this.filters[key] = date
    }

    get timFrameDisplayName() {
        for (const [key, value] of Object.entries(this.TimeFrame)) {
            if (value === this.timFrameState.selected) return key
        }
    }

    get filterDateLabel() {
        const d0 = this.filterData?.date_0;
        const d1 = this.filterData?.date_1;
        if (!d0 || !d1) return 'Filters';
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const fmt = (s) => {
            const [y, m, d] = s.split('/');
            return `${d} ${months[+m - 1]} ${y.slice(2)}`;
        };
        return `${fmt(d0)} - ${fmt(d1)}`;
    }

    timeFrameChange(ev) {
        var value = ev.target.value
        this.timFrameState.selected = value
        if (value !== "custom") {
            var flag = !['quarter_l', 'month_l', 'year_l'].includes(value)
            value = value.split("_")[0]
            this.dateOrder(flag, value)
        }
    }

    sourceDashboard(dashboard) {
        this.actionService.doAction({
            target: "current",
            tag: "cy_analytic_dashboard",
            type: "ir.actions.client",
            context: {
                rec_id: dashboard.id
            }
        })
    }

    /**
     * Fetch data for the dashboard.
     */
    fetchData() {
    }

    /**
     * Explain the dashboard with AI.
     * @returns {Promise} - A promise for performing the action.
     */
    explainWithAI(options) {
        this.dialogService.add(ExplainAIModal, {
            options,
            theme: this.themeState.theme,
            currentTheme: this.themeState.currentTheme,
            isDarkMode: this.state.darkMode
        })
    }

    computeStyle(item) {
        const unit = this.state.width
        const toggleClass = 'chart-container-absolute'
        const sheetPosition = item.dashboard_sheet_option_ids
        let graph_height, graph_width, x, y
        const { height, width } = this.getChartSizes(item.type)
        if (item.id in this.positions.cache) {
            ({
                graph_height,
                graph_width,
                x,
                y
            } = this.positions.cache[item.id])
        } else {
            if (sheetPosition?.length) {
                ({
                    graph_height,
                    graph_width,
                    x,
                    y
                } = sheetPosition[0].attributes)
                // Enforce per-type minimums immediately so stale 1×1 DB values
                // don't corrupt the layout accumulator or the cache.
                if (item.type === 'kpi') {
                    const _minH = item.kpi_target ? 2 : 1;
                    graph_width = Math.max(graph_width || 3, 3);
                    graph_height = Math.max(graph_height || _minH, _minH);
                } else {
                    graph_width = Math.max(graph_width || 3, 3);
                    graph_height = Math.max(graph_height || 3, 3);
                }
                if (this.positions.w && !x) {
                    this.positions.w = 0
                }
            } else {
                graph_height = height
                graph_width = width
                if (item.type === 'kpi') {
                    const _kpiMinH = item.kpi_target ? 2 : 1
                    graph_width = Math.max(graph_width, 3)
                    graph_height = Math.max(graph_height, _kpiMinH)
                }
                x = this.positions.w + graph_width > 12 ? 0 : this.positions.w
                if (this.positions.w && !x) {
                    this.positions.w = 0
                    const newY = this.positions.maxHVal[this.positions.y]
                    y = Math.max(...newY) + this.positions.y
                } else {
                    y = this.positions.y
    const bottomOf = ([key, items]) =>
        items.map(item => item + parseInt(key, 10));
    const rows = Object.entries(this.positions.maxHVal);
    // Whether to drop to a new row is decided by the *other*
    // rows: a tile in this one is what we would sit beside, and
    // counting it here would push every tile onto a row of its
    // own and undo the packing entirely.
    const others = rows
        .filter(([key]) => parseInt(key, 10) !== y)
        .flatMap(bottomOf);
    if (others.some(value => value > y)) {
        // Where to drop to is a different question, and must
        // count every row including this one. Measuring only the
        // others put a new tile at the bottom of its neighbours
        // while the row it was leaving reached further down - so
        // a chart added to a dashboard whose last row is taller
        // than the rest lands on top of it. Which is the whole
        // bug: the trigger and the destination were reading two
        // different sets of tiles.
        y = Math.max(...rows.flatMap(bottomOf))
        x = 0
        this.positions.w = 0
    }
}
            }
            this.positions.x = x
            this.positions.y = y
            this.positions.w += graph_width
            this.positions.h = graph_height
            if (this.positions.maxHVal[y]) {
                this.positions.maxHVal[y].push(graph_height)
            } else this.positions.maxHVal[y] = [graph_height]
            if (!sheetPosition?.length && !(item.id in this.positions.cache)) {
                this.orm.call("dashboard.sheet", "set_sheet_position", [item.id, this.id], {
                    x,
                    y,
                    graph_width,
                    graph_height
                })
            }
        }

        const attributes = {
            graph_height,
            graph_width,
            x,
            y
        }
        if (item.type === 'kpi') {
            graph_width = Math.max(graph_width || 3, 3);
            const kpiMinH = item.kpi_target ? 2 : 1;
            graph_height = Math.max(graph_height || kpiMinH, kpiMinH);
        } else if (item.type !== 'table') {
            graph_width = Math.max(graph_width || 3, 3);
            graph_height = Math.max(graph_height || 3, 3);
        } else if (item.type === 'table') {
            graph_width = Math.max(graph_width || 3, 3);
            graph_height = Math.max(graph_height || 3, 3);
        }

        this.positions.cache[item.id] = attributes
        const GAP = 4;
        let style;
        style = {
            height: `calc(${graph_height} * var(--cy-grid-row-px, 60px) - ${GAP * 2}px);`,
            width: `calc(${graph_width} * var(--cy-grid-col-px, 60px) - ${GAP * 2}px);`,
            top: `calc(${y} * var(--cy-grid-row-px, 60px) + ${GAP}px);`,
            left: `calc(${x} * var(--cy-grid-col-px, 60px) + ${GAP}px);`,
        }
        this.refreshObject.currentLen++
        return {
            style,
            toggleClass,
            attributes
        }
    }

    /**
     * Edit the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    onEdit() {
        if (this.state.showInfo) return;
        return this.actionService.doAction({
            target: "current",
            tag: "edit_dashboard",
            type: "ir.actions.client",
            context: {
                rec_id: this.id
            }
        })
    }

    getRecordModel(item, kpi = false) {
        if (kpi?.model) {
            return kpi.model;
        }
        const tables = item?.table_ids || [];
        const primaryTable = tables.find((table) => !table.linked && table.model) || tables.find((table) => table.model);
        return primaryTable?.model || false;
    }

    openRecord(kpi, item) {
        const resModel = this.getRecordModel(item, kpi);
        if (!resModel) {
            return;
        }
        var {
            filter_ids,
            sheet_filter_ids
        } = item
        const tables = item.table_ids || [];
        const tableJoinMap = {};
        tables.forEach(t => tableJoinMap[t.name] = t);

        const buildRelationPath = (tableName) => {
            const table = tableJoinMap[tableName];
            if (!table || !table.linked) return "";
            const match = table.join.match(/ON\s+[\w_]+\.id\s*=\s*([\w_]+)\.([\w_]+)/i);
            if (match) {
                const parentTable = match[1];
                const fieldName = match[2];
                const parentPath = buildRelationPath(parentTable);
                return parentPath ? `${parentPath}.${fieldName}` : fieldName;
            }
            return "";
        };

        const primaryTable = tables.find(t => !t.linked) || tables[0];
        const primaryTableName = resModel.replace(/\./g, '_');

        var domain = [];
        // 1. Implicit Relational Filters (INNER JOIN Simulation)
        const addedRelationalPaths = new Set();
        tables.forEach(table => {
            if (table.linked) {
                const path = buildRelationPath(table.name);
                if (path && !addedRelationalPaths.has(path)) {
                    domain.push([path, '!=', false]);
                    addedRelationalPaths.add(path);
                }
            }
        });

        // 2. Global Filters (ANDed)
        for (const filter of sheet_filter_ids) {
            const code = filter.global_filter_id.code;
            const operator = filter.global_filter_id.operator;
            const val = this.filters[code];
            if (val !== undefined && val !== null && (Array.isArray(val) ? val.length : true)) {
                let field = filter.field;
                if (field.includes('.')) {
                    const [table, col] = field.split('.');
                    if (table === primaryTableName || tableJoinMap[table]) {
                        const path = buildRelationPath(table);
                        field = path ? `${path}.${col}` : col;
                    } else {
                        field = col; // Fallback
                    }
                }
                domain.push([field, operator, val]);
            }
        }

        // 3. Item Filters (Internal ORs, External ANDs)
        filter_ids = filter_ids.filter(item => item.is_active);
        for (const { domain: filterD } of filter_ids) {
            const parts = filterD.split(" OR ");
            if (parts.length > 1) {
                for (let i = 0; i < parts.length - 1; i++) {
                    domain.push('|');
                }
            }
            for (const part of parts) {
                const match = part.match(/^(.*?)\s*(=|!=|>|<|>=|<=|IN|NOT\s+IN)\s*(.*)$/i);
                if (match) {
                    let lhs = match[1].trim();
                    if (lhs.includes('.')) {
                        const [table, col] = lhs.split('.');
                        if (table === primaryTableName || tableJoinMap[table]) {
                            const path = buildRelationPath(table);
                            lhs = path ? `${path}.${col}` : col;
                        } else {
                            lhs = col; // Fallback
                        }
                    }
                    const opr = match[2].trim().toLowerCase();
                    let rhs = match[3].trim();
                    if (rhs.startsWith("'") && rhs.endsWith("'")) {
                        rhs = rhs.slice(1, -1);
                    }
                    if (rhs.includes('(') && rhs.includes(')')) {
                        rhs = rhs.replace(/\(/g, '[').replace(/\)/g, ']');
                        try {
                            rhs = JSON.parse(rhs.replace(/'/g, '"'));
                        } catch (e) {
                            try {
                                rhs = eval(rhs);
                            } catch (e2) { }
                        }
                    }
                    domain.push([lhs, opr, rhs]);
                }
            }
        }

        // 4. MAX Aggregation Support
        const chartItem = this.ChartData.data.find(d => d.id === item.id);
        const maxMeasure = (item.axis_ids || []).find(a => a.type === 'measure' && a.aggregate_func === 'MAX');
        const dimension = (item.axis_ids || []).find(a => a.type === 'dimension');

        if (maxMeasure && dimension && chartItem && chartItem.data && chartItem.data.length) {
            const getOdooField = (colPath) => {
                if (colPath.includes('.')) {
                    const [table, col] = colPath.split('.');
                    if (table === primaryTableName || tableJoinMap[table]) {
                        const path = buildRelationPath(table);
                        return path ? `${path}.${col}` : col;
                    }
                    return col;
                }
                return colPath;
            }

            const dimField = getOdooField(dimension.column);
            const msrField = getOdooField(maxMeasure.column);
            const maxDomain = [];

            // Add OR prefixes
            if (chartItem.data.length > 1) {
                for (let i = 0; i < chartItem.data.length - 1; i++) {
                    maxDomain.push('|');
                }
            }

            chartItem.data.forEach(row => {
                const dimVal = row[dimension.alias];
                const msrVal = row[maxMeasure.alias];
                if (dimVal !== undefined && dimVal !== null) {
                    maxDomain.push('&', [dimField, '=', dimVal], [msrField, '=', msrVal]);
                } else {
                    maxDomain.push('&', [dimField, '=', false], [msrField, '=', msrVal]);
                }
            });

            if (maxDomain.length) {
                domain.push(...maxDomain);
            }
        }
        return this.actionService.doAction({
            name: _t("My Dashboard"),
            type: 'ir.actions.act_window',
            res_model: resModel,
            view_mode: 'tree,form,calendar',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain,
            target: 'current',
        });
    }

    hideDropdown() {
        var sheet_conf = this.graph.el.querySelector('.stack-item').querySelectorAll('.dropdown')
        for (const elem of sheet_conf) {
            if (!elem.style.display) {
                elem.style.display = 'none';
            } else {
                elem.style.display = 'block';
            }
        }
    }

    async exportPDF(type) {
        this.state.isPrinting = true;

        // Force-render all charts that haven't scrolled into view yet,
        // then wait for every chart's ECharts 'finished' event before capturing.
        const chartReadyPromises = [];
        const onChartReady = (ev) => chartReadyPromises.push(ev.detail.ready);
        this.env.bus.addEventListener('CHART_PRINT_READY', onChartReady);
        this.env.bus.trigger('FORCE_RENDER_ALL_CHARTS');
        this.env.bus.removeEventListener('CHART_PRINT_READY', onChartReady);
        await Promise.all(chartReadyPromises);

        const cutoffImage = (image, rowsToCut, pageHeight) => {
            var imagePieces = [];
            var widthOfOnePiece = image.width;
            var heightOfOnePiece = pageHeight || image.height / rowsToCut;
            for (var x = 0; x < 1; ++x) {
                for (var y = 0; y < rowsToCut; ++y) {
                    var canvas = document.createElement('canvas');
                    canvas.width = widthOfOnePiece;
                    canvas.height = heightOfOnePiece;
                    var context = canvas.getContext('2d');
                    context.drawImage(
                        image,
                        x * widthOfOnePiece,
                        y * heightOfOnePiece,
                        widthOfOnePiece,
                        heightOfOnePiece,
                        0,
                        0,
                        canvas.width,
                        canvas.height
                    );
                    imagePieces.push(canvas.toDataURL('image/png'));
                }
            }

            return imagePieces;
        };
        var element = this.graph.el.querySelector('.stack-item');
        element.querySelectorAll('.chart-container-absolute').forEach((item) => {
            item.classList.add('print-card')
        })
        this.hideDropdown();
        let pdf = new jsPDF(type, 'mm', 'a4');
        html2canvas(element, {
            scale: 1.2,
            allowTaint: true,
            useCORS: true,
            logging: false,
            scrollY: -window.scrollY, // Capture the entire scrollable area
            windowHeight: element.scrollHeight + 1000,
            ignoreElements: (node) => node.classList.contains('ai-btn-class')
        }).then((canvas) => {
            let imgData = canvas.toDataURL('image/png');
            let pageWidth = pdf.internal.pageSize.getWidth();
            let pageHeight = pdf.internal.pageSize.getHeight();
            let imageWidth = pageWidth - 25;
            let imageHeight = (imageWidth / canvas.width) * canvas.height;
            let offsetX = 12;
            let offsetY = 15;
            var pdfPages = Math.ceil(imageHeight / pageHeight);
            var value = 2850
            if (type === 'l') {
                imageWidth = pageWidth - 100
                offsetX = 50;
                pdfPages = Math.ceil(imageHeight / 250);
                value = 2000
            }
            const canvasData = cutoffImage(canvas, pdfPages, value)
            for (let i = 0; i < pdfPages; i++) {
                const pieceOffsetY = i * pageHeight;
                var pieceHeight = 250;
                const pieceImgData = canvasData[i];
                if (i === 0) {
                    pdf.setFont("helvetica");
                    pdf.setFontType("bold");
                    pdf.setFontSize(9);
                    pdf.text(`${this.name} - This Dashboard Shows Information From ${this.filterData.date_0} To ${this.filterData.date_1}.`, offsetX, 10);
                }
                if (i > 0) {
                    offsetY = 2;
                    pdf.addPage();
                }
                pdf.addImage(pieceImgData, 'PNG', offsetX, offsetY, imageWidth, -pieceHeight);
            }
            this.hideDropdown();
            pdf.save(this.name);
            element.querySelectorAll('.chart-container-absolute').forEach((item) => {
                item.classList.remove('print-card')
            })
            this.state.isPrinting = false;
        });
    }

    /**
     * Export the dashboard data to JSON.
     */
    async onJsonExport() {
        try {
            const data = await this.orm.call("dashboard.config", "get_dashboard_data", [this.id]);
            const json = JSON.stringify(data);
            const blob = new Blob([json], {
                type: "application/json"
            });
            const url = URL.createObjectURL(blob);
            const file = document.createElement("a"); // Correct the element type to "a"
            file.download = this.name + " dashboard.json";
            file.href = url;
            file.click();
        } catch (error) {
            console.error("An error occurred:", error);
        }
    }

    /**
     * Add the dashboard to the menu. */
    onAddToMenu() {
        this.dialogService.add(MenuDialog, {
            rec_id: this.id,
            name: this.name
        })
    }

    /**
     * Delete the dashboard.
     */
    onDelete() {
        this.dialogService.add(DeleteDialog, {
            body: `Are You Sure you Want To Delete, ${this.state.name} Dashboard?`,
            id: this.id,
            removeManually: this.removeManually.bind(),
            model: 'dashboard.config'
        })
    }

    /**
     * Configure the dashboard.
     */
    onConfig() {
        this.dialogService.add(ConfigurationDialog, {
            id: this.id,
            name: this.props.name,
            applyTheme: this.switchTheme.bind(this),
            onClickSave: this.onConfigSave.bind(this),
        })
    }

    /**
     * Share the dashboard.
     */
    onShareDashboard() {
        if (this.state.showInfo) return;
        const sheetQueries = {};
        if (this.state.sortedItems) {
            this.state.sortedItems.forEach(item => {
                sheetQueries[item.id] = item.query;
            });
        }
        return this.actionService.doAction({
            name: "Share Dashboard",
            type: "ir.actions.act_window",
            res_model: "dashboard.config",
            res_id: this.id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                hide_access_rights: true,
                default_sheet_queries: JSON.stringify(sheetQueries),
                default_date_from: this.filterData?.date_0 || false,
                default_date_to: this.filterData?.date_1 || false,
            },
        });
    }

    /**
     * Present the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    onPresent() {
        if (this.state.showInfo) return;
        return this.actionService.doAction({
            target: "current",
            tag: "present_selection",
            type: "ir.actions.client",
            context: {
                rec_id: this.id
            }
        })
    }

    /**
     * Select a theme.
     * @param {number} themeId - The ID of the selected theme.
     */
    async OnSelectTheme(themeId) {
        this.themeState.theme_id = themeId
        if (this.id) {
            await this.orm.write("dashboard.config", [this.id], {
                theme_id: themeId
            })
        }
        this.applyTheme()
    }

    /**
     * Apply the selected theme.
     */
    async applyTheme() {
        this.themeState.theme = await this.orm.call("dashboard.theme", "read_theme",
            [this.themeState.theme_id]
        )
        var theme_maker = new ThemeMaker(this.themeState.theme)
        this.themeState.currentTheme = theme_maker.getTheme()
    }

    /**
     * Switch the theme.
     * @param {number} themeId - The ID of the theme to switch to.
     */
    switchTheme(themeId) {
        this.themeState.theme_id = themeId
        this.applyTheme()
    }

    /**
     * Add a graph to the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    addGraph() {
        return this.actionService.doAction("cyllo_analytics.cyllo_dashboard_sheet", {
            target: "fullscreen",
            additionalContext: {
                dashboard_id: this.id,
                display_name: this.name,
                is_new_sheet: true
            }
        })
    }

    onEditSheet(sheet) {
        return this.actionService.doAction("cyllo_analytics.cyllo_dashboard_sheet", {
            target: "fullscreen",
            additionalContext: {
                rec_id: sheet.id,
                dashboard_id: this.id,
                display_name: this.name
            }
        })
    }

    onDeleteSheet(sheet) {
        this.dialogService.add(SheetDeleteDialog, {
            id: sheet.id,
            model: "dashboard.sheet",
            body: `Are You Sure you Want To Delete ${sheet.name} ?`,
            removeManually: () => {
                var index = this.state.sortedItems.indexOf(sheet)
                this.state.sortedItems.splice(index, 1)
                if (!this.state.sortedItems.length) {
                    this.state.showInfo = true;
                }
            }
        })
    }

    async onSetAlert(item) {
        // Use string comparison for IDs to be safe against type mismatches
        const allData = this.ChartData.data || [];
        let chartData = [...allData].reverse().find(d => String(d.id) === String(item.id));

        // If data is missing from the store, fetch it manually (GraphTile handles its own fetching)
        if (!chartData && item.query) {
            try {
                const sql = item.query.replace(/\n/g, ' ');
                const res = await this.orm.call("dashboard.config", "sql_execute", [sql]);
                if (res && Array.isArray(res)) {
                    let measuresList = item.measure || '[]';
                    if (typeof measuresList === 'string') {
                        try {
                            measuresList = JSON.parse(measuresList.replaceAll("'", '"'));
                        } catch (e) {
                            measuresList = [];
                        }
                    }
                    const measureAliases = Array.isArray(measuresList) ? measuresList.map(m => typeof m === 'object' ? m.alias : m) : [];

                    chartData = {
                        data: res,
                        id: item.id,
                        name: item.name,
                        dimension: item.dimension,
                        measures: measureAliases,
                    };
                    // Sync back to store for future use
                    this.ChartData.data.push(chartData);
                }
            } catch (err) {
                console.error("Failed to fetch alert data:", err);
            }
        }

        const dimensionAxis = (item.axis_ids || []).find(a => a.type === 'dimension');
        let dimKey = dimensionAxis ? (dimensionAxis.alias || dimensionAxis.name) : (chartData ? chartData.dimension : null);
        let dimensionValues = [];

        if (chartData && chartData.data && Array.isArray(chartData.data) && chartData.data.length > 0) {
            const firstRow = chartData.data[0];
            const dataKeys = Object.keys(firstRow);

            // Resilient dimKey detection
            if (!dimKey || !dataKeys.includes(dimKey)) {
                const ciKey = dimKey ? dataKeys.find(k => k.toLowerCase() === dimKey.toLowerCase()) : null;
                if (ciKey) {
                    dimKey = ciKey;
                } else {
                    // Try to find a key that is likely the dimension (string-like, not a measure)
                    const measureKeys = (chartData.measures || []).concat(['__count']);
                    dimKey = dataKeys.find(k => !measureKeys.includes(k) && typeof firstRow[k] === 'string')
                        || dataKeys.find(k => !measureKeys.includes(k))
                        || dataKeys[0];
                }
            }

            if (dimKey && dataKeys.includes(dimKey)) {
                dimensionValues = [...new Set(chartData.data.map(row => row[dimKey]))]
                    .filter(v => v !== undefined && v !== null && v !== "")
                    .map(v => String(v));
            }
        }

        this.dialogService.add(AlertConfigurationDialog, {
            item,
            dimensionValues
        })
    }

    onHideSheet(sheet) {
        this.dialogService.add(SheetDeleteDialog, {
            title: 'Hide',
            body: `Are You Sure you Want To Hide ${sheet.name} From Dashboard ${this.name} ?`,
            callBackAction: () => {
                var index = this.state.sortedItems.indexOf(sheet)
                this.state.sortedItems.splice(index, 1)
                if (!this.state.sortedItems.length) {
                    this.state.showInfo = true;
                }
                this.orm.call("dashboard.config", "remove_sheet", [this.id, sheet.id])
            }
        })

    }

    async onConfigSave(changes) {
        if (changes.name) {
            this.state.name = changes.name
        }
        if (Object.keys(changes).includes("banner_id")) {
            if (changes.banner_id) {
                this.bannerState.banner = await this.orm.read('dashboard.banner', [changes.banner_id])
            } else this.bannerState.banner = [];
        }

    }

    exportAsPNG(sheet) {
        const imgSrc = this.chartImages[sheet.id]
        const downloadLink = document.createElement('a');
        downloadLink.href = imgSrc;
        downloadLink.download = sheet.name;
        downloadLink.click();
    }

    filterClose() {
        this.filter_dropdown.el.classList.remove('show');
    }

    setImage(img, name, id) {
        this.chartImages[id] = img;
        // Each call means a chart (GraphTile) just finished an ECharts render pass.
        // Debounce: once charts stop painting for 150ms they're considered settled,
        // then try to lift the loading overlay. Keeps the overlay up through the
        // chart's deferred ~500ms init + 'finished' event so no half-drawn/empty
        // chart frame is ever shown (the "flash").
        if (!this.state.gridRevealed) {
            clearTimeout(this._chartSettleTimer);
            this._chartSettleTimer = setTimeout(() => {
                if (status(this) === 'destroyed') return;
                this._chartsSettled = true;
                this._tryReveal();
            }, 150);
        }
    }

    /**
     * Arm the overlay-reveal gating once the grid is ready (vars set, cards mounted).
     * The overlay stays visible until charts have actually painted; see _tryReveal.
     */
    _armReveal() {
        if (this._revealArmed) return;
        this._revealArmed = true;
        // Only echart tiles (GraphTile) have the deferred init + async 'finished'
        // paint. KPIs and tables paint synchronously, so a dashboard without charts
        // needs no chart-settle wait.
        this._hasCharts = (this.state.sortedItems || []).some(
            i => i.type !== 'kpi' && i.type !== 'table'
        );
        this._chartsSettled = !this._hasCharts;
        // Hard cap: never let the overlay hang. Off-screen-only charts (lazy-rendered
        // on scroll), a chart error, or a missing 'finished' event would otherwise
        // block reveal forever. Force it after 4s.
        clearTimeout(this._revealCapTimer);
        this._revealCapTimer = setTimeout(() => {
            if (status(this) === 'destroyed') return;
            this._chartsSettled = true;
            this.state.gridRevealed = true;
        }, 4000);
        // Let the freshly-mounted cards lay out for a couple of frames, then attempt
        // the first reveal (handles the no-charts / no-KPI case immediately).
        requestAnimationFrame(() => requestAnimationFrame(() => this._tryReveal()));
    }

    /**
     * Lift the loading overlay only when everything is genuinely painted:
     * grid ready, all KPIs loaded, and all (visible) charts finished rendering.
     */
    _tryReveal() {
        if (status(this) === 'destroyed') return;
        if (this.state.gridRevealed) return;
        if (!this.state.gridReady) return;
        if (this.state.kpiPending > 0) return;
        if (this._hasCharts && !this._chartsSettled) return;
        this.state.gridRevealed = true;
        clearTimeout(this._revealCapTimer);
    }

    getDomain(filter) {
        let ids = this.filters[filter.code] || []
        return [
            ['id', 'not in', ids]
        ]
    }

    onRemoveFilter(rec, filter) {
        let indexTimFrameState = this.timFrameState[filter.code].indexOf(rec)
        let indexFilters = this.filters[filter.code].indexOf(rec)
        this.timFrameState[filter.code].splice(indexTimFrameState, 1)
        this.filters[filter.code].splice(indexFilters, 1)
    }

    async onSelect(ev, filter) {
        if (filter.type == 'datetime') {
            this.timFrameState.selected = 'custom'
            var {
                value
            } = ev.target
            var id = ev.target.getAttribute('id')
            this.setCustomDate(id, value)
        }
        if (filter.type == 'many2one') {
            if (!this.timFrameState[filter.code]) {
                this.timFrameState[filter.code] = [];
            }
            var res = await this.orm.read(filter.relation, [ev[0].id], ["display_name"]);
            if (!this.timFrameState[filter.code].includes(res[0])) {
                this.timFrameState[filter.code].push(res[0]);
            }
            if (!this.filters[filter.code]) {
                this.filters[filter.code] = [];
            }
            if (!this.filters[filter.code].includes(ev[0].id)) {
                this.filters[filter.code].push(ev[0].id);
            }
        }
    }

    closeFilter() {
        this.filter_dropdown.el.classList.add("cy_filter_toggler")
        this.dashboard.el.querySelector(".cy-churn-filter-btn").classList.remove("show")
    }

    onClickFilter() {
        this.filter_dropdown.el.classList.toggle("cy_filter_toggler")
        this.dashboard.el.querySelector(".cy-churn-filter-btn").classList.toggle("show")
    }

    applyFilter() {
        Object.assign(this.filterData, {
            ...JSON.parse(JSON.stringify(this.timFrameState)),
            date_0: this.timFrameState.date_0.replace(/-/g, '/'),
            date_1: this.timFrameState.date_1.replace(/-/g, '/'),
        });
        this.storeDefaultFilter();
        this.applyAllFilters();
        this.closeFilter()
    }

    onClickChart(item, index) {
        if (index === this.state.currentItem) {
            this.state.optionClass = 'collapse-filter'
            this.state.options = []
            this.state.currentItem = false
        } else {
            this.state.options = item.filter_ids
            this.state.currentItem = index
            this.state.optionClass = ''
        }
    }

    filterChange(option, index) {
        option.is_active = !option.is_active
        this.applyItemFilter(this.state.sortedItems[index])
        this.env.bus.trigger("REFRESH_GRAPH", { type: "refresh_graph" });
    }

    get filterInfo() {
        return owl.markup(
            "The Global Filter applies based on the fields defined in the sheet editor's global filter section." +
            `To change default filter fields, Click "Edit" in dropdown menu of the charts, then go to Global Filter and modify the corresponding fields.`
        );
    }
}

// Define the components used in the CylloDashboard
CylloDashboard.components = {
    Dropdown,
    DropdownItem,
    GraphTile,
    ControlPanel,
    Many2XAutocomplete,
    KpiSheet,
    KpiSheetChart,
    Table
}
// Define the template for the CylloDashboard
CylloDashboard.template = "cyllo_analytics.CylloDashboard";
// Register the cyllo_analytics component in the actions category
registry.category("actions").add("cy_analytic_dashboard", CylloDashboard);
