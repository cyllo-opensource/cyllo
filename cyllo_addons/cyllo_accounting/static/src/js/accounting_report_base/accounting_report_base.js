/** @odoo-module **/
import { Component, onWillStart, useState, onWillUnmount, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ReportDropdown } from "./reportDropdown";
import { AnnotateDialog } from "./annotate_dialog";
import { download } from "@web/core/network/download";
import { useSaveContext } from "../hooks/useSaveContext";
import { useResize } from "@cyllo_base/js/hooks"
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

const getValueFromLocalStorage = (key) => {
    const value = localStorage.getItem(key);
    if (value !== null) {
        try {
            return JSON.parse(value);
        } catch (e) {
            console.error(`Error parsing JSON for key: ${key}`, e);
            return false;
        }
    } else {
        console.warn(`No value found in localStorage for key: ${key}`);
        return false;
    }
}

const TIMEFRAMES = {
    'month': 'This Month',
    'quarter': 'This Quarter',
    'year': 'This Financial Year',
    'month_l': 'Last Month',
    'quarter_l': 'Last Quarter',
    'year_l': 'Last Financial Year',
    'custom': 'Custom'
}

const REPORTS = [
    "Partner Ledger",
    "General Ledger",
    "Aged Receivable",
    "Aged Payable"
]

export class AccountingReportBase extends Component {
    model = ""
    reportMethod = "get_report"
    defaultDateFilter = 'month'
    pdfReport = true;
    ledgerId = 0
    breadCrumbs = false
    sidebarClass = {
        off: "",
        on: "",
        bodyOn:"",
        bodyOff: "",
    }

    setup() {
        this.env.bus.addEventListener("SIDEBAR_MENU_TOGGLE", ({ detail }) => {
            this.uiState.isSideBarActive = !detail.isSidebarOn
        })

        this.uiState = useState({
            isSideBarActive: true
        })
        this.orm = useService('orm');
        this.action = useService('action');
        this.ui = useService('ui');
        this.dialog = useService("dialog");
        this.company = useService("company");
        this.dialogService = useService("dialog");
        this.financialYear = {
            start_date: "",
            end_date: ""
        }
        this.filters = useState({
            dateFilterValue: this.defaultDateFilter,
            startDate: "",
            endDate: ""
        })
        this._ctxDates = this._readContextDates()
        this._ctxFilters = this._readContextFilters()
        this.searchViewId = false
        this.saveContext = useSaveContext()
        onWillStart(async () => {
            this.searchViewId = await this.orm.call("abstract.financial.report", "get_search_view", [])
        })
        onWillStart(this.setInitialValues)
        for (const report of REPORTS) { // Removes the opened lines if a new report is opened
            if (report !== this.reportName) {
                this.saveContext.removeManually(report)
            }
        }
    }

    get reportName() {
        return this.props.action.display_name || ''
    }

    get timeFrame() {
        return TIMEFRAMES
    }

    get dateFilterValue() {
        return this.timeFrame[this.filters.dateFilterValue]
    }

    /**
     * Groups filter records by their company so a dropdown can render one
     * company header per block. Records whose company_id is not set (analytic
     * accounts shared across companies) are collected under "Unassigned".
     *
     * @param {Array} records search_read result carrying company_id
     * @param {string} key name the grouped records are exposed under
     * @returns {Array} [{ companyName, [key]: records }]
     */
    groupByCompany(records, key) {
        const groups = {};
        for (const record of records || []) {
            const companyName = Array.isArray(record.company_id) ? record.company_id[1] : _t("Unassigned");
            if (!groups[companyName]) {
                groups[companyName] = [];
            }
            groups[companyName].push(record);
        }
        return Object.entries(groups).map(([companyName, grouped]) => ({
            companyName,
            [key]: grouped,
        }));
    }

    get journalsByCompany() {
        return this.groupByCompany(this.state.journals, "journals")
    }

    get analyticsByCompany() {
        return this.groupByCompany(this.state.analytics, "analytics")
    }

    get accountsByCompany() {
        return this.groupByCompany(this.state.accounts, "accounts")
    }

    get filterContext() {
        return {}
    }

    get args() {
        return []
    }

    get pdfData() {
        return ["", "", {}]
    }

    get xlsxData() {
        return ["", {}]
    }

    get comparisonUnit() {
        const dateFilter = this.filters.dateFilterValue || ""
        if (dateFilter.startsWith("year")) {
            return "year"
        }
        if (dateFilter.startsWith("quarter")) {
            return "quarter"
        }
        if (dateFilter.startsWith("month")) {
            return "month"
        }
        return "custom"
    }

    get periodData() {
        const periodCount = this.state.comparison > 1 ? this.state.comparison : 1
        const unit = this.comparisonUnit
        const periods = []
        for (let index = 0; index < periodCount; index++) {
            periods.push(this.getPeriodLabel(unit, index))
        }
        return periods
    }

    getPeriodLabel(unit, index) {
        const startDate = moment(this.filters.startDate)
        const endDate = moment(this.filters.endDate)
        switch (unit) {
            case "year": {
                const startYear = startDate.clone().subtract(index, "years").format("YYYY")
                const endYear = endDate.clone().subtract(index, "years").format("YYYY")
                return `${startYear} - ${endYear}`
            }
            case "quarter": {
                const quarterStart = startDate.clone().subtract(index, "quarters")
                return `[Q${quarterStart.quarter()}] ${quarterStart.format("YYYY")}`
            }
            case "month":
                return startDate.clone().subtract(index, "months").format("MMM YYYY")
            default: {
                // custom: shift by the length of the selected range
                const rangeLength = endDate.diff(startDate, "days") + 1
                const from = startDate.clone().subtract(index * rangeLength, "days").format("YYYY-MM-DD")
                const to = endDate.clone().subtract(index * rangeLength, "days").format("YYYY-MM-DD")
                return `[${from}] - [${to}]`
            }
        }
    }

