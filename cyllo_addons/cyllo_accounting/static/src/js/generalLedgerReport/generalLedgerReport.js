/* @odoo-module */
import {useState, useEffect, onMounted, onWillDestroy} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {AccountingReportBase} from "../accounting_report_base/accounting_report_base";
import {ReportDropdownWithPager} from "./reportDropdownWithPager";

export class GeneralLedgerReport extends AccountingReportBase {
    model = "report.cyllo_accounting.general_ledger"
    ledgerId = 1;

    sidebarClass = {
        off: "",
        on: "",
        bodyOn: "general_ledger_body_on",
        bodyOff: "general_ledger_body_off",
    }

    setup() {
        super.setup();
        this.state = useState({
            journals: [],
            data: [],
            isFolded: true,
            currencySymbol: "$",
            accountDataPage: {},
            openAccounts: []
        })
        this.filterState = useState({
            get_filters: true,
            journal_ids: [],
            analytic_ids: [],
            target_move: ['posted'],
        })
        const cf = this._ctxFilters
        if (cf.journal_ids.length) this.filterState.journal_ids = cf.journal_ids
        if (cf.analytic_ids.length) this.filterState.analytic_ids = cf.analytic_ids
        if (cf.target_move) this.filterState.target_move = cf.target_move
        useEffect(() => {
            this.loadData()
        }, () => [this.filters.dateFilterValue, this.filters.startDate, this.filters.endDate])
        onMounted(() => {
            const {accountId, breadCrumb} = this.props.action.context
            if (typeof accountId === 'number') {
                this.state.openAccounts.push(accountId)
            } else if (typeof accountId === 'object') {
                this.state.openAccounts = accountId
            }
            this.breadCrumbs = breadCrumb || false;
            const openAccounts = this.saveContext.getKeyValue(this.reportName)
            if (openAccounts?.length && !this.state.openAccounts.length) {
                this.state.openAccounts = openAccounts
            }
        })
        this.removeSession = true
        //FIXME: somehow the removeSession becomes true again after calling the saveSession
        // onWillDestroy(() => this.removeSession && this.saveContext.removeManually(this.model))
    }

    get filterContext() {
        const {startDate: start_date, endDate: end_date} = this.filters
        return {
            ...this.filterState,
            start_date,
            end_date,
            company_ids: this.company.activeCompanyIds,
            filter_type: this.filters.dateFilterValue
        }
    }

    toggleUnfold() {
        const {isFolded} = this.state
        if (isFolded) {
            this.env.bus.trigger('UNFOLD_ALL:REPORT_LINE')
            this.state.isFolded = false
        } else {
            this.env.bus.trigger('FOLD_ALL:REPORT_LINE')
            this.state.isFolded = true
        }
    }

    get records() {
        return this.state.data
    }

    get currencySymbol() {
        return this.state.currencySymbol
    }

    get sumRecords() {
        return this.state.sumData
    }

    get xlsxData() {
        const filterData = {...this.filterContext}
        return [this.model, {
            reportName: this.reportName,
            filterData,
        }]
    }

    get pdfData() {
        const report = 'cyllo_accounting.report_general_ledger'
        const filterData = {...this.filterContext}
        return [report, report, {
            reportName: this.reportName,
            filterData,
        }]
    }

    get grandTotal() {
        let totalDebit = 0
        let totalCredit = 0
        let grandTotal = 0
        if (this.sumRecords) {
            for (const rec of Object.keys(this.sumRecords)) {
                const record = this.sumRecords[rec][0]
                totalDebit += record.total_debit
                totalCredit += record.total_credit
            }
            grandTotal = (totalDebit - totalCredit).toFixed(2)
        }
        return {totalDebit, totalCredit, grandTotal}
    }

    get reportDropdownProps() {
        return {
            parentTemplate: 'parentGeneralLedger',
            childTemplate: 'childGeneralLedger',
            sumRecords: this.sumRecords,
            currencySymbol: this.currencySymbol,
            records: this.records,
            gotoJournalItem: this.gotoJournalItem.bind(this),
            accountDataPage: this.state.accountDataPage,
            updateMoveLines: this.updateMoveLines.bind(this),
            openAnnotation: this.openAnnotation.bind(this),
            openJournal: this.openJournal.bind(this),
            removeAnnotation: this.removeAnnotation.bind(this),
            ledgerId: this.ledgerId,
            openAccounts: this.state.openAccounts,
            onClickAccount: this.onClickAccount.bind(this),
            callBackKey: "generalLedger"
        }
    }

