/** @odoo-module **/
import { registry } from "@web/core/registry"
import { onWillStart, useState, Component, useRef, useEffect} from "@odoo/owl";
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
        })
        this.orm = useService('orm')
        this.root = useRef('root')
        this.chartContainer = useRef('chart-container')
        this.actionService = useService('action')
        this.notification = useService('notification')
        useResize("root", (width) => {
            this.state.width = width / 12
        });
        this.analyticsTable = useState({
            analysisTableActual : [],
            analysisTableForecast : [],
        })
        this.responsiveness = useState({
            sideBarOn: false,
        })
        this.env.bus.addEventListener("SIDEBAR_MENU_TOGGLE", ({detail}) => {
            this.responsiveness.sideBarOn = !this.responsiveness.sideBarOn
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
    get getBodyClass() {
        const {noData, status} = this.demandState
        if (noData && status !== 'none') {
            if (this.responsiveness.sideBarOn) {
                return "w-93"
            }
            return "w-82"
        }
        return ""
    }
    get getHeaderClass() {
        const {noData, status} = this.demandState
        if (noData && status !== 'none') {
            if (this.responsiveness.sideBarOn) {
                return "w-95"
            }
            return "w-84"
        }
        return ""
    }
    renderGraph() {
        const element = this.chartContainer.el?.querySelector("#demand_prediction_chart")
        if (this.demandState.chartData.length && element) {
            this.myChart = echarts.init(element);
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
                    data: this.demandState.chartData.map((item) => item.date),
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
                    type: this.state.typeChart,
                    smooth: true,
                    data: this.demandState.chartData.map((item) => item.qty),
                }],
                visualMap: {
                    show: false,
                    dimension: 0,
                    pieces: [{
                        lte: 0,
                        color: '#9ea700'
                    },
                    {
                        gt:0,
                        lte: (this.analyticsTable.analysisTableActual.length) - 1,
                        color: '#9ea700'
                    },
                    {
                        gt: (this.analyticsTable.analysisTableActual.length) - 1,
                        color: '#ff3333'
                    }
                    ]
                },
                dataZoom: [{
                    type: 'inside',
                    id: 'insideX',
                    XAxisIndex: 0,
                    start: 45,
                    end: 100,
                    zoomOnMouseWheel: false,
                    moveOnMouseMove: true,
                    moveOnMouseWheel: true
                  }]
            };
            option && this.myChart.setOption(option);
        }
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

    async exportDemandPDF(){
        var chart = this.root.el?.querySelector('.chart-col')
            || this.root.el?.querySelector('.cy-no_data')
        var canvas = await html2canvas(chart)
        var chartImg = canvas.toDataURL('image/png');
        return this.actionService.doAction({
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
        var canvas = await html2canvas(content);
        var image = canvas.toDataURL('image/png');
        var link = document.createElement('a');
        link.download = 'Demand_Prediction_Dashboard.png';
        link.href = image;
        link.click();
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
        try {
            await download({
                url: '/smartd_xlsx_reports',
                data: action.data,
            });
        } catch (error) {
            this.notification.add(
                _t("Could not download the report. Please try again."),
                { type: "danger" });
        }
    }

    onClickChartType(type){
        // typeChart drives the ECharts series type; demandForecastAction()
        // re-fetches and re-renders the graph from scratch.
        this.state.typeChart = type;
        this.demandForecastAction()
    }

}
DemandPredictionDashboard.components = { FilterDropdown, DropdownItem, Dropdown }
DemandPredictionDashboard.template = "DemandPredictionDashboard";
registry.category("actions").add("demand_prediction", DemandPredictionDashboard);