    async getReport() {
        return await this.orm.call(this.model, this.reportMethod, [...this.args], this.filterContext)
    }

    onSelectTimeFrame(time, force = true) {
        this.filters.dateFilterValue = time
        this.setDate()
        if (force) {
            this.setDefaultComparison()
        }
    }

    applyComparison() {
        if (!this.state.comparisonCopy) {
            return
        }
        this.state.comparison = this.state.comparisonCopy
        this.state.comparisonType = this.comparisonUnit
    }

    setDefaultComparison() {
        // Reset to "no comparison". No-op for reports that do not use it.
        if (!("comparison" in this.state)) {
            return
        }
        this.state.comparison = 1
        this.state.comparisonCopy = 1
        this.state.comparisonType = this.comparisonUnit
    }

    _readContextDates() {
        const ctx = (this.props.action && this.props.action.context) || {}
        const re = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/
        const from = ctx.cyllo_date_from
        const to = ctx.cyllo_date_to
        if (typeof from === "string" && re.test(from) &&
            typeof to === "string" && re.test(to)) {
            return { from, to }
        }
        return null
    }

    _readContextFilters() {
        const ctx = (this.props.action && this.props.action.context) || {}
        const ids = (v) => (typeof v === "string" && /^\d+(,\d+)*$/.test(v))
            ? v.split(",").map(Number) : []
        const tm = (typeof ctx.cyllo_target_move === "string" &&
            /^(posted|draft)(,(posted|draft))*$/.test(ctx.cyllo_target_move))
            ? ctx.cyllo_target_move.split(",") : null
        return {
            partner_ids: ids(ctx.cyllo_partner_ids),
            journal_ids: ids(ctx.cyllo_journal_ids),
            account_ids: ids(ctx.cyllo_account_ids),
            analytic_ids: ids(ctx.cyllo_analytic_ids),
            target_move: tm,
        }
    }

    async setInitialValues() {
        this.financialYear = await this.orm.call("abstract.financial.report", "get_financial_year", [])
        if (this._ctxDates) {
            this.filters.dateFilterValue = 'custom'
            this.filters.startDate = this._ctxDates.from
            this.filters.endDate = this._ctxDates.to
        } else {
            this.setDate()
        }
    }

    openAnnotation(moveLineId, message = "", account) {
        this.dialog.add(AnnotateDialog, {
            title: 'Annotate',
            message: message,
            onConfirm: async (result) => {
                await this.writeAnnotation(moveLineId, result, account)
            }
        });
    }

    async writeAnnotation(moveLineId, value, account) {
        await this.orm.call("account.move.line", "write_annotations", [moveLineId, this.ledgerId, value])
    }

    async removeAnnotation(moveLineId, account) {
        await this.orm.call("account.move.line", "remove_annotations", [moveLineId, this.ledgerId])
    }

    setDate() {
        const [startDate, endDate] = this.getDate()
        this.filters.startDate = startDate
        this.filters.endDate = endDate
    }

    getDate() {
        const { dateFilterValue } = this.filters
        const filter = dateFilterValue.split('_')
        let startDate, endDate
        if (['year', 'year_l'].includes(dateFilterValue)) {
            ({ start_date: startDate, end_date: endDate } = this.financialYear)
            if (dateFilterValue === 'year') {
                return [startDate, endDate]
            } else {
                const currentStartDate = moment(startDate);
                const previousStartDate = moment(currentStartDate).subtract(1, 'year').format('YYYY-MM-DD');
                const currentEndDate = moment(endDate);
                const previousEndDate = moment(currentEndDate).subtract(1, 'year').format('YYYY-MM-DD');
                return [previousStartDate, previousEndDate]
            }
        } else if (dateFilterValue === 'today') {
            let today = new Date()
            today = moment(today).format('YYYY-MM-DD')
            return [today, today]
        } else {
            const momentValue = !Boolean(filter.length > 1) ? moment() : moment().subtract(1, filter[0]);
            startDate = momentValue.startOf(filter[0]).format('YYYY-MM-DD');
            endDate = momentValue.endOf(filter[0]).format('YYYY-MM-DD');
            return [startDate, endDate]
        }
    }

    onDateChange(ev, type) {
        this.filters.dateFilterValue = 'custom'
        const value = ev.target.value
        if (!value) {
            this.dialogService.add(WarningDialog, {
                title: _t("Warning: Missing Date"),
                message: _t("Please select a valid date before proceeding."),
            });
            return;
        }

        this.filters[type] = value;
    }

    printPDF() {
        const [report_name, report_file, data] = this.pdfData
        return this.action.doAction({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name,
            report_file,
            data,
            display_name: this.reportName,
        })
    }

    async printXLSX() {
        const [model, xlsxData] = this.xlsxData
        const data = {
            model,
            data: JSON.stringify(xlsxData),
            output_format: 'xlsx',
            report_name: this.reportName,
        }
        this.ui.block()
        await download({
            url: '/cyllo_xlsx_report',
            data,
            complete: () => this.ui.unblock(),
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        });
        this.ui.unblock()
    }

    onClickBreadCrumbs() {
        window.history.go(-1)
    }

    openGeneralLedger(accountId) {
        return this.action.doAction("cyllo_accounting.action_dynamic_general_ledger", {
            additionalContext: {
                accountId: accountId,
                breadCrumb: this.reportName
            },
        })
    }
}

AccountingReportBase.template = "AccountingReportBase"
AccountingReportBase.components = { Dropdown, DropdownItem, ReportDropdown }
