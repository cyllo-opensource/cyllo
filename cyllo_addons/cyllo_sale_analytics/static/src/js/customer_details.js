/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart, onMounted, useRef } = owl
import { browser } from "@web/core/browser/browser";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { useResize } from "@cyllo_base/js/hooks"

export class CustomerChurnDetails extends Component {
    setup() {
        this.rootRef = useRef("root")
        this.actionService = useService("action");
        this.savedContext = useSaveContext()
        this.state = useState({
            custDetails: [],
            dateRange: [],
            period: [],
            chartData: [],
            saleOrders: {},
            labels: {},
        });
        useResize("root", this.resizeContainer.bind(this));
        this.orm = useService('orm')
        onWillStart(async () => {
            var cust, dateRange, period, dateRangeIso
            if (this.props.action.context.cust) {
                ({ cust, dateRange, period, dateRangeIso } = this.props.action.context)
                this.savedContext.saveManually(this.props.action.context, "context")
            } else {
                ({ cust, dateRange, period, dateRangeIso } = this.savedContext.context)
            }
            this.state.custDetails = cust
            this.state.dateRange = dateRange;
            this.state.dateRangeIso = dateRangeIso;
            this.state.period = period;
            this.state.labels = await this.orm.call('res.partner', 'get_churn_labels', []);
        })
        onMounted(async () => {
            await this.renderChart()
            await this.getSale()
        })
    }
    resizeContainer() {
        // The two bar charts live in fixed-height cards, so they can simply
        // follow the width of the box they sit in.
        for (const chart of this._charts || []) {
            const dom = chart.getDom();
            if (dom && dom.clientWidth && dom.clientHeight) {
                chart.resize({ width: dom.clientWidth, height: dom.clientHeight });
            }
        }
    }

    // Translated churn label (Yes/No/Waiting -> At-Risk/Loyal/Waiting).
    churnLabel(v) {
        return (this.state.labels && this.state.labels[v]) || v;
    }

    /** Colour family of a churn verdict (drives text + pill colours). */
    churnTone(v) {
        if (v === 'No') return 'is-ok';
        if (v === 'Waiting') return 'is-warn';
        return 'is-bad';
    }

    /** Short helper line shown under the churn verdict. */
    churnNote(v) {
        if (v === 'No') return 'Healthy account';
        if (v === 'Waiting') return 'Awaiting purchase history';
        return 'Needs attention';
    }

    /** Colour family of a sale order state. */
    orderStateTone(v) {
        if (v === 'sale' || v === 'done') return 'is-ok';
        if (v === 'cancel') return 'is-bad';
        return 'is-warn';
    }

    /** Money like the churn dashboard list: "$ 1,990" / "$ 2,947.5". */
    formatMoney(value) {
        const n = parseFloat(value) || 0;
        return '$ ' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    // Translated period word (Quarter/Half Year/Year/Month), for chart x-axis.
    periodLabel() {
        const p = this.state.period || '';
        const key = String(p).toLowerCase().replace(/ /g, '_');
        return (this.state.labels && this.state.labels[key]) || p;
    }

    renderChart() {
        const frequencyValues = {};
        const monetaryValues = {};
        for (const key in this.state.custDetails) {
            const f_regex = /^frequency_(\d+)$/;
            const m_regex = /^monetary_(\d+)$/;
            const freq_match = key.match(f_regex);
            const mon_match = key.match(m_regex);
            if (freq_match) {
                const i = freq_match[1];
                frequencyValues[`${this.periodLabel()}-${i}`] = this.state.custDetails[key];
            }
            if (mon_match) {
                const i = mon_match[1];
                monetaryValues[`${this.periodLabel()}-${i}`] = this.state.custDetails[key];
            }
        }
        if (this.state.custDetails.total_sales) {
            const freqEl = this.rootRef.el.querySelector('#freq_chart');
            const monEl = this.rootRef.el.querySelector('#mon_chart');
            if (!freqEl || !monEl) return;
            this._charts = [];
            const freqChart = this._initChart(freqEl);
            const monChart = this._initChart(monEl);
            this.renderDetails(freqChart, frequencyValues, this.state.labels.total_sale_orders || 'Total Sale Orders')
            this.renderDetails(monChart, monetaryValues, this.state.labels.total_sale_amount || 'Total Sale Amount')
        }
    }

    /** Chart sized to the card that holds it (see .cy-cust-plot). */
    _initChart(el) {
        const chart = window.echarts.init(el, null, {
            width: el.clientWidth || 420,
            height: el.clientHeight || 220,
        });
        this._charts.push(chart);
        return chart;
    }

    getSale() {
        let dateRange = this.state.dateRangeIso || this.state.dateRange;
        if (dateRange) {
            dateRange.forEach(async (date, index) => {
                const domain = [['date_order', '>=', date[0]], ['date_order', '<=', date[1]], ['partner_id', '=', this.state.custDetails.custId]];
                this.state.saleOrders[`${index + 1}`] = await this.orm.searchRead("sale.order", domain);
            });
        }
    }

    goBack() {
        browser.history.go(-1)
    }

    onClickSaleOrder(orderId) {
        this.actionService.doAction({
            name: "Sale",
            res_model: "sale.order",
            res_id: orderId,
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
            target: "current",
        });
    }

    /** All orders of this customer inside one period (the card's View All). */
    openAllOrders(periodKey) {
        const domain = [["partner_id", "=", this.state.custDetails.custId]];
        const range = (this.state.dateRangeIso || [])[Number(periodKey) - 1];
        if (range && range.length === 2) {
            domain.push(["date_order", ">=", range[0]], ["date_order", "<=", range[1]]);
        }
        return this.actionService.doAction({
            name: "Sale Orders",
            res_model: "sale.order",
            type: "ir.actions.act_window",
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    renderDetails(chart, vals, name) {
        const data = Object.keys(vals).map((key) => ({
            name: key,
            value: vals[key],
        }));
        const option = {
            // the card header carries the title; nothing is drawn in the plot
            grid: { left: 6, right: 12, top: 16, bottom: 4, containLabel: true },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(158, 167, 0, 0.07)' } },
                backgroundColor: '#ffffff',
                borderColor: '#eceee2',
                borderWidth: 1,
                padding: [8, 12],
                textStyle: { color: '#2b2f26', fontSize: 12 },
                extraCssText: 'border-radius: 10px; box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);',
            },
            xAxis: {
                type: 'category',
                data: data.map((item) => item.name),
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#8b9182', fontSize: 11 },
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#a8ad9e', fontSize: 11 },
                splitLine: { lineStyle: { color: '#edefe4', type: 'dashed' } },
                axisPointer: {
                    snap: true
                }
            },
            series: [
                {
                    name: name,
                    type: 'bar',
                    data: data.map((item) => item.value),
                    barMaxWidth: 46,
                    itemStyle: {
                        borderRadius: [8, 8, 0, 0],
                        color: {
                            type: 'linear',
                            x: 0,
                            y: 0,
                            x2: 0,
                            y2: 1,
                            colorStops: [
                                { offset: 0, color: '#b6c21c' },
                                { offset: 1, color: '#9ea700' },
                            ],
                        },
                    },
                    emphasis: { itemStyle: { color: '#8f9800' } },
                },
            ],
        };
        chart.setOption(option);
    }
}

// Define the template for the CustomerChurnDetails component
CustomerChurnDetails.template = "CustomerChurnDetails"
registry.category("actions").add("cyllo_sale_analytics.customer_details", CustomerChurnDetails);