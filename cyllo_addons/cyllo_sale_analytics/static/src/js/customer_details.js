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
            width: 0,
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
    resizeContainer(width) {
        this.state.width = width / 12;
    }

    // Translated churn label (Yes/No/Waiting -> At-Risk/Loyal/Waiting).
    churnLabel(v) {
        return (this.state.labels && this.state.labels[v]) || v;
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
            const freqChart = echarts.init(this.rootRef.el.querySelector('#freq_chart'), null, this.chartDimension)
            const monChart = echarts.init(this.rootRef.el.querySelector('#mon_chart'), null, this.chartDimension)
            this.renderDetails(freqChart, frequencyValues, this.state.labels.total_sale_orders || 'Total Sale Orders')
            this.renderDetails(monChart, monetaryValues, this.state.labels.total_sale_amount || 'Total Sale Amount')
        }
    }

    get chartDimension() {
        const { width } = this.state
        const wRatio = 6.0606
        const hRatio = 3.7879

        return {
            width: width * wRatio,
            height: width * hRatio
        }
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

    renderDetails(chart, vals, name) {
        const data = Object.keys(vals).map((key) => ({
            name: key,
            value: vals[key],
        }));
        const option = {
            title: {
                text: name,
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            xAxis: {
                type: 'category',
                data: data.map((item) => item.name),
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}'
                },
                axisPointer: {
                    snap: true
                }
            },
            series: [
                {
                    name: name,
                    type: 'bar',
                    data: data.map((item) => item.value),
                },
            ],
        };
        chart.setOption(option);
    }
}

// Define the template for the CustomerChurnDetails component
CustomerChurnDetails.template = "CustomerChurnDetails"
registry.category("actions").add("cyllo_sale_analytics.customer_details", CustomerChurnDetails);