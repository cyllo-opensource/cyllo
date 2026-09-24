/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useState, useEffect, Component, useRef, onWillStart, onMounted, onWillUpdateProps, status, onWillDestroy} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {ChartMaker} from "../../chart_maker"
import { useService, useBus } from "@web/core/utils/hooks";

export const RE_RENDER_GRAPHS = ['map', 'heatmap', 'pictorialBar']
export const NO_ZOOM_CHARTS = ["map", "gauge", "doughnut", "radar", "pie", "funnel"]

/**
 * GraphTile class for displaying a graph in a dashboard view.
 * @class
 */
export class GraphTile extends Component {
    /**
     * Initializes the GraphTile class.
     * @function
     */
    setup() {
        const {
            theme,
        } = this.props
        this.state = useState({
            style: "",
            cardStyle: "",
            theme,
            rec_id: false,
            hasData: true,
            zoom: 0,
            showZoom: false,
            showColorGuide: false,
            // Annotation inline overlay
            showAnnotation: false,
            annotationX: 0,
            annotationY: 0,
            annotationNote: '',
            annotationLabel: '',
            annotationSeries: '',
            annotationSeriesIndex: 0,
            annotationDataIndex: 0,
            annotationValue: null,
        })
        this.orm = useService('orm')
        this.action = useService('action')
        this.is_init = true
        this.rootRef = useRef('root')
        this._clickTimer = null
        this._isVisible = false
        this._pendingRender = false
        this._hasRenderedOnce = false
        this._resolveReady = null
        this.ready = Promise.resolve()

        useBus(this.env.bus, "REFRESH_GRAPH", async (ev) => {
            if (ev && ev.detail && ev.detail.type === "refresh_graph") {
                await this.setupGraphData()
            } else {
                // CSS vars drive sizing — just fit canvas to new container size
                if (this.eChart && !this._animating) {
                    this.eChart.resize();
                }
            }
        })

        useBus(this.env.bus, "FORCE_RENDER_ALL_CHARTS", () => {
            if (!this._hasRenderedOnce) {
                this._isVisible = true;
                this._pendingRender = false;
                this.addElement();
            }
            this.env.bus.trigger('CHART_PRINT_READY', { ready: this.ready });
        })

        useBus(this.env.bus, "RERENDER_ALL_GRAPHS", async () => {
            const item = this.props.value || this.props.item
            if (item) {
                this.setOptions(item)
                this.options = await this.maker.makeGraphOptions()
                this.addElement()
            }
        })

        useBus(this.env.bus, "CHART_SHOW_ANNOTATION", (ev) => {
            const d = ev.detail;
            if (d.itemId !== this.props.itemId) return;
            this.state.showAnnotation = true;
            this.state.annotationNote = d.existingNote || '';
            this.state.annotationLabel = `${d.measureName} — ${d.dimensionName} : ${d.numericValue}`;
            this.state.annotationSeries = d.alias;
            this.state.annotationValue = d.numericValue;
            this._annotationSaveCallback = d.onSave;
        })
        let reRender = true
        useEffect(() => {
            if (reRender) {
                this.setupGraphData()
            }
            reRender = this.props.reRender
        }, () => [this.props.item?.query, this.props.value])
        
        useEffect(() => {
            this.setStyle()
        }, () => [this.props.style])
        
        useEffect(() => {
            if (this.props.theme != this.state.theme) {
                this.state.theme = this.props.theme
                this.reRender()
            }
        }, () => [this.props.theme])


        // NOTE: No useEffect on this.options — every setter calls addElement() directly.
        // A useEffect here causes a second addElement() call (via OWL re-render triggered
        // by state.hasData change in fetchData), which runs setOption mid-legend-click
        // animation and makes ZRender restart hit-area calculation → legend clicks lost.

        onMounted(() => {
            // Sync initial visibility before any addElement() call
            if (this.rootRef.el) {
                const rect = this.rootRef.el.getBoundingClientRect();
                this._isVisible = (
                    rect.bottom > 0 && rect.top < window.innerHeight &&
                    rect.right > 0 && rect.left < window.innerWidth
                );
            }

            if (this.options) {
                this.addElement()
            }

            this.resizeObserver = new ResizeObserver(() => {
                if (this.eChart && !this._animating) {
                    this.eChart.resize();
                }
            });
            if (this.rootRef.el) {
                this.resizeObserver.observe(this.rootRef.el);
            }

            this._intersectionObserver = new IntersectionObserver((entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting && !this._isVisible) {
                        this._isVisible = true;
                        if (this._pendingRender) {
                            this.addElement();
                        }
                    } else if (!entry.isIntersecting) {
                        this._isVisible = false;
                    }
                }
            }, { threshold: 0.1 });
            if (this.rootRef.el) {
                this._intersectionObserver.observe(this.rootRef.el);
            }

            // ECharts calls preventDefault() on wheel events even when moveOnMouseWheel=false,
            // so the browser never scrolls the page. Capture the event first (capture:true)
            // and manually forward the delta to the nearest scrollable ancestor.
            if (this.rootRef.el) {
                this._wheelHandler = (ev) => {
                    let node = this.rootRef.el.parentElement;
                    while (node && node !== document.documentElement) {
                        const { overflowY } = window.getComputedStyle(node);
                        if (overflowY === 'auto' || overflowY === 'scroll') {
                            node.scrollTop += ev.deltaY;
                            return;
                        }
                        node = node.parentElement;
                    }
                    window.scrollBy(0, ev.deltaY);
                };
                this.rootRef.el.addEventListener('wheel', this._wheelHandler, { capture: true, passive: true });
            }
        })

        onWillDestroy(() => {
            if (this._radarZr) {
                this._radarZr.off('mousemove', this._radarMove);
                this._radarZr.off('mouseout', this._radarOut);
                this._radarZr = null;
            }
            if (this._radarTip) { this._radarTip.remove(); this._radarTip = null; }
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }
            if (this._intersectionObserver) {
                this._intersectionObserver.disconnect();
            }
            if (this._clickTimer) {
                clearTimeout(this._clickTimer);
            }
            if (this._wheelHandler && this.rootRef.el) {
                this.rootRef.el.removeEventListener('wheel', this._wheelHandler, { capture: true });
            }
        })
    }

    /**
     * Radar tooltip: show ONLY the hovered vertex (e.g. "Lounge Sofa\nSales Price: 350")
     * instead of ECharts' default which dumps the whole value array. ECharts gives the
     * tooltip no hovered-axis index for radar, so we find the nearest vertex ourselves
     * via radar.coordinateSystem.dataToPoint(value, i) and render a small custom tooltip.
     */
    _setupRadarTooltip() {
        if (!this.eChart) return;
        // Tear down any previous wiring (re-render / theme switch).
        if (this._radarZr) {
            this._radarZr.off('mousemove', this._radarMove);
            this._radarZr.off('mouseout', this._radarOut);
            this._radarZr = null;
        }
        if (this._radarTip) { this._radarTip.remove(); this._radarTip = null; }

        const isRadar = this.options?.series?.[0]?.type === 'radar';
        if (!isRadar) return;

        // Suppress the built-in (all-values) tooltip for this chart.
        this.eChart.setOption({ tooltip: { show: false } });

        const tip = document.createElement('div');
        tip.className = 'cy-radar-point-tip';
        tip.style.display = 'none';
        (this.rootRef.el || this.eChart.getDom()).appendChild(tip);

        this._radarMove = (e) => {
            const coordSys = this.eChart.getModel().getComponent('radar')?.coordinateSystem;
            const data = this.options?.series?.[0]?.data?.[0]?.value || [];
            const indicators = this.options?.radar?.indicator || [];
            if (!coordSys || !data.length) { tip.style.display = 'none'; return; }
            let best = -1, bestD = Infinity;
            for (let i = 0; i < data.length; i++) {
                const p = coordSys.dataToPoint(Number(data[i]) || 0, i);
                const d = (p[0] - e.offsetX) ** 2 + (p[1] - e.offsetY) ** 2;
                if (d < bestD) { bestD = d; best = i; }
            }
            // Only show when the cursor is actually near a vertex (~24px).
            if (best < 0 || bestD > 24 * 24) { tip.style.display = 'none'; return; }
            const axisName = indicators[best]?.name ?? '';
            const seriesName = this.options.series[0].name || '';
            tip.innerHTML =
                `<div class="cy-radar-point-tip__name">${axisName}</div>` +
                `<div>${seriesName} : <b>${data[best]}</b></div>`;
            tip.style.display = 'block';
            tip.style.left = (e.offsetX + 14) + 'px';
            tip.style.top = (e.offsetY + 14) + 'px';
        };
        this._radarOut = () => { tip.style.display = 'none'; };

        this._radarZr = this.eChart.getZr();
        this._radarZr.on('mousemove', this._radarMove);
        this._radarZr.on('mouseout', this._radarOut);
        this._radarTip = tip;
    }

    toggleColorGuide() {
        this.state.showColorGuide = !this.state.showColorGuide;
    }

    saveAnnotation() {
        if (this._annotationSaveCallback) {
            this._annotationSaveCallback(this.state.annotationNote);
        }
        this.state.showAnnotation = false;
        this.state.annotationNote = '';
        this._annotationSaveCallback = null;
    }

    closeAnnotation() {
        this.state.showAnnotation = false;
        this.state.annotationNote = '';
        this._annotationSaveCallback = null;
    }

    onDblClickChart(ev) {
        if (!this.eChart) return;
        const rect = this.rootRef.el.getBoundingClientRect();
        const mx = ev.clientX - rect.left;
        const my = ev.clientY - rect.top;
        const opt = this.eChart.getOption();
        if (!opt) return;
        const series = opt.series || [];
        const xAxisData = (opt.xAxis && opt.xAxis[0] && opt.xAxis[0].data) || [];

        for (let si = 0; si < series.length; si++) {
            const ser = series[si];
            const rawData = ser.data || [];
            if (xAxisData.length) {
                try {
                    const res = this.eChart.convertFromPixel({ seriesIndex: si }, [mx, my]);
                    const di = Array.isArray(res) ? Math.round(res[0]) : null;
                    if (di !== null && di >= 0 && di < xAxisData.length) {
                        const val = rawData[di];
                        this._fireAnnotation({
                            seriesIndex: si,
                            seriesName: ser.name,
                            dataIndex: di,
                            name: xAxisData[di],
                            value: typeof val === 'object' ? (val && val.value !== undefined ? val.value : val) : val
                        });
                        return;
                    }
                } catch(e) {}
            } else {
                try {
                    const res = this.eChart.convertFromPixel({ seriesIndex: si }, [mx, my]);
                    const di = Array.isArray(res) ? res[0] : (typeof res === 'number' ? res : null);
                    if (di !== null && di >= 0) {
                        const entry = rawData[di];
                        if (entry) {
                            this._fireAnnotation({
                                seriesIndex: si,
                                seriesName: ser.name,
                                dataIndex: di,
                                name: typeof entry === 'object' ? entry.name : String(entry),
                                value: typeof entry === 'object' ? (entry.value !== undefined ? entry.value : 0) : entry
                            });
                            return;
                        }
                    }
                } catch(e) {}
            }
        }
        // Fallback
        this._fireAnnotation({ seriesIndex: 0, seriesName: '', dataIndex: 0, name: '(chart)', value: '' });
    }

    _fireAnnotation(params) {
        if (this.props.onChartPointClick) {
            this.props.onChartPointClick(params, this.props.itemId);
        }
    }

    /**
     * Re-renders the graph when there are changes in the theme.
     * @function
     */
    async reRender() {
        if (this.props.item?.type && RE_RENDER_GRAPHS.includes(this.props.item?.type)) {
            var params = this.props.themeColor ? {themeColor: this.props.themeColor} : {};
            this.options = await this.maker.regenGraphOptions(params)
        } else {
            this.setOptions(this.props.value || this.props.item)
            this.options = await this.maker.makeGraphOptions()
        }
        this.addElement()
    }

    /**
     * Sets up the initial data for the graph.
     * @async
     * @function
     */
    async setupGraphData() {
        if (this.props.value) {
            this.state.rec_id = this.props.value.id
            if (this.is_init) {
                await this.setStyle()
                this.is_init = false
            }
            this.reRender()
        } else if (this.props.item) {
            this.state.rec_id = this.props.item.id
            if (this.is_init) {
                await this.setStyle()
                this.is_init = false
            }
            await this.fetchData(this.props.item)
        }
    }

    /**
     * Sets the style for the graph tile.
     * @function
     */
    setStyle() {
        let cardStyle = "";
        if (this.props.style) {
            Object.keys(this.props.style).forEach(key => {
                let val = this.props.style[key];
                if (!val.endsWith(';')) val += ';';
                let k = key === 'card_width' ? 'width' : key;
                cardStyle += `${k}:${val} `;
            });
        }
        this.state.cardStyle = cardStyle + " border-radius: 12px;"
        // The chart root must fill the card BELOW the header, not take the card's
        // full height — giving it the full height pushed it past the card by the
        // header height, so the chart overflowed into the card below. flex:1 in the
        // flex-column card sizes it to the remaining space; ECharts fits via its RO.
        this.state.style = "width:100%;flex:1;min-height:0;"
    }

    /**
     * Sets the options for the graph based on the provided props.
     * @param {Object} props - The props for configuring the graph.
     * @function
     */
    setOptions(props) {
        var params = {
            toolFeatures: {},
            measureNames: props.measureNames || {},
            color_mappings: props.color_mappings || [],
            annotations: props.annotations || [],
            isDarkMode: this.props.isDarkMode || false,
            hidePieSliceLabels: props.hidePieSliceLabels || false,
            pieLegendBottom: props.pieLegendBottom,
        }
        if (this.props.themeColor) {
            params.themeColor = this.props.themeColor
        }
        let measures = props.measures
        if (!measures && props.measure) {
            try {
                measures = JSON.parse(props.measure.replaceAll("'", '"'))
            } catch (e) {
                measures = []
            }
        }
        this.maker = new ChartMaker(props.data, props.dimension, measures || [],
            props.name, props.type, props.dimension_axis, params)
    }

    /**
     * Handles the click event on the chart.
     * @param {Event} ev - The click event.
     * @function
     */
    onClickChart(ev) {
        var hasData = true
        if (this.props.value) {
            hasData = Boolean(this.props.value.data?.length)
        }
        this.props.onClickChart(ev, hasData);
    }

    /**
     * Adds the graph element to the DOM.
     * @async
     * @function
     */
    addElement() {
        if (status(this) === "destroyed") return

        // Defer initial render until the element scrolls into view so ECharts
        // animation plays when the user can actually see it.
        if (!this._hasRenderedOnce && !this._isVisible) {
            this._pendingRender = true;
            return;
        }
        this._pendingRender = false;

        this.ready = new Promise(resolve => { this._resolveReady = resolve; });

        const themeName = this.props.isDarkMode ? `${this.state.theme}_dark` : this.state.theme
        const needsFullInit = !this.eChart || this.eChart.isDisposed() || this._lastTheme !== themeName;
        if (!needsFullInit) {
            // ECharts already live and theme unchanged — just update options in place.
            // Avoids dispose+500ms gap that makes legend clicks unresponsive.
            try {
                if (this.options) {
                    this._animating = true;
                    // Preserve user's legend selections across setOption(notMerge:true).
                    // notMerge:true wipes legend.selected, causing visual/state mismatch
                    // where a grayed series can't be un-grayed by clicking again.
                    const savedLegend = {};
                    try {
                        const cur = this.eChart.getOption();
                        if (cur && cur.legend) {
                            cur.legend.forEach(l => { if (l.selected) Object.assign(savedLegend, l.selected); });
                        }
                    } catch (_) {}
                    this.eChart.setOption(this.options, true);
                    if (Object.keys(savedLegend).length) {
                        this.eChart.setOption({ legend: { selected: savedLegend } });
                    }
                    this.eChart.resize();
                }
                this._hasRenderedOnce = true;
                this.eChart.one('finished', () => {
                    this._animating = false;
                    this._setupRadarTooltip();
                    this.props.setImage(this.Image, this.maker?.name || 'Chart', this.props.item?.id || this.props.value?.id)
                    if (this._resolveReady) { this._resolveReady(); this._resolveReady = null; }
                });
            } catch (e) {
                console.error("ECharts setOption error:", e);
                this._animating = false;
                if (this._resolveReady) { this._resolveReady(); this._resolveReady = null; }
            }
            return;
        }
        setTimeout(() => {
            if (status(this) === "destroyed") {
                if (this._resolveReady) { this._resolveReady(); this._resolveReady = null; }
                return;
            }
            try {
                if (this.eChart) {
                    this.eChart.dispose();
                }
                this.eChart = echarts.init(this.rootRef.el, themeName)
                this._lastTheme = themeName;
                if (this.options) {
                    this._animating = true;
                    this.eChart.setOption(this.options, true)
                }
                this._hasRenderedOnce = true;

                // Chart element click handler for Drill-Down
                this.eChart.on('click', (params) => {
                    if (params.componentType === 'series') {
                        this.onChartClick(params);
                    }
                });
                // Use one() not on() to avoid accumulating handlers across theme switches.
                // Do NOT call resize() here — it triggers ResizeObserver mid-click and
                // causes ZRender to restart hit-area calc, making legend clicks get lost.
                this.eChart.one('finished', () => {
                    this._animating = false;
                    this._setupRadarTooltip();
                    this.props.setImage(this.Image, this.maker?.name || 'Chart', this.props.item?.id || this.props.value?.id)
                    if (this._resolveReady) { this._resolveReady(); this._resolveReady = null; }
                })

            } catch (e) {
                console.error("ECharts init error:", e);
                if (this._resolveReady) { this._resolveReady(); this._resolveReady = null; }
            }
        }, 500);
    }

    /**
     * Handles drill-down when a chart element is clicked.
     * Maps the clicked dimension to a domain and opens the related records.
     * @param {Object} params - ECharts click parameters.
     */
    onChartClick(params) {
        const rootData = this.props.value || this.props.item;
        const model = rootData?.model;
        const field = rootData?.dimension_field;

        if (!model || !field) return;

        // Build domain for the clicked point
        let drillDomain = [[field, "=", params.name]];
        
        // Add existing sheet filters if they are in Odoo domain format
        const sheetFilters = rootData.where || [];
        sheetFilters.forEach(f => {
            if (f.is_active && f.domain_py_expression) {
                // Assuming domain_py_expression is a valid Odoo domain list
                try {
                    const filters = typeof f.domain_py_expression === 'string' 
                        ? JSON.parse(f.domain_py_expression) 
                        : f.domain_py_expression;
                    if (Array.isArray(filters)) {
                        drillDomain = drillDomain.concat(filters);
                    }
                } catch(e) {}
            }
        });

        // Execute Odoo action to open list view
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: `${rootData.name}: ${params.name}`,
            res_model: model,
            domain: drillDomain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    /**
     * Fetches data for the graph based on the provided item.
     * @param {Object} item - The item containing information for data retrieval.
     * @function
     */
    fetchData(item) {
        if (status(this) == "destroyed") return
        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            if (!res || (res && res.__query_error__)) {
                const msg = res && res.message ? res.message : _t('The query returned no data.');
                this.state.hasData = false;
                this.options = {
                    graphic: [{
                        type: 'text',
                        left: 'center',
                        top: 'center',
                        style: { text: msg, fill: '#999', font: '14px sans-serif' }
                    }]
                };
                this.addElement();
                return;
            }

            try {
                let measuresList = item.measure;
                if (typeof measuresList === 'string') {
                    try {
                        measuresList = JSON.parse(measuresList);
                    } catch (e) {
                        measuresList = JSON.parse(measuresList.replaceAll("'", '"'));
                    }
                }
                const measureAliases = measuresList.map(m => typeof m === 'object' ? m.alias : m);
                const measureNames = (Array.isArray(measuresList) ? measuresList : []).reduce((acc, m) => {
                    if (typeof m === 'object' && m.isPreset) {
                        acc[m.alias] = m.value;
                    }
                    return acc;
                }, {});

                let props = {
                    data: res,
                    name: item.name,
                    measures: measureAliases,
                    measureNames: measureNames,
                    dimension: item.dimension,
                    dimension_axis: item.dimension_axis,
                    type: item.type,
                    id: item.id,
                    color_mappings: item.color_mappings || [],
                    annotations: item.annotations || [],
                }
                this.state.hasData = Boolean(res?.length)
                item.data = res; // Preserve data for re-renders on resize
                this.setOptions(props)
                this.options = await this.maker.makeGraphOptions()
                this.addElement()
            } catch(err) {
                console.error("GraphTile render error for:", item.name, err);
            }
        }).catch(err => {
            console.error("GraphTile fetchData RPC error:", err);
        });
    }

    /**
     * Gets the base64-encoded image of the chart.
     * @member {string}
     * @readonly
     */
    get Image() {
        var imgSrc
        try {
            imgSrc = this.eChart.getDataURL({
                type: 'png',
                pixelRatio: 1,
                backgroundColor: '#fff',
            });
        } catch (e) {
            console.warn("Could not get Image from eChart")
        }
        return imgSrc;
    }

    get showZoom() {
        const valueType = this.props.value?.type;
        const itemType = this.props.item?.type;
        return !NO_ZOOM_CHARTS.includes(valueType || itemType);
    }

    async zoom(arg) {
        let dz = this.options.dataZoom[0];
        if (dz.start === 0) {
            if (arg === 'in') {
                if (dz.end > 10) dz.end -= 1;
            } else {
                if (dz.end < 100) dz.end += 1;
            }
            this.state.zoom = 100 - dz.end;
        } else {
            if (arg === 'in') {
                if (dz.start < 100) dz.start += 1;
            } else {
                if (dz.start > 10) dz.start -= 1;
            }
            this.state.zoom = dz.start;
        }
        this.state.showZoom = true;
        setTimeout(() => {
            this.state.showZoom = false;
        }, 500)
        this.eChart?.dispose()
        this.eChart = null
        this.addElement()
    }
}

GraphTile.template = "GraphTile";
GraphTile.defaultProps = {
    style: {
        height: `400px;`,
        width: `440px;`,
    },
    footer: false,
    onClickChart: () => {
    },
    setImage: () => {
    },
    theme: "",
    reRender: true,
    width: "",
    isDarkMode: false,
}
GraphTile.props = {
    onClickChart: {type: Function, optional: true},
    onChartPointClick: {type: Function, optional: true},
    reRender: {type: Boolean, optional: true},
    width: {type: String, optional: true},
    setImage: {type: Function, optional: true},
    style: {type: Object, optional: true},
    theme: {type: String, optional: true},
    themeColor: {type: Object, optional: true},
    value: {type: Object, optional: true},
    item: {type: Object, optional: true},
    footer: {type: Boolean, optional: true},
    slots: {type: Object, optional: true},
    toggleClass: {type: String, optional: true},
    itemId: {type: Number, optional: true},
    isDarkMode: {type: Boolean, optional: true},
    showNoteHint: {type: Boolean, optional: true},
    isCreator: {type: Boolean, optional: true},
    name: {type: String, optional: true},
}