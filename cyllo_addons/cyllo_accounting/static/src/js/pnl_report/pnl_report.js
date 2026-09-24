/** @odoo-module **/
import { useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AccountingReportBase } from "../accounting_report_base/accounting_report_base";

/**
 * PnLReport class represents a Profit and Loss report.
 * It extends the AccountingReportBase class.
 */
export class PnlReport extends AccountingReportBase {
    model = "abstract.financial.report"
    ledgerId = 7;
    sidebarClass = {
        off: "",
        on: "",
        bodyOn: "balance_body_on",
        bodyOff: "balance_body_off",
    }

    setup() {
        super.setup()
        this.filterState = useState({
            journal_ids: [],
            account_ids: [],
            analytic_ids: [],
            target_move: ['posted'], //['draft', 'posted']
            get_filters: true
        })
        const cf = this._ctxFilters
        if (cf.journal_ids.length) this.filterState.journal_ids = cf.journal_ids
        if (cf.account_ids.length) this.filterState.account_ids = cf.account_ids
        if (cf.analytic_ids.length) this.filterState.analytic_ids = cf.analytic_ids
        if (cf.target_move) this.filterState.target_move = cf.target_move
        this.state = useState({
            comparison: 1, //defaults to 1
            comparisonCopy: 1,
            comparisonType: "month", //year or month
            data: [],
            journals: [],
            accounts: [],
            analytics: [],
            isFolded: true,
        })
        /**
        * Loads the data when the comparison value or the date filter value changes.
        */
        useEffect(() => {
            this.loadData()
        }, () => [this.state.comparison, this.filters.dateFilterValue, this.filters.startDate, this.filters.endDate])
        useEffect((comparison) => {
            if (!comparison) return
            if (comparison < 1) {
                this.state.comparisonCopy = 1
            } else if (comparison >= 5) {
                this.state.comparisonCopy = 5
            }
        }, () => [this.state.comparisonCopy])
    }

    get filterContext() {
        const { startDate: start_date, endDate: end_date } = this.filters
        return { ...this.filterState, start_date, end_date, filter_type: this.filters.dateFilterValue }
    }

    get args() {
        const { comparison, comparisonType } = this.state
        return [comparison, comparisonType]
    }

    get pdfData() {
        const report = "cyllo_accounting.report_profit_n_loss"
        const { comparison, comparisonType } = this.state
        const filterData = { ...this.filterContext, comparison_value: comparison, comparison_type_value: comparisonType }
        return [report, report, {
            reportName: "Profit And Loss Report",
            filterData,
            periods: this.periodData,
            filterBy: this.dateFilterValue
        }]
    }

    get xlsxData() {
        const report = "report.cyllo_accounting.report_profit_n_loss"
        const { comparison, comparisonType } = this.state
        const filterData = { ...this.filterContext, comparison_value: comparison, comparison_type_value: comparisonType }
        return [report, {
            reportName: "Profit And Loss Report",
            filterData,
            periods: this.periodData,
            filterBy: this.dateFilterValue
        }]
    }


    get records() {
        return this.state.data
    }

    get currencySymbol() {
        return this.records[0]?.currency_symbol ?? "$"
    }

    get commonReportDropdownProps() {
        return {
            records: this.records,
            parentTemplate: "commonPNLParent",
            currencySymbol: this.currencySymbol,
            getAccountLine: this.getAccountLine.bind(this),
            childTemplate: "commonPNLChild",
            ledgerId: this.ledgerId,
            openGeneralLedger: this.openGeneralLedger.bind(this),
            openAnnotation: this.openAnnotation.bind(this),
            removeAnnotation: this.removeAnnotation.bind(this)
        }
    }

    async loadData() {
        const { startDate, endDate } = this.filters
        if (!startDate || !endDate) return;
        const [accountingReportData, filters] = await this.getReport()
        this.state.data = accountingReportData
        Object.assign(this.state, { ...filters })
        this.filterState.get_filters = false
    }

    async addFilters(filterId, filterKey) {
        if (this.filterState[filterKey].includes(filterId)) {
            const index = this.filterState[filterKey].indexOf(filterId);
            if (index !== -1) {
                this.filterState[filterKey].splice(index, 1);
            }
        } else {
            this.filterState[filterKey].push(filterId)
        }
        await this.loadData()
    }

    toggleUnfold() {
        const { isFolded } = this.state
        if (isFolded) {
            this.env.bus.trigger('UNFOLD_ALL:REPORT_LINE')
            this.state.isFolded = false
        } else {
            this.env.bus.trigger('FOLD_ALL:REPORT_LINE')
            this.state.isFolded = true
        }
    }

    getAccountLines(field) {
        const records = this.records.map(item => item[field][0]);
        const shouldHaveData = this.records.some(item => item[field][2] !== 0)
        return shouldHaveData ? records : []
    }


    getAccountLine(accountId, accountLines) {
        const accountInfo = accountLines.flatMap(item => item.filter(acc => acc.id === accountId))
        return accountInfo.some(item => item.amount !== 0) ? accountInfo : []
    }

    async writeAnnotation(accountId, value, account) {
        await this.orm.call("account.account", "write_annotations", [accountId, this.ledgerId, value])
        for (const rec of this.state.data) {
            const record = rec[account][0].find(acc => acc.id === accountId)
            record.annotations = { [this.ledgerId]: value }
        }
    }

    async removeAnnotation(accountId, account) {
        await this.orm.call("account.account", "remove_annotations", [accountId, this.ledgerId])
        for (const rec of this.state.data) {
            const record = rec[account][0].find(acc => acc.id === accountId)
            record.annotations = {}
        }
    }

}

PnlReport.template = "PnlReport"
registry.category("actions").add("pnl_report", PnlReport);
