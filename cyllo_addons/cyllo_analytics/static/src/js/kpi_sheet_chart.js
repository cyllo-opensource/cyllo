/** @odoo-module **/
import { Component, useState, useRef, onWillStart, useEffect } from "@odoo/owl";
import { KpiSheet } from "@cyllo_analytics/js/KpiSheet";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { convertToTitleCase } from "./chart_maker"

export class KpiSheetChart extends KpiSheet {
    setup() {
        super.setup();
        this.kpiCardRef = useRef("kpiCard");
        this.orm = useService('orm')
        useEffect(() => {
            if (this.state.query.query) {
                this.fetchData(this.state.query)
            }
        }, () => [this.state.query.query])
        useEffect(() => {
            this.setStyle()
        }, () => [this.props.style])
        useEffect(() => {
            if (this.kpiCardRef.el) {
                // Determine themeColor or fallback to dashboard system variable
                const themeColor = this.props.theme?.theme_color_ids?.[0] || this.props.theme_color || 'var(--dashboard-primary-color, #ff4d4f)';
                this.kpiCardRef.el.style.setProperty('--kpi-color', themeColor);
            }
        });
    }

    setStyle() {
        var style = Object.keys(this.props.style).map(key => {
            return `${key}:${this.props.style[key]}`;
        }).join('');
        this.state.style = style
    }

    get kpiData() {
        if (this.state.query.data) {
            var key = this.state.query.measures[0]
            var val = 0
            var result = this.state.query.data
            if (result) {
                for (let i = 0; i < result.length; i++) {
                    val = val + result[i][key];
                }
            }
            return val.toFixed(2)
        }
    }

    get kpiTarget() {
        if (this.state.target && this.state.query.data) {
            const target_value = Number(this.state.target)
            const kpi_data = this.kpiData
            const growth = ((kpi_data / target_value) * 100)
            this.state.kpiTarget = growth.toFixed(2)
            return this.state.kpiTarget
        }
    }

    setPercentage() {
    }

    fetchData(item) {
        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            this.state.query.data = res
            this.state.query.measures = eval(item.measure)
            this.env.bus.trigger('KPI_LOADED')
        }).catch(() => {
            this.env.bus.trigger('KPI_LOADED')
        })
    }

    get Title() {
        return convertToTitleCase(this.props.name, " ")
    }
}

KpiSheetChart.defaultProps = {
    style: {
        height: `215px;`,
        width: `500px;`,
    },
    footer: false,
    editSheet: false,
}

KpiSheetChart.template = owl.xml`
    <div t-ref="kpiCard" class="cy_tile_o chart-container-absolute cy-kpi-top-card"
         t-att-style="!props.editSheet ? state.style : 'inset: 0px; width: auto; height: auto;'">
        <t t-if="state.measureView === 'View 2'">
            <t t-call="kpi.sheet.view.type.2"/>
        </t>
        <t t-elif="state.measureView === 'no_view'">
            <t t-call="kpi.sheet.view.type.3"/>
        </t>
        <t t-else="">
            <t t-call="kpi.sheet.view.type.1"/>
        </t>
    </div>
`