/** @odoo-module **/
import { ChartMaker } from "./chart_maker";
import { KpiSheetChart } from "./kpi_sheet_chart";
import { Table } from "./table/table";
import { templates } from "@web/core/assets";


export class StackItem {
    constructor(element, props, theme, params = {}) {
        this.ready = this.setup(element, props, theme, params);
    }

    async setup(element, props, theme, params) {
        this.maker = new ChartMaker(
            props.data, props.dimension, props.measures,
            props.name, props.type, props.dimension_axis, params
        );
        this.options = await this.maker.makeGraphOptions();
        this.theme = theme;
        this.params = params;
        // element is .grid-stack-item-content — already absolutely positioned
        // by GridStack CSS with margin vars; getBoundingClientRect() returns
        // real pixel dimensions immediately after makeWidget().
        this.parent = element;
        try {
            this.addElement();
        } catch(e) {
            console.error('StackItem.addElement error:', e);
        }
    }

    addElement() {
        // .grid-stack-item-content is position:absolute with top/bottom set but no
        // explicit height declaration. CSS spec: child height:100% computes to auto
        // when parent height is not "explicitly specified". Calculate pixel height
        // from known grid parameters (unit = cell height px, graph_height = h rows).
        const unit = this.params.unit || 60;
        const gridH = this.params.graph_height || 3;
        const margin = 4; // must match MARGIN in edit_dashboard.fetchData
        const contentH = Math.max(gridH * unit - 2 * margin, 40);

        this.wrapper = document.createElement('div');
        this.wrapper.classList.add("edit-border", "background-color-class", "cy_tile", "cy_dashboard_chart", "card");
        // Absolutely fill the GridStack cell (.grid-stack-item-content is position:
        // absolute, so it's our containing block). This makes the wrapper EXACTLY the
        // cell size at all times — no JS height that can desync from GridStack's live
        // cell height — so the chart can never exceed the card. overflow:hidden clips
        // anything extra; the chart (this.el) resizes to fit via the ResizeObserver.
        this.wrapper.style.cssText = `position:absolute;inset:0;box-sizing:border-box;display:flex;flex-direction:column;overflow:hidden;`;

        this.header = document.createElement('div');
        this.header.className = "sheet-header d-flex justify-content-between align-items-center";
        this.title = document.createElement('div');
        this.title.className = "sheet-title";
        this.title.innerText = this.maker.name;
        this.header.appendChild(this.title);
        this.wrapper.appendChild(this.header);

        this.el = document.createElement('div');
        this.el.style.cssText = 'width:100%;flex:1;min-height:0;box-sizing:border-box;';
        this.wrapper.appendChild(this.el);

        this.parent.appendChild(this.wrapper);

        // this.el stays FLUID (width:100% + flex:1 inside a definite-height wrapper),
        // so it tracks card resizes and the ResizeObserver below keeps ECharts fitted.
        // Do NOT lock it to a fixed px width: a stale width measured before GridStack
        // positions the cell would never shrink, and the chart overflows the card.
        // Measure the realized box only for the initial ECharts size, with a computed
        // fallback in case the height chain hasn't resolved yet.
        const parentRect = this.parent.getBoundingClientRect();
        const headerH = this.header.getBoundingClientRect().height || 32;
        const rect = this.el.getBoundingClientRect();
        const chartW = Math.max(rect.width || parentRect.width || 40, 40);
        const chartH = Math.max(rect.height || (contentH - headerH - 8), 40);

        // Pass explicit pixel dimensions to ECharts so it never reads 0×0.
        const themeName = this.params.isDarkMode && this.theme ? `${this.theme}_dark` : (this.theme || undefined);
        this.eChart = echarts.init(this.el, themeName, { width: chartW, height: chartH });

        const series = Array.isArray(this.options.series)
            ? this.options.series.map(s => ({...s, animation: false, animationDuration: 0, animationDelay: 0}))
            : this.options.series;
        this.eChart.setOption({...this.options, series, animation: false, animationDuration: 0});

        // Always resize ECharts to the EXACT live box of this.el. resize() with no
        // args lets ECharts keep a stale internal width (e.g. the full-container width
        // measured before GridStack sized the cell) — passing explicit dims forces it
        // to the real cell size every time.
        const refit = () => {
            if (!this.eChart || !this.el) return;
            const r = this.el.getBoundingClientRect();
            if (r.width && r.height) this.eChart.resize({ width: r.width, height: r.height });
        };
        this.refit = refit;
        this.resizeObserver = new ResizeObserver(refit);
        this.resizeObserver.observe(this.el);
        // GridStack may finish sizing the cell AFTER this runs, so the box measured at
        // init can be too large. Refit once the layout has settled.
        requestAnimationFrame(() => requestAnimationFrame(refit));
    }

    reRender(theme, newH, newW) {
        const themeChanged = theme && theme !== this.theme;


        if (!themeChanged && newH && this.eChart) {
            if (newH) this.params = {...this.params, graph_height: newH};
            if (newW) this.params = {...this.params, graph_width: newW};
            this.refit ? this.refit() : this.eChart.resize();
            return;
        }

        if (!themeChanged && this.eChart) return; // no-op: resize handled by ResizeObserver

        // Full re-render for theme change.
        if (this.resizeObserver) this.resizeObserver.disconnect();
        if (this.eChart) { this.eChart.dispose(); this.eChart = null; }
        if (this.wrapper?.parentElement) this.wrapper.parentElement.removeChild(this.wrapper);
        if (theme) this.theme = theme;
        if (newH) this.params = {...this.params, graph_height: newH};
        if (newW) this.params = {...this.params, graph_width: newW};
        this.addElement();
    }
}


export class StackKpiItem {
    constructor(element, props, env, params = {}) {
        this.params = params;
        this.element = element;
        this.ready = this.setup(element, props, env);
    }

    async setup(element, props, env) {
        // element is .grid-stack-item-content — mount KPI component directly into it
        element.classList.add("edit-border", "kpi_class");
        await owl.mount(KpiSheetChart, element, {
            props: {
                query: props,
                kpi: props.kpi,
                editSheet: true,
                name: props.name,
            },
            env,
            templates,
        });
    }

    reRender() {}
}


export class StackTableItem {
    constructor(element, props, env, params = {}) {
        this.element = element;
        this.env = env;
        this.props = props;
        this.params = params;
        this.ready = this.setup(element, props);
    }

    async setup(element, props) {
        props.dimension = [props.dimension];
        // element is .grid-stack-item-content — mount Table component directly into it
        element.classList.add("cyllo_table");
        await this.mountChild();
    }

    reRender() {}

    async mountChild() {
        this._tableInstance = await owl.mount(Table, this.element, {
            props: {
                data: this.props,
                name: this.props.name,
                toggleClass: "edit-border",
                theme: this.params.theme,
                style: {width: '100%', height: '100%'},
            },
            env: this.env,
        });
    }
}
