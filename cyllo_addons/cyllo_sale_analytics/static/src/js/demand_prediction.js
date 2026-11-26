/** @odoo-module **/
import { registry } from "@web/core/registry"
import { onWillStart, useState, Component, useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import {useResize} from "@cyllo_base/js/hooks"
import { FilterDropdown } from "@cyllo_analytics/js/filterDropdown";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";


export class DemandPredictionDashboard extends Component {

    setup() {
        this.demandState = useState({
            productTable: [],
            actStartDate: '',
            actEndDate: '',
            defaultProduct: [],
            periodDemand: 10,
            frequencyDemand: 'D',
            noData: '',
            showTable: '',
            'formattedDate': {
                'startDate': '',
                'endDate': '',
                'frequency': '',
                'period':''
            },
            status: "block",
            chartData: [],
            labels: {},
            // per-product trend badge (second half vs first half of the window)
            productStats: {},
            // product variants that actually have a photo (initials otherwise)
            productImages: {},
        })
        this.orm = useService('orm')
        this.root = useRef('root')
        this.chartContainer = useRef('chart-container')
        this.tableScroll = useRef('table-scroll')
        this.actionService = useService('action')
        this.notification = useService('notification')
        this.ui = useService('ui')
        useResize("root", (width) => {
            this.state.width = width / 12
        });
        this.analyticsTable = useState({
            analysisTableActual : [],
            analysisTableForecast : [],
        })

        this.state = useState({
            typeChart: 'bar',
            width: 0,
            search: '',
            prodList: [],
        })
        useEffect(() => {
            if(this.state.search){
                this.state.prodList = this.demandState.productTable.filter(item => {
                    var search = this.state.search.toLowerCase()
                    return Object.values(item)[0][1].toLowerCase().includes(search)
                })
            } else {
                this.state.prodList = this.demandState.productTable
            }
        }, () => [this.state.search])
        useEffect(() => {
            const render = async () => {
                if (this.myChart) {
                    this.myChart.dispose()
                }
                await this.renderGraph()
            }
            if (this.demandState.chartData.length) {
                let promise = render();
            }
        }, () => [this.state.width, this.demandState.chartData]);
        // park the period table on the actual/forecast boundary every time a
        // new forecast comes back (runs after the DOM patch)
        useEffect(() => {
            this.scrollTableToForecast();
        }, () => [this.analyticsTable.analysisTableForecast]);

        onWillStart(async () => {
            this.demandState.labels = await this.orm.call('sale.order', 'get_demand_labels', []);
            this.demandForecastAction();
        });
        useEffect(() => {
            const getLimit = (freq) => {
                switch (freq) {
                    case "D":
                       return 250;
                    case "M":
                       return 150;
                    case "Y":
                       return 50;
                }
            }
            const maxLimit = getLimit(this.demandState.frequencyDemand)
            this.demandState.periodDemand = this.demandState.periodDemand < 0 ? 0 : this.demandState.periodDemand > maxLimit ? maxLimit : this.demandState.periodDemand
        }, () => [this.demandState.periodDemand, this.demandState.frequencyDemand])
    }
    renderGraph() {
        const element = this.chartContainer.el?.querySelector("#demand_prediction_chart")
        if (!this.demandState.chartData.length || !element) {
            return;
        }
        const actualRows = this.analyticsTable.analysisTableActual;
        const forecastRows = this.analyticsTable.analysisTableForecast;
        const rows = this.demandState.chartData;
        const split = actualRows.length;
        const dates = rows.map((item) => item.date);
        const qty = rows.map((item) => Number(item.qty) || 0);
        const actualData = qty.map((v, i) => (i < split ? v : null));
        const forecastData = qty.map((v, i) => (i >= split ? v : null));
        const isBar = this.state.typeChart === 'bar';
        const hasForecast = forecastRows.length > 0 && split > 0;
        this.myChart = echarts.init(element);
        const series = [
            {
                name: 'Actual',
                type: this.state.typeChart,
                data: actualData,
                smooth: true,
                symbolSize: 6,
                barMaxWidth: 18,
                itemStyle: {
                    color: '#a3b315',
                    borderRadius: isBar ? [4, 4, 0, 0] : 0,
                },
                lineStyle: { width: 2.5, color: '#a3b315' },
                emphasis: { focus: 'series' },
            },
            {
                name: 'Forecast',
                type: this.state.typeChart,
                data: forecastData,
                smooth: true,
                symbolSize: 6,
                barMaxWidth: 18,
                itemStyle: {
                    color: '#e2453c',
                    borderRadius: isBar ? [4, 4, 0, 0] : 0,
                },
                lineStyle: { width: 2.5, color: '#e2453c' },
                label: isBar ? {
                    show: true,
                    position: 'top',
                    color: '#b3382f',
                    fontSize: 10,
                    fontWeight: 600,
                } : { show: false },
                emphasis: { focus: 'series' },
                markArea: hasForecast ? {
                    silent: true,
                    itemStyle: { color: 'rgba(226, 69, 60, 0.07)' },
                    data: [[{ xAxis: dates[split] }, { xAxis: dates[dates.length - 1] }]],
                } : undefined,
                markLine: hasForecast ? {
                    silent: true,
                    symbol: 'none',
                    label: { show: false },
                    lineStyle: { color: '#e2453c', type: 'dashed', width: 1, opacity: 0.6 },
                    data: [{ xAxis: dates[split] }],
                } : undefined,
            },
        ];
        // keep the actual/forecast boundary in view (a few actual periods on
        // the left, the whole horizon on the right)
        const visibleTail = split > 0 ? Math.max(2, dates.length - split) + 4 : dates.length;
        const zoomStart = dates.length > visibleTail
            ? Math.max(0, ((dates.length - visibleTail) / dates.length) * 100)
            : 0;
        const option = {
            grid: { left: 44, right: 16, top: 28, bottom: 30, containLabel: false },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
            },
            legend: { show: false },
            xAxis: {
                type: 'category',
                data: dates,
                axisTick: { show: false },
                axisLine: { lineStyle: { color: '#e6e6df' } },
                axisLabel: { color: '#8b9098', fontSize: 11, hideOverlap: true, formatter: (value) => this.shortDate(value) },
            },
            yAxis: {
                type: 'value',
                splitLine: { lineStyle: { color: '#f0f0ea' } },
                axisLabel: { color: '#8b9098', fontSize: 11 },
            },
            series,
            dataZoom: [{
                type: 'inside',
                id: 'insideX',
                xAxisIndex: 0,
                start: zoomStart,
                end: 100,
                zoomOnMouseWheel: false,
                moveOnMouseMove: true,
                moveOnMouseWheel: true,
            }],
        };
        this.myChart.setOption(option);
    }
    async datePeriod(ev) {
        this.demandForecastAction();
    }

    get dateToday() {
        var today = new Date().toISOString().split('T')[0]
        return today
    }

    async demandForecastAction() {
        var demand_option = {
            'actStartDate': this.demandState.actStartDate,
            'actEndDate': this.demandState.actEndDate,
            'period': this.demandState.periodDemand,
            'frequency': this.demandState.frequencyDemand,
        };
        this.demandState.noData = true;
        this.demandState.status = "none";
        this.demandState.showTable = true;
        var results = await this.orm.call('sale.order','product_demand_forecast',[demand_option,this.demandState.defaultProduct])
        if(results){
            this.demandState.noData = results['no_data'];
            this.demandState.status = "block";
            if (this.demandState.actStartDate == '' && this.demandState.actEndDate == ''){
                this.demandState.actStartDate = results['start_date'];
                this.demandState.actEndDate = results['end_date'];
            }
            this.demandState.productTable = results['product_list'];
            this.state.prodList = results['product_list'];
            this.demandState.defaultProduct = results['current_product'];
            this.demandState.productStats = results['product_stats'] || {};
            this.loadProductTrends();
            this.loadProductImages();
            var chartData = results['chart_data'];
            this.demandState.chartData = chartData;
            this.analyticsTable.analysisTableActual = results['table_act_data'];
            this.analyticsTable.analysisTableForecast = results['table_fore_data']
            this.demandState.formattedDate.startDate = moment(this.demandState.actStartDate).format('YYYY/MM/DD')
            this.demandState.formattedDate.endDate = moment(this.demandState.actEndDate).format('YYYY/MM/DD')
            this.demandState.formattedDate.period = this.demandState.periodDemand
            this.demandState.formattedDate.frequency = this.demandState.frequencyDemand
        }
        else {
            this.demandState.noData = false;
            this.demandState.status = "none";
            this.demandState.showTable = false;
        }
    }

    onClickProduct(product){
        this.demandState.defaultProduct = product;
        this.demandForecastAction()
    }

    // ─────────────────────────────────────────────────────────────────────
    // Product rail helpers
    // ─────────────────────────────────────────────────────────────────────
    /** "[FURN_9999] Office Design Software" -> "[FURN_9999]" */
    prodCode(name) {
        const match = /^\s*\[([^\]]+)\]/.exec(name || '');
        return match ? `[${match[1]}]` : '';
    }

    /** "[FURN_9999] Office Design Software" -> "Office Design Software" */
    prodName(name) {
        const match = /^\s*\[([^\]]+)\]\s*(.*)$/.exec(name || '');
        return match ? match[2] : (name || '');
    }

    /** Two-letter avatar text built from the product name. */
    prodInitials(name) {
        const words = this.prodName(name)
            .replace(/[^A-Za-z0-9 ]/g, ' ')
            .split(/\s+/)
            .filter(Boolean);
        if (!words.length) {
            return '?';
        }
        if (words.length === 1) {
            return words[0].slice(0, 2).toUpperCase();
        }
        return (words[0][0] + words[1][0]).toUpperCase();
    }

    avatarColor(index) {
        const palette = [
            '#8a9a00', '#c07f22', '#7f9a6d', '#8a6fb0',
            '#a8562f', '#5f8c88', '#b05060', '#6d7f9a',
        ];
        return palette[index % palette.length];
    }

    prodDelta(productId) {
        const stats = this.demandState.productStats || {};
        const delta = stats[productId];
        return (delta === undefined || delta === null) ? null : delta;
    }

    prodDeltaLabel(productId) {
        const delta = this.prodDelta(productId);
        if (delta === null) {
            return '';
        }
        if (delta === 'new') {
            return 'New';
        }
        const capped = Math.max(-999, Math.min(999, Math.round(delta)));
        return `${capped > 0 ? '+' : ''}${capped}%`;
    }

    prodDeltaClass(productId) {
        const delta = this.prodDelta(productId);
        if (delta === 'new') {
            return 'is-new';
        }
        return Number(delta) >= 0 ? 'is-up' : 'is-down';
    }

    /** "2026/10/10" or "2026-10-10" -> "Oct 10" (other formats untouched). */
    shortDate(value) {
        const text = value == null ? '' : String(value);
        const match = /^(\d{4})[\/-](\d{2})[\/-](\d{2})$/.exec(text);
        if (!match) {
            return text;
        }
        const date = new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00`);
        if (isNaN(date.getTime())) {
            return text;
        }
        return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
    }

    // ─────────────────────────────────────────────────────────────────────
    // KPI values
    // ─────────────────────────────────────────────────────────────────────
    formatMoney(value) {
        const amount = parseFloat(value) || 0;
        return '$ ' + amount.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        });
    }

    formatNumber(value) {
        return (parseFloat(value) || 0).toLocaleString('en-US');
    }

    get actualRows() {
        return this.analyticsTable.analysisTableActual || [];
    }

    get forecastRows() {
        return this.analyticsTable.analysisTableForecast || [];
    }

    /** Units / revenue / peak of the forecast horizon. */
    get forecastTotals() {
        let qty = 0;
        let revenue = 0;
        let peak = null;
        for (const row of this.forecastRows) {
            const rowQty = Number(row.qty) || 0;
            qty += rowQty;
            revenue += Number(row.subtotal ?? row.sub_total) || 0;
            if (!peak || rowQty > peak.qty) {
                peak = { qty: rowQty, date: row.date };
            }
        }
        return { qty, revenue, peak };
    }

    /** Same-length window of actual periods right before the forecast. */
    get comparedActuals() {
        const length = this.forecastRows.length || 1;
        return this.actualRows.slice(-length);
    }

    get comparedUnits() {
        return this.comparedActuals.reduce(
            (sum, row) => sum + (Number(row.qty) || 0), 0);
    }

    get comparedRevenue() {
        return this.comparedActuals.reduce(
            (sum, row) => sum + (Number(row.sub_total ?? row.subtotal) || 0), 0);
    }

    get unitsDeltaPct() {
        if (!this.comparedUnits) {
            return null;
        }
        return Math.round(
            ((this.forecastTotals.qty - this.comparedUnits) / this.comparedUnits) * 100);
    }

    get revenueDelta() {
        return this.forecastTotals.revenue - this.comparedRevenue;
    }

    get avgPrice() {
        const rows = this.forecastRows.length ? this.forecastRows : this.actualRows;
        const last = rows[rows.length - 1];
        return last ? (Number(last.avg_price) || 0) : 0;
    }

    get comparedPeriods() {
        return this.comparedActuals.length;
    }

    get accuracyMetrics() {
        const actuals = this.actualRows.map((row) => Number(row.qty) || 0);
        const recent = actuals.slice(-8);
        const recentAvg = recent.length
            ? recent.reduce((sum, value) => sum + value, 0) / recent.length
            : 0;
        const forecasts = this.forecastRows.map((row) => Number(row.qty) || 0);
        const forecastAvg = forecasts.length
            ? forecasts.reduce((sum, value) => sum + value, 0) / forecasts.length
            : 0;
        const deviation = Math.abs(forecastAvg - recentAvg);
        const mape = recentAvg ? (deviation / recentAvg) * 100 : 0;
        return {
            accuracy: Math.max(0, Math.min(99, Math.round(100 - mape))),
            mape: Math.round(mape * 10) / 10,
            periods: recent.length,
        };
    }

    get accuracy() {
        return this.accuracyMetrics.accuracy;
    }

    get mape() {
        return this.accuracyMetrics.mape;
    }

    /**
     * Which products actually have a photo. Binary search domains are not
     * reliable on the variant, so this asks the template (where image_128 is
     * a stored column) and maps the answer back to the variants in the rail.
     */
    async loadProductImages() {
        const ids = (this.demandState.productTable || []).map(
            (item) => Object.values(item)[0][0]);
        if (!ids.length) {
            this.demandState.productImages = {};
            return;
        }
        try {
            const variants = await this.orm.read(
                'product.product', ids, ['product_tmpl_id']);
            const templateByVariant = {};
            for (const variant of variants) {
                if (variant.product_tmpl_id) {
                    templateByVariant[variant.id] = variant.product_tmpl_id[0];
                }
            }
            const templateIds = [...new Set(Object.values(templateByVariant))];
            const withImage = templateIds.length
                ? await this.orm.search(
                    'product.template',
                    [['id', 'in', templateIds], ['image_128', '!=', false]])
                : [];
            const withImageSet = new Set(withImage);
            const map = {};
            for (const [variantId, templateId] of Object.entries(templateByVariant)) {
                if (withImageSet.has(templateId)) {
                    map[variantId] = true;
                }
            }
            this.demandState.productImages = map;
        } catch (error) {
            // initials stay as a perfectly fine fallback
            this.demandState.productImages = {};
        }
    }

    prodImage(productId) {
        return Boolean((this.demandState.productImages || {})[productId]);
    }

    /**
     * Per-product trend for the rail badges: quantity sold in the second half
     * of the selected window compared with the first half. One grouped read
     * per half — the forecast RPC only covers the selected product.
     */
    async loadProductTrends() {
        const start = this.demandState.actStartDate;
        const end = this.demandState.actEndDate;
        if (!start || !end) {
            return;
        }
        const startMs = new Date(start).getTime();
        const endMs = new Date(end).getTime();
        const midDate = new Date(startMs + (endMs - startMs) / 2);
        const mid = midDate.toISOString().slice(0, 10);
        const baseDomain = [
            ['order_id.state', '=', 'sale'],
            ['order_id.date_order', '>=', start],
            ['order_id.date_order', '<=', end],
        ];
        try {
            const [firstHalf, secondHalf] = await Promise.all([
                this.orm.readGroup(
                    'sale.order.line',
                    [...baseDomain, ['order_id.date_order', '<=', mid]],
                    ['product_uom_qty:sum'],
                    ['product_id']),
                this.orm.readGroup(
                    'sale.order.line',
                    [...baseDomain, ['order_id.date_order', '>', mid]],
                    ['product_uom_qty:sum'],
                    ['product_id']),
            ]);
            const before = {};
            for (const group of firstHalf) {
                if (group.product_id) {
                    before[group.product_id[0]] = group.product_uom_qty || 0;
                }
            }
            const stats = {};
            for (const group of secondHalf) {
                if (!group.product_id) {
                    continue;
                }
                const productId = group.product_id[0];
                const firstQty = before[productId] || 0;
                const secondQty = group.product_uom_qty || 0;
                if (!secondQty) {
                    continue;
                }
                if (!firstQty) {
                    // no sales in the first half — a percentage would be a lie
                    stats[productId] = 'new';
                    continue;
                }
                stats[productId] = Math.round(
                    ((secondQty - firstQty) / firstQty) * 100);
            }
            for (const [productId, firstQty] of Object.entries(before)) {
                if (!(productId in stats) && firstQty) {
                    // sold in the first half only: demand dropped to zero
                    stats[productId] = -100;
                }
            }
            this.demandState.productStats = stats;
        } catch (error) {
            // the badges are decorative — never break the dashboard for them
            this.demandState.productStats = {};
        }
    }

    get periodUnit() {
        const unit = this.demandState.frequencyDemand;
        if (unit === 'M') {
            return 'months';
        }
        if (unit === 'Y') {
            return 'years';
        }
        return 'days';
    }

    /** Index of the selected product in the rail (keeps the avatar colour
     *  consistent between the rail tile and the product header card). */
    get selectedProductIndex() {
        const productId = this.demandState.defaultProduct?.[0];
        const index = (this.demandState.productTable || []).findIndex(
            (item) => Object.values(item)[0][0] === productId);
        return Math.max(0, index);
    }

    /** Header subtitle, e.g. "Predicted demand for 10 days". */
    get demandSummary() {
        const period = this.demandState.formattedDate.period
            || this.demandState.periodDemand || 10;
        const unit = this.periodUnit;
        const label = Number(period) === 1 ? unit.replace(/s$/, '') : unit;
        return `Predicted demand for ${period} ${label}`;
    }

    /** Selected product name without the "[SKU] " prefix. */
    get selectedProductName() {
        return this.prodName(this.demandState.defaultProduct?.[1] || '');
    }

    /** Put the actual/forecast boundary in view inside the period table. */
    scrollTableToForecast() {
        const el = this.tableScroll.el;
        if (!el) {
            return;
        }
        const cells = Array.from(el.querySelectorAll('thead th'));
        const firstForecast = el.querySelector('thead th.is-forecast');
        if (!firstForecast) {
            el.scrollLeft = 0;
            return;
        }
        const scrollerLeft = el.getBoundingClientRect().left;
        const offsetOf = (cell) =>
            cell.getBoundingClientRect().left - scrollerLeft + el.scrollLeft;
        // a table that (almost) fits should simply start at its first column —
        // scrolling it would just hide columns behind the sticky label
        const overflow = el.scrollWidth - el.clientWidth;
        if (overflow < 140) {
            el.scrollLeft = 0;
            return;
        }
        // the label column is sticky, so the visible columns start after it
        const labelWidth = cells[0] ? cells[0].getBoundingClientRect().width : 0;
        const forecastIndex = cells.indexOf(firstForecast);
        // keep two actual periods before the boundary, but never show a half
        // column: snap the scroll position to a column edge
        const anchorIndex = Math.max(1, forecastIndex - 2);
        const anchor = cells[anchorIndex];
        if (!anchor) {
            el.scrollLeft = 0;
            return;
        }
        el.scrollLeft = Math.min(overflow, Math.max(0, offsetOf(anchor) - labelWidth));
    }

    async exportDemandPDF(){
        var chart = this.root.el?.querySelector('.chart-col')
            || this.root.el?.querySelector('.cy-no_data')
        if (!chart) {
            return this.notification.add(
                _t("There is nothing to export yet."),
                { type: "warning" }
            );
        }
        this.ui.block({ message: _t("Preparing your PDF export…") });
        try {
            await new Promise((resolve) => setTimeout(resolve, 0));
            var canvas = await html2canvas(chart)
            var chartImg = canvas.toDataURL('image/png');
            return await this.actionService.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: 'cyllo_sale_analytics.report_demand_prediction',
                report_file: "cyllo_sale_analytics.report_demand_prediction",
                data: {
                    chartImg,
                    'start_date': moment(this.demandState.actStartDate).format('YYYY/MM/DD'),
                    'end_date': moment(this.demandState.actEndDate).format('YYYY/MM/DD'),
                    'current_prod': this.demandState.defaultProduct[1],
                    'actual_data': this.analyticsTable.analysisTableActual,
                    'forecast_data': this.analyticsTable.analysisTableForecast,
                    'period': this.demandState.periodDemand,
                    'frequency': this.demandState.frequencyDemand,
                }
            });
        } finally {
            this.ui.unblock();
        }
    }

    async exportDemandPNG(){
        var content = this.root.el?.querySelector('.chart-col')
            || this.root.el?.querySelector('.cy-no_data')
        if (!content) {
            return this.notification.add(
                _t("There is nothing to export yet."),
                { type: "warning" }
            );
        }
        this.ui.block({ message: _t("Preparing your PNG export…") });
        try {
            await new Promise((resolve) => setTimeout(resolve, 0));
            var canvas = await html2canvas(content);
            var image = canvas.toDataURL('image/png');
            var link = document.createElement('a');
            link.download = 'Demand_Prediction_Dashboard.png';
            link.href = image;
            link.click();
        } finally {
            this.ui.unblock();
        }
    }

    async exportDemandXLSX(){
        var dataList = {
            'start_date' : moment(this.demandState.actStartDate).format('YYYY/MM/DD'),
            'end_date' : moment(this.demandState.actEndDate).format('YYYY/MM/DD'),
            'period' : this.demandState.periodDemand,
            'frequency' : this.demandState.frequencyDemand,
            'product' : this.demandState.defaultProduct[1],
            'actual' : this.analyticsTable.analysisTableActual,
            'predict' : this.analyticsTable.analysisTableForecast,
        }
        var action = {
               'data': {
                    'model': 'sale.order',
                    'data': JSON.stringify(dataList),
                    'output_format': 'xlsx',
                    'report_name': 'Demand Prediction Report',
               },
           };
        this.ui.block({ message: _t("Preparing your XLSX export…") });
        try {
            await new Promise((resolve) => setTimeout(resolve, 0));
            await download({
                url: '/smartd_xlsx_reports',
                data: action.data,
            });
        } catch (error) {
            this.notification.add(
                _t("Could not download the report. Please try again."),
                { type: "danger" });
        } finally {
            this.ui.unblock();
        }
    }

    onClickChartType(type){
        // Switching bar <-> line only repaints the chart: re-running the
        // forecast would refit Prophet for nothing.
        if (this.state.typeChart === type) {
            return;
        }
        this.state.typeChart = type;
        if (this.myChart) {
            this.myChart.dispose();
            this.myChart = null;
        }
        this.renderGraph();
    }

}
DemandPredictionDashboard.components = { FilterDropdown, DropdownItem, Dropdown }
DemandPredictionDashboard.template = "DemandPredictionDashboard";
registry.category("actions").add("demand_prediction", DemandPredictionDashboard);