    async onClickAccount(accountId, click) {
        // Note: the dropdown passes the numeric account_id here (not the display
        // name key used by state.data / accountDataPage).
        if (click) {
            const account = Object.entries(this.sumRecords).find(
                ([, sums]) => sums[0]?.account_id === accountId
            )?.[0]
            this.state.openAccounts.push(accountId)
            // Detail lines are not loaded up front (only per-account totals are),
            // so fetch this account's first page when it is expanded. getAccountData
            // returns the data keyed by display name, which updateMoveLines stores.
            await this.updateMoveLines({
                accountData: {account, account_id: accountId, limit: 100, offset: 0},
            })
        } else {
            const index = this.state.openAccounts.indexOf(accountId);
            if (index !== -1) {
                this.state.openAccounts.splice(index, 1); // Remove 1 item at index
            }
        }
    }

    async loadData() {
        const {startDate, endDate} = this.filters
        if (!startDate || !endDate) return;
        // Only the per-account totals are loaded initially; the detail lines are
        // lazy-loaded per account on expand (see onClickAccount).
        const [generalReport, generalSumReport, accountDataPage, filters, currencySymbol] =
            await this.orm.call(this.model, "get_report", [], {
                ...this.filterContext,
                summary_only: true
            })
        this.state.data = generalReport[0]
        this.state.sumData = generalSumReport[0]
        this.state.currencySymbol = currencySymbol
        this.state.accountDataPage = accountDataPage
        Object.assign(this.state, {...filters})
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

    async getAccountData(data) {
        const kwargs = {...this.filterContext, ...data}
        return await this.orm.call(this.model, "get_account_data", [], kwargs)
    }

    async updateMoveLines(data) {
        const [accountData, accountPageData] = await this.getAccountData(data.accountData)
        const key = Object.keys(accountData)[0]
        this.state.data[key] = accountData[key]
        this.state.accountDataPage[key] = accountPageData[key]
    }

    async saveSession() {
        this.removeSession = false
        await this.saveContext.saveToSession(this.reportName, this.state.openAccounts, true)
    }

    async gotoJournalItem(accountId, account) {
        await this.saveSession()
        const domain = await this.getDomain(accountId, account)
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move.line",
            search_view_id: [this.searchViewId, 'search'],
            views: [[false, "tree"], [false, "form"]],
            domain,
            name: account,
            context: {
                search_default_date_between: 1,
                date_from: this.filterContext['start_date'],
                date_to: this.filterContext['end_date'],
                search_default_group_by_account: 1,
                search_default_journal_ids_in: this.filterContext['journal_ids'].length,
                search_default_account_ids_in: 1,
                account_ids: [accountId],
                journal_ids: this.filterContext['journal_ids'],
                search_default_posted: this.filterContext['target_move'].length === 1
            }
        })
    }

    async getDomain(accountId, account) {
        if (this.filterContext['analytic_ids'].length) {
            const [accountData, dummy] = await this.getAccountData({
                limit: 0,
                account_id: accountId
            })
            return [['id', 'in', accountData[account].map(item => item.id)]]
        } else {
            return []
        }
    }

    async openJournal(res_id, name) {
        await this.saveSession()
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            res_id,
            name
        })
    }

    async writeAnnotation(moveLineId, value, account) {
        await super.writeAnnotation(...arguments);
        const moveLine = this.records[account].find(item => item.id === moveLineId)
        moveLine.annotations = {[this.ledgerId]: value}
    }

    async removeAnnotation(moveLineId, account) {
        await super.removeAnnotation(...arguments)
        const moveLine = this.records[account].find(item => item.id === moveLineId)
        moveLine.annotations = {}
    }

}

GeneralLedgerReport.template = "GeneralLedgerReport"
GeneralLedgerReport.components = {...GeneralLedgerReport.components, ReportDropdownWithPager}
registry.category("actions").add("general_ledger", GeneralLedgerReport);
