/** @odoo-module */
import { registry } from "@web/core/registry";
import { useState, useEffect, onMounted } from "@odoo/owl";
import { AccountingReportBase } from "@cyllo_accounting/js/accounting_report_base/accounting_report_base"
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { LinesHeaderPartnerLedger } from "./components/lines_header"
import { Pager } from "@web/core/pager/pager";
import { PartnerSelection } from "../components/partnerSelection";

export class PartnerLedger extends AccountingReportBase {
    model = 'partner.ledger.report'
    ledgerId = 2
    removeSession = true
    setup() {
        super.setup(...arguments);
        this.action = useService('action');
        this.state = useState({
            data: null,
            total: null,
            filtered_partner: null,
            filters: null,
            partner_ids: [],
            account_type: [],
            parent_state: null,
            isFolded: true,
            openAccounts: []
        });

        this.pager = useState({
            total: 0,
            limit: 50,
            offset: 0,
        })

        this.filters = useState({
            ...this.filters,
            selected_partners: [],
        })
        // Seed partner filter requested by a chatbot deep-link.
        if (this._ctxFilters.partner_ids.length) {
            this.filters.selected_partners = this._ctxFilters.partner_ids
        }
        useEffect(()=> {
            const loadData = async () => {
                 await this.loadData()
            }
            loadData()
        },()=> [this.filters.startDate, this.filters.endDate,this.filters.dateFilterValue,this.filters.selected_partners,this.state.account_type, this.state.parent_state])
        onMounted(() => {
            const openAccounts = this.saveContext.getKeyValue(this.reportName)
            if (openAccounts?.length && !this.state.openAccounts.length) {
                this.state.openAccounts = openAccounts
            }
        })
    }
    get filterContext() {
        return {startDate: this.filters.startDate,endDate:this.filters.endDate, partner_id: this.filters.selected_partners,account_type:this.state.account_type,parent_state: this.state.parent_state,company_id:this.company.activeCompanyIds}
    }

    toggleDraft() {
        this.state.parent_state = this.state.parent_state ? null : 'draft';
    }

    async saveSession() {
        this.removeSession = false
        await this.saveContext.saveToSession(this.reportName, this.state.openAccounts, true)
    }
    addPartnerToAccounts(partnerId, click) {
        if (click) {
            this.state.openAccounts.push(partnerId)
        } else {
            const index = this.state.openAccounts.indexOf(partnerId);
            if (index !== -1) {
                this.state.openAccounts.splice(index, 1); // Remove 1 item at index
            }
        }
    }

    async loadData() {
            /**
             * Loads the data for the partner ledger report.
             */
                if (!this.filters.startDate || !this.filters.endDate) return;
                const [data, all_partner_ids] = await this.getReport()
                this.state.data = data
                this.pager.total = all_partner_ids.length ? all_partner_ids.length : 1
    }

    get args() {
        return [this.pager.offset, this.pager.limit]
    }

     async onPagerChanged({offset, limit}, hasNavigated){
        this.pager.offset = offset
        this.pager.limit = limit
        await this.loadData()
    }

    toggleUnfold() {
        const {isFolded} = this.state
        if (isFolded) {
            this.env.bus.trigger('UnFoldAll')
            this.state.isFolded = false
        } else {
            this.env.bus.trigger('FoldAll')
            this.state.isFolded = true
        }
    }

    get pdfData() {
        const report = 'cyllo_accounting.partner_ledger'
        return [report, report, {...this.filterContext, report_name: this.reportName }]
    }
    get xlsxData() {
        const report = 'report.cyllo_accounting.partner_ledger'
        return [report, {...this.filterContext, report_name: this.reportName }]
    }


    async AccountType(dataValue){
        const { account_type } = this.state;
        const isAccountTypeIncluded = account_type.includes(dataValue);
        if (isAccountTypeIncluded) {
            this.state.account_type = account_type.filter(type => type !== dataValue); // Direct assignment, Owl does not have setState
        } else {
            // Assign it to this.state.account_type
            this.state.account_type = [...account_type, dataValue]; // Direct assignment, Owl does not have setState
        }
    }

    async writeAnnotation(moveLineId, value, account) {
        await super.writeAnnotation(...arguments);
        const moveLine = this.state.data.partner_totals[account].move_lines.find(item => item.id === moveLineId)
        moveLine.annotations = {[this.ledgerId]: value}
    }
    async removeAnnotation(moveLineId, account) {
        await super.removeAnnotation(...arguments)
        const moveLine = this.state.data.partner_totals[account].move_lines.find(item => item.id === moveLineId)
        moveLine.annotations = {}
    }
    get records() {
        return this.state.data.partner_totals
    }
    async onClickPartners() {
        // Load the (period-bounded) partner list lazily, only when the picker is
        // opened, so it never slows down the initial report load.
        this.state.partner_ids = await this.orm.call(this.model, 'get_partner',
            [this.filters.startDate, this.filters.endDate, this.company.activeCompanyIds])
        this.dialog.add(PartnerSelection, {
            selectedPartners: this.filters.selected_partners,
            domain: [['id', 'in', this.state.partner_ids]],
            addPartner: this.addPartner.bind(this)
        })
    }
    addPartner(partnerIds) {
        this.filters.selected_partners = partnerIds
    }
}


PartnerLedger.template = 'PartnerLedger';
PartnerLedger.components = {
    ...AccountingReportBase.components,
    LinesHeaderPartnerLedger,
        MultiRecordSelector,
        Pager
}
registry.category("actions").add("p_l", PartnerLedger);

