/* @odoo-module */
import { Component, useEffect, useState,onMounted } from "@odoo/owl";
import { useBus,useService } from "@web/core/utils/hooks";
import { formatCurrency } from "@web/core/currency";


export class ReconcileLines extends Component {
    setup() {
        this.action = useService("action");
        useBus(this.env.bus, "validate-lines", this.validateLines);
        this.formatCurrency = formatCurrency;
    }

    validateLines() {
        this.action.doAction('soft_reload');
    }

}
ReconcileLines.props={
    value: { type: Object, optional: true },
    onClick: { type: Function, optional: true },
    isActive: { type: Boolean, optional: true },
}
ReconcileLines.template = `ReconcileLines`;