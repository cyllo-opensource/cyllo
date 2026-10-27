/** @odoo-module **/

import { Component } from "@odoo/owl";

export class DashboardKpi extends Component {
    onTitleClick() {
        if (this.props.onSelect && this.props.titleFilter) {
            this.props.onSelect(this.props.titleFilter);
        }
    }

    onItemClick(filter) {
        if (this.props.onSelect && filter) {
            this.props.onSelect(filter);
        }
    }

    get iconClass() {
        return `${this.props.icon || ""} cy_user_dashboard_metric_icon`;
    }

    get segments() {
        return this.props.segments || [];
    }

    get legendItems() {
        return this.props.legend || [];
    }
}
DashboardKpi.template = "DashboardKpi";
DashboardKpi.components = {};
DashboardKpi.props = {
    title: String,
    titleFilter: { type: String, optional: true },
    titleTip: { type: String, optional: true },
    value: { type: Number, optional: true },
    icon: { type: String, optional: true },
    segments: { type: Array, optional: true },
    legend: { type: Array, optional: true },
    onSelect: { type: Function, optional: true },
};
