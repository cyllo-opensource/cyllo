/* @odoo-module */
import {PnlReport} from "../pnl_report/pnl_report";
import {registry} from "@web/core/registry";

export class BalanceSheetReport extends PnlReport {
    static template = "BalanceSheetReport"
    reportMethod = "get_balance_sheet"

    get filterContext() {
        return {
            ...super.filterContext,
            company_ids: this.company.activeCompanyIds,
        }
    }

    get pdfData() {
        const report = "cyllo_accounting.report_balance_sheet"
        const {comparison, comparisonType} = this.state
        const filterData = {...this.filterContext, comparison_value: comparison, comparison_type_value: comparisonType}
        return [report, report, {
            reportName: "Balance Sheet Report",
            filterData,
            periods: this.periodData,
            filterBy: this.dateFilterValue
        }]
    }
}

registry.category("actions").add("balance_sheet", BalanceSheetReport);