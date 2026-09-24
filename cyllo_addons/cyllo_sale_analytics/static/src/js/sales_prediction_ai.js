/** @odoo-module **/
import {registry} from "@web/core/registry"
import {onMounted, useState, Component, useRef, useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {useResize} from "@cyllo_base/js/hooks"
import {FilterDropdown} from "@cyllo_analytics/js/filterDropdown"
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class SalesPredictionAiDashboard extends Component {
    setup() {
        this.graphState = useState({
            'start_date': '',
            'end_date': '',
            'frequency': 'D',
            'period': 10,
            'formattedDate': {
                'startDate': '',
                'endDate': '',
                'frequency': '',
                'period': '',
            }
        })
        this.stateChart = useState({
            typeChart: 'bar',
            chartDataSales: true,
            isChartVisible: true,
            chartData: '',
            actual_sale_data: '',
            predict_sale_data: '',
            res: 0,
            metrics: {},
            summary: '',
            showSummary: false
        })
        this.state = useState({width: 0})
        this.orm = useService('orm')
        this.actionService = useService("action")
        this.root = useRef('root')
        this.canvas = useRef('canvas')
        this.notification = useService("notification");
        useResize("root", (width) => this.state.width = width / 12);
        useEffect(() => {
            const render = async () => {
                if (this.myChart) {
                    this.myChart.dispose()
                }
                await this.renderGraph()
            }
            if (this.stateChart.res) {
                let promise = render();
            }
        }, () => [this.state.width, this.stateChart.res, this.stateChart.chartData]);

        onMounted(async () => {
            await this.renderSalesChart();
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
            const maxLimit = getLimit(this.graphState.frequency)
            this.graphState.period = this.graphState.period < 0 ? 0 : this.graphState.period > maxLimit ? maxLimit : this.graphState.period
        }, () => [this.graphState.period, this.graphState.frequency])
    }

    async filter_date(ev) {
        await this.renderSalesChart();
    }

    get dateToday() {
        var today = new Date().toISOString().split('T')[0]
        return today
    }

    async renderSalesChart() {
        var date_dict = {
            'start_date': this.graphState.start_date,
            'end_date': this.graphState.end_date,
            'period': this.graphState.period,
            'frequency': this.graphState.frequency,
        };

        this.orm.call('sale.order', 'forecast_configure_ai', [date_dict]).then(async (results) => {
            if (results[0]) {
                this.stateChart.chartDataSales = true;
                this.stateChart.isChartVisible = true;
                this.stateChart.chartData = results[0];
                this.stateChart.actual_sale_data = results[4]
                this.stateChart.predict_sale_data = results[5]
                this.stateChart.res = results[1]
                this.stateChart.metrics = results[6] || {}
                this.stateChart.summary = results[7] || ''
                if (!this.graphState.start_date && !this.graphState.end_date) {
                    this.graphState.start_date = results[2];
                    this.graphState.end_date = results[3];
                }
            } else if (results[0] == false || results == false) {
                this.stateChart.chartDataSales = false;
                this.stateChart.isChartVisible = false;
            }
            this.graphState.formattedDate.startDate = moment(this.graphState.start_date).format('YYYY/MM/DD')
            this.graphState.formattedDate.endDate = moment(this.graphState.end_date).format('YYYY/MM/DD')
            this.graphState.formattedDate.period = this.graphState.period
            this.graphState.formattedDate.frequency = this.graphState.frequency
        });
    }

    async renderGraph() {
        this.myChart = echarts.init(this.root.el?.querySelector('#sale_forecast_chart'), null);
        let {chartData: forecast_data, res} = this.stateChart
        let {actual_sale_data, predict_sale_data} = this.stateChart
        let forecastLength = actual_sale_data.length + predict_sale_data.length
        let option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: Object.keys(forecast_data)
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}              '
                },
                axisPointer: {
                    snap: true
                }
            },
            series: [{
                type: this.stateChart.typeChart,
                smooth: true,
                data: Object.values(forecast_data),
            }],
            visualMap: {
                show: false,
                dimension: 0,
                pieces: [{
                    lte: 0,
                    color: '#9ea700'
                },
                    {
                        gt: 0,
                        lte: res - 1,
                        color: '#9ea700'
                    },
                    {
                        gt: res - 1,
                        color: '#ff3333'
                    }
                ]
            },
            dataZoom: [{
                type: 'inside',
                id: 'insideX',
                XAxisIndex: 0,
                start: forecastLength > 30 ? 45 : 0,
                end: 100,
                zoomOnMouseWheel: false,
                moveOnMouseMove: true,
                moveOnMouseWheel: true
            }]
        };
        option && this.myChart.setOption(option);
    }

    async exportSalePDF() {
        const chart = this.stateChart.chartDataSales ? this.canvas.el.querySelector("canvas") : this.root.el?.querySelector('.cy-sales-forcaste_graph-area')
        const canvas = await html2canvas(chart)
        const chartImg = canvas.toDataURL('image/png');
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: 'cyllo_sale_analytics.report_sales_prediction',
            report_file: "cyllo_sale_analytics.report_sales_prediction",
            data: {
                chartImg,
                'start_date': moment(this.graphState.start_date).format('YYYY/MM/DD'),
                'end_date': moment(this.graphState.end_date).format('YYYY/MM/DD'),
                'actual_sale_data': this.stateChart.actual_sale_data,
                'predict_sale_data': this.stateChart.predict_sale_data,
                'chart_data_sales': this.stateChart.chartDataSales,
                'period': this.graphState.period,
                'frequency': this.graphState.frequency,
            }
        });
    }

    async exportSalePNG() {
        const content = this.stateChart.chartDataSales ? this.canvas.el.querySelector("canvas") : this.root.el?.querySelector('.cy-sales-forcaste_graph-area')
        if (content) {
            const canvas = await html2canvas(content);
            const image = canvas.toDataURL('image/png');
            const link = document.createElement('a');
            link.download = 'Sales_Prediction_AI_Dashboard.png';
            link.href = image;
            link.click();
        }
    }

    onClickTypeChart(type) {
        this.stateChart.typeChart = type;
        this.renderGraph();
    }

    toggleSummary() {
        this.stateChart.showSummary = !this.stateChart.showSummary;
    }

    closeSummary() {
        this.stateChart.showSummary = false;
    }
}

SalesPredictionAiDashboard.components = {FilterDropdown, Dropdown, DropdownItem}
SalesPredictionAiDashboard.template = "SalesPredictionAiDashboard";
registry.category("actions").add("sales_prediction_ai", SalesPredictionAiDashboard);
