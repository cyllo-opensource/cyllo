/** @odoo-module */
import { registry } from "@web/core/registry";
import { useState, onWillStart, useEffect, onMounted } from "@odoo/owl";
import { AccountingReportBase } from "@cyllo_accounting/js/accounting_report_base/accounting_report_base"
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { Pager } from "@web/core/pager/pager";
import { LinesHeader } from "./components/lines_header"
import {PartnerSelection} from "../components/partnerSelection";

const TIMEFRAMES = {
    'today': 'Today',
    'month_l': 'End of Last Month',
    'quarter_l': 'End of Last Quarter',
    'year_l': 'End of Last Year',
    'custom': 'Custom'
}

export class AgedReceivable extends AccountingReportBase {
    model = 'aged.payable.receivable.report'
    defaultDateFilter = 'today'
    ledgerId = 3
    removeSession = true

    sidebarClass = {
        off: "receivable_menu_off",
        on: "receivable_menu_on",
        bodyOn: "receivable_menu_body_on",
        bodyOff: "receivable_menu_body_off",
        pagerOn: "receivable_menu_pager_on",
        pagerOff: "receivable_menu_pager_off",
    }

    setup() {
        super.setup();
        this.state = useState({
            data: {},
            grandTotal: {},
            partnerIds: [],
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
        if (this._ctxFilters.partner_ids.length) {
            this.filters.selected_partners = this._ctxFilters.partner_ids
        }

        useEffect(()=> {
            const loadData = async () => {
                 await this.loadData()
            }
            loadData()
        },()=> [this.filters.selected_partners, this.filters.endDate])
        onMounted(() => {
            const openAccounts = this.saveContext.getKeyValue(this.reportName)
            if (openAccounts?.length && !this.state.openAccounts.length) {
                this.state.openAccounts = openAccounts
            }
        })
    }

    get filterContext() {
        /**
         * Retrieves the context used for filtering data in the report.
         *
         * @returns {object} - The filter context containing date, selected partners, and active company IDs.
         */
        return {date: this.filters.endDate, partners: this.filters.selected_partners, company_ids: this.company.activeCompanyIds}
    }

    get args() {
        /**
         * Retrieves the arguments used for fetching data from the backend.
         *
         * @returns {Array} - An array containing the account type, offset, and limit.
         */
        return ['asset_receivable', this.pager.offset, this.pager.limit]
    }

    get timeFrame() {
        /**
         * Retrieves the time frame options available for the report.
         *
         * @returns {object} - An object containing the available time frame options.
         */
        return TIMEFRAMES
    }

    async loadData() {
        /**
         * Loads data for the report asynchronously.
         * Retrieves partner totals, grand total, and updates pagination.
         * Update partnerIds where no partners are selected.
         */
         if(!this.filters.endDate){
            return;
         }
        const data = await this.getReport()
        this.state.data = data.partner_totals
        this.state.grandTotal = data.grand_total
        this.pager.total = data.partners.length ? data.partners.length : 1
        if (!this.filters.selected_partners.length) {
            this.state.partnerIds = data.partners
        }
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

    async onPagerChanged({offset, limit}, hasNavigated){
        /**
         * Handles the pager change event and loads data accordingly.
         *
         * @param {object} param0 - Object containing the new offset and limit.
         * @param {boolean} hasNavigated - Indicates whether the change is a navigation event.
         */
        this.pager.offset = offset
        this.pager.limit = limit
        await this.loadData()
    }

    toggleUnfold() {
        /**
         * Toggles the folded state of the report lines.
         * Trigger bus to toggle fold report lines
         */
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
        /**
         * Retrieves the data required for generating a PDF report.
         *
         * @returns {Array} - An array containing the report details and filter context.
         */
        const report = 'cyllo_accounting.aged_receivable'
        return [report, report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName }]
    }

    get xlsxData() {
        /**
         * Retrieves the data required for generating an Excel report.
         *
         * @returns {Array} - An array containing the report details and filter context.
         */
        const report = 'report.cyllo_accounting.aged_receivable'
        return [report, {...this.filterContext, account_type: this.args[0], report_name: this.reportName}]
    }

  async writeAnnotation(moveLineId, value, partnerId) {
   /**
     * Writes an annotation for a specific move line and partner.
     *
     * @param {number} moveLineId - The ID of the move line.
     * @param {string} value - The annotation value.
     * @param {number} partnerId - The ID of the partner.
     */
    await super.writeAnnotation(...arguments);
    const moveLines = this.state.data.find(item => item.partner_id === partnerId)?.move_lines;
    const moveLine = moveLines.find(line => line.id === moveLineId)
    moveLine.annotations = {[this.ledgerId]: value}
  }

  async removeAnnotation(moveLineId, partnerId) {
    /**
     * Removes an annotation for a specific move line and partner.
     *
     * @param {number} moveLineId - The ID of the move line.
     * @param {number} partnerId - The ID of the partner.
     */
    await super.removeAnnotation(...arguments)
    const moveLines = this.state.data.find(item => item.partner_id === partnerId)?.move_lines;
    const moveLine = moveLines.find(line => line.id === moveLineId)
    moveLine.annotations = {}
  }

  onClickPartners() {
        this.dialog.add(PartnerSelection, {
            selectedPartners: this.filters.selected_partners,
            domain: [['id', 'in', this.state.partnerIds]],
            addPartner: this.addPartner.bind(this)
        })
    }
    addPartner(partnerIds) {
        this.filters.selected_partners = partnerIds
    }

}
AgedReceivable.template = 'AgedReceivable';
AgedReceivable.components = {
    ...AccountingReportBase.components,
    MultiRecordSelector,
    LinesHeader,
    Pager
}

registry.category("actions").add("age_r", AgedReceivable);