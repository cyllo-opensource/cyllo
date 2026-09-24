/** @odoo-module **/
import {useState, onWillStart, useEffect} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {AccountingReportBase} from "../accounting_report_base/accounting_report_base";

const today = luxon.DateTime.now();

export class TrialBalance extends AccountingReportBase {
    model = "trial.balance.report"
    ledgerId = 5;
    sidebarClass = {
        off: "",
        on: "",
        bodyOn:"balance_body_on",
        bodyOff: "balance_body_off",
    }

    setup() {
        super.setup()
        this.filterState = useState({
            journal_ids: [],
            account_ids: [],
            analytic_ids: [],
            options: ['posted'],
            method: {'accural': true},
            get_filters: true,
        })
        const cf = this._ctxFilters
        if (cf.journal_ids.length) this.filterState.journal_ids = cf.journal_ids
        if (cf.account_ids.length) this.filterState.account_ids = cf.account_ids
        if (cf.analytic_ids.length) this.filterState.analytic_ids = cf.analytic_ids
        if (cf.target_move) this.filterState.options = cf.target_move
        this.state = useState({
            comparison: 1, //defaults to 0
            comparisonType: "year", //year or month
            comparisonCopy: 1,
            journals: [],
            data: [],
            total_data: {},
            total_common_data: {},
            draft: false,
        })
        useEffect(() => {
            this.loadData()
        }, () => [...this.depends])
        useEffect((comparison) => {
            if (!comparison) return
            if (comparison < 1) {
                this.state.comparisonCopy = 1
            } else if (comparison >= 5) {
                this.state.comparisonCopy = 5
            }
        }, () => [this.state.comparisonCopy])
    }

    get depends() {
        return [this.state.comparison, this.state.comparisonType, this.filters.dateFilterValue, this.state.draft]
    }

    get filterContext() {
        const {activeCompanyIds} = this.company
        const {startDate: start_date, endDate: end_date} = this.filters
        return {
            ...this.filterState,
            start_date,
            end_date,
            filter_type: this.filters.dateFilterValue,
            company_ids: activeCompanyIds
        }
    }

    get args() {
        const {comparison, comparisonType} = this.state
        return [comparison, comparisonType]
    }

    async loadData() {
        const {startDate, endDate} = this.filters
        if (!startDate || !endDate) return;
        const [reportData, filters, total_data, total_common_data] = await this.getReport()
        this.state.data = reportData
        this.state.total_data = total_data
        this.state.total_common_data = total_common_data
        Object.assign(this.state, {...filters})
        this.filterState.get_filters = false
    }

    onSelectDraftEntries(value) {
        this.filterState.options = value ? ['posted', 'draft'] : ['posted']
        this.state.draft = value
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

    get pdfData() {
        const report = "cyllo_accounting.report_trial_balance"
        const {comparison, comparisonType} = this.state
        const filterData = {...this.filterContext, comparison_value: comparison, comparison_type_value: comparisonType}
        return [report, report, {
            reportName: "Trial Balance Report",
            filterData,
            periods: this.periodData,
            filterBy: this.dateFilterValue
        }]
    }

    get xlsxData() {
        const report = "report.cyllo_accounting.report_trial_balance"
        const {comparison, comparisonType} = this.state
        const filterData = {...this.filterContext, comparison_value: comparison, comparison_type_value: comparisonType}
        return [report, {
            reportName: "Trial Balance Report",
            filterData,
            periods: this.periodData,
            filterBy: this.dateFilterValue
        }]
    }

    onClickJournal(acc_id) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move.line',
            name: "Journal Items",
            views: [[false, "list"]],
            target: "current",
            context: {
                group_by: ["account_id"],
                search_default_account_ids_in: 1,
                account_ids: [acc_id],
                search_default_date_between: 1,
                date_from: this.filters.startDate,
                date_to: this.filters.endDate,
                search_default_posted: this.filterState.options.length === 1
            },
        });

    }

    async writeAnnotation(accountId, value, account) {
        await this.orm.call("account.account", "write_annotations", [accountId, this.ledgerId, value])
        const accountData = this.state.data.find(item => item.account.id === accountId)
        accountData.account.annotations = {[this.ledgerId]: value}
    }

    async removeAnnotation(accountId, account) {
        await this.orm.call("account.account", "remove_annotations", [accountId, this.ledgerId])
        const accountData = this.state.data.find(item => item.account.id === accountId)
        accountData.account.annotations = {}
    }

    formatCurrency(val) {
        if (!this.state.currency_symbol) return val;
        if (this.state.currency_position === 'before') {
            return this.state.currency_symbol + ' ' + val;
        }
        return val + ' ' + this.state.currency_symbol;
    }
}

TrialBalance.template = "trial_balanceReport"
registry.category("actions").add("tb_r", TrialBalance);
