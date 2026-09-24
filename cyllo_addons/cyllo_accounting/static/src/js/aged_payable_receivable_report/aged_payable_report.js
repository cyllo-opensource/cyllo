/** @odoo-module */
import { registry } from "@web/core/registry";
import { AgedReceivable } from "./aged_receivable_report"

class AgedPayable extends AgedReceivable {
    ledgerId = 4

    get args() {
        return ['liability_payable', this.pager.offset, this.pager.limit]
    }

    get pdfData() {
        const report = 'cyllo_accounting.aged_payable'
        return [report, report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName }]
    }

    get xlsxData() {
        const report = 'report.cyllo_accounting.aged_payable'
        return [report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }
 }

registry.category("actions").add("age_p", AgedPayable);
