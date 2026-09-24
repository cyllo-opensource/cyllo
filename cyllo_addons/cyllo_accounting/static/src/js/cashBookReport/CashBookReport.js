/** @odoo-module **/
import {BankBookReport} from "../bankBookReport/bankBookReport";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {useEffect, useState} from "@odoo/owl";


export class CashBookReport extends BankBookReport {
    model = 'bank.cash.book.report'
    ledgerId = 9;

    setup() {
        super.setup();
        this.orm = useService('orm');
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
            journal_ids: [],
            account_ids: [],
            get_filters: true,
            target_move: ['posted'], //['draft', 'posted'],
            selected_partners: [],
        })
        const cf = this._ctxFilters
        if (cf.account_ids.length) this.filterState.account_ids = cf.account_ids
        if (cf.partner_ids.length) this.filterState.selected_partners = cf.partner_ids
        if (cf.target_move) this.filterState.target_move = cf.target_move
        useEffect(() => {
            const loadData = async () => {
                await this.loadData()
            }
            loadData()
        }, () => [this.filters.startDate, this.filters.endDate, this.filterState.selected_partners, this.filterState.account_ids])
    }

    get partner_args() {
        return ['cash']
    }

    get args() {
        return ['cash']
    }

    get currencySymbol() {
        return this.state.currency
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
        const report = 'cyllo_accounting.report_cash_book'
        return [report, report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }

    get xlsxData() {
        const report = 'report.cyllo_accounting.report_cash_book'
        return [report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }
}

CashBookReport.template = "CashBookReport"
registry.category("actions").add("cash_book", CashBookReport);
