/** @odoo-module **/
import {useState, onWillStart, useEffect} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {AccountingReportBase} from "../accounting_report_base/accounting_report_base";

const REPORT_TYPES = {
    'generic': 'Generic Tax Report',
    'account': 'Group By : Account > Tax',
    'tax': 'Group By : Tax > Account',
}

export class TaxReport extends AccountingReportBase {
    model = "tax.report"
    ledgerId = 10;
    sidebarClass = {
        off: "",
        on: "",
        bodyOn:"balance_body_on",
        bodyOff: "balance_body_off",
    }

    setup() {
        super.setup()
        this.filters = useState({
            ...this.filters,
            options: ['posted'],
            report_type: "generic",
        })

        this.state = useState({
            comparison: 1, //defaults to 0
            comparisonCopy: 1,
            comparisonType: "month", //year or month
            data: [],
            draft: false,
        })

        useEffect(
            () => {
                this.loadData()
            },
            () => [this.state.comparison, this.state.comparisonType, this.filters.dateFilterValue, this.filters.report_type, this.filters.options, this.filters.startDate, this.filters.endDate]
        );

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
        const {activeCompanyIds} = this.company
        return {company: activeCompanyIds, ...this.filters}
    }

    get args() {
        const {comparison, comparisonType} = this.state
        return [comparison, comparisonType]
    }

    get pdfData() {
        const data = this.filterContext
        const period_data = this.periodData
        const report_name = REPORT_TYPES[data['report_type']]
        return ["cyllo_accounting.tax_report", "cyllo_accounting.tax_report", {
            report_name,
            period_data,
            args: this.args,
            filters: {...data}
        }];
    }

    get xlsxData() {
        const data = this.filterContext
        const period_data = this.periodData
        const report_name = REPORT_TYPES[data['report_type']]
        return ["report.cyllo_accounting.tax_report", {
            report_name,
            period_data,
            args: this.args,
            filters: {...data}
        }]
    }

    async loadData() {
        const {startDate, endDate} = this.filters
        if (!startDate || !endDate) return;
        const {report_data} = await this.getReport()
        this.state.data = report_data;
    }

    get getTableData() {
        return this.state.data || []
    }

    applyComparisonPeriod(period) {
        this.onSelectTimeFrame(period, false)
        const {comparisonCopy} = this.state
        this.state.comparisonType = period
        this.state.comparison = comparisonCopy
    }

    onChangeReportType(type) {
        if (type === this.filters.report_type) return
        this.state.data = [];
        this.filters.report_type = type;
    }

    get reportTypes() {
        return REPORT_TYPES
    }

    toggleDraftEntries(value) {
        this.filters.options = value ? ['posted', 'draft'] : ['posted']
        this.state.draft = value
    }

    async writeAnnotation(taxID, value, account) {
        await this.orm.call("account.tax", "write_annotations", [taxID, this.ledgerId, value]);
        this.updateAnnotations(taxID, value);
    }

    async removeAnnotation(taxID, account) {
        await this.orm.call("account.tax", "remove_annotations", [taxID, this.ledgerId]);
        this.updateAnnotations(taxID, null);
    }

    updateAnnotations(targetTaxId, value) {
        const updateRecord = (record) => {
            if (record.tax_id === targetTaxId) {
                record.annotations = value ? {[this.ledgerId]: value} : null;
                return true; // Return true to break out of the loop
            }
            return false;
        };

        if (this.filters.report_type === 'generic') {
            for (const obj of this.state.data) {
                const found = obj.values.some(updateRecord);
                if (found) break;
            }
        } else if (this.filters.report_type === 'account') {
            for (const obj of this.state.data) {
                for (const account of obj.data) {
                    account.values.some(updateRecord);
                }
            }
        } else if (this.filters.report_type === 'tax') {
            for (const obj of this.state.data) {
                const found = obj.data.some(updateRecord);
                if (found) break;
            }
        }
    }

    viewJournalItems(tax) {
        const taxIds = [tax.tax_id];
        if (tax.children_tax_ids && tax.children_tax_ids.length > 0) {
            taxIds.push(...tax.children_tax_ids);
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move.line',
            name: "Journal Items",
            views: [[false, "list"]],
                   domain: [
                "|",
                ["tax_ids", "in", [tax.tax_id]],
                ["tax_line_id", "in", taxIds]
            ],
            target: "current",
            context: {
                group_by: ["account_id"],
                search_default_date_between: 1,
                tax_ids: [tax.tax_id],
                search_default_tax_ids_in: 1,
                date_from: this.filters.startDate,
                date_to: this.filters.endDate,
                search_default_posted: this.filters.options.length === 1
            },
        });
    }
}

TaxReport.template = "TaxReport"
registry.category("actions").add("tax_r", TaxReport);

