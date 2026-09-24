/** @odoo-module **/
import {AccountingReportBase} from "../accounting_report_base/accounting_report_base";
import {registry} from "@web/core/registry";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {useEffect, useState, onMounted} from "@odoo/owl";
import {ReportDropdownWithPager} from "../generalLedgerReport/reportDropdownWithPager";
import {PartnerSelection} from "../components/partnerSelection";

export class BankBookReport extends AccountingReportBase {
    model = 'bank.cash.book.report'
    ledgerId = 8;
    sidebarClass = {
        off: "",
        on: "",
        bodyOn:"balance_body_on",
        bodyOff: "balance_body_off",
    }


    setup() {
        super.setup();
        this.state = useState({
            accountEntries: {},
            accounts: [],
            all_account: [],
            totalDebit: null,
            totalCredit: null,
            totalBalance: null,
            currency: null,
            filtered_partner: null,
            partner_ids: [],
            isFolded: true,
            openAccounts: []
        });
        this.filterState = useState({
            // ...this.filters,
            journal_ids: [],
            account_ids: [],
            target_move: ['posted'], //['draft', 'posted']
            get_filters: true,
            selected_partners: [],
        })
        const cf = this._ctxFilters
        if (cf.account_ids.length) this.filterState.account_ids = cf.account_ids
        if (cf.partner_ids.length) this.filterState.selected_partners = cf.partner_ids
        if (cf.target_move) this.filterState.target_move = cf.target_move
        onMounted(()=> {
            const openAccounts = this.saveContext.getKeyValue(this.reportName)
            if (openAccounts?.length && !this.state.openAccounts.length) {
                this.state.openAccounts = openAccounts
            }
        })
        useEffect(() => {
            const loadData = async () => {
                await this.loadData()
            }
            loadData()
        }, () => [this.filters.startDate, this.filters.endDate, this.filterState.selected_partners, this.filterState.account_ids])
    }

    get partner_args() {
        return ['bank']
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

    get args() {
        return ['bank']
    }

    get currencySymbol() {
        return this.state.currency
    }


    async getPartner() {
        const {startDate, endDate} = this.filters
        this.state.partner_ids = await this.orm.call(
            this.model, "get_partner", [...this.partner_args, startDate, endDate])
    }

    async loadData() {
        const {
            account_entries,
            all_account,
            accounts,
            total_debit,
            total_credit,
            total_balance,
            currency_id
        } = await this.getReport()
        this.state.accountEntries = account_entries
        this.state.accounts = accounts
        this.state.all_account = all_account
        this.state.totalBalance = total_balance
        this.state.totalDebit = total_debit
        this.state.totalCredit = total_credit
        this.state.currency = currency_id
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

    get filterContext() {
        return {
            parent_state: this.filterState.target_move,
            accounts: this.filterState.account_ids,
            partners: this.filterState.selected_partners,
            startDate: this.filters.startDate,
            endDate: this.filters.endDate,
            company_ids: this.company.activeCompanyIds
        }
    }

    get pdfData() {
        const report = 'cyllo_accounting.report_bank_book'
        return [report, report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }

    get xlsxData() {
        const report = 'report.cyllo_accounting.report_bank_book'
        return [report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }

    async writeAnnotation(moveLineId, value, account) {
        await super.writeAnnotation(...arguments);
        const record = this.state.accountEntries[account][0].find(move => move.id === moveLineId)
        record.annotations = {[this.ledgerId]: value}
    }

    async removeAnnotation(moveLineId, account) {
        await super.removeAnnotation(...arguments)
        const record = this.state.accountEntries[account][0].find(move => move.id === moveLineId)
        record.annotations = {}
    }

    onClickAccount(account, click) {
        if (click) {
            this.state.openAccounts.push(account)
        } else {
            const index = this.state.openAccounts.indexOf(account);
            if (index !== -1) {
                this.state.openAccounts.splice(index, 1); // Remove 1 item at index
            }
        }
    }

    async saveSession() {
        this.removeSession = false
        await this.saveContext.saveToSession(this.reportName, this.state.openAccounts, true)
    }

    async openJournal(res_id, name) {
        await this.saveSession()
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            res_id,
            name
        })
    }

    async getAccountData(data) {
        const kwargs = {...this.filterContext, ...data.accountData, account_name: data.account}
        return await this.orm.call(this.model, "get_account_data", this.args, kwargs)
    }

    async updateMoveLines(data) {
        this.state.accountEntries[data.account] = await this.getAccountData(data)

    }
    async onClickPartners() {
        await this.getPartner()
        this.dialog.add(PartnerSelection, {
            selectedPartners: this.filterState.selected_partners,
            domain: [['id', 'in', this.state.partner_ids]],
            addPartner: this.addPartner.bind(this)
        })
    }
    addPartner(partnerIds) {
        this.filterState.selected_partners = partnerIds
    }
}

BankBookReport.template = "BankBookReport"
BankBookReport.components = {
    ...AccountingReportBase.components,
    MultiRecordSelector, ReportDropdownWithPager
}
registry.category("actions").add("bank_book", BankBookReport);
