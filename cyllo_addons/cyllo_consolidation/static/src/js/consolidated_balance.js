/** @odoo-module **/
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class ConsolidatedBalance extends owl.Component {
    async setup() {
        super.setup(...arguments);
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.journal = useRef('journal');
        this.group = useRef('group');
        this.comparison = useRef('comparison');
        this.filter_root = useRef('filter');
        this.state = useState({
            data: null,
            journal: [],
            comparison: [],
            selected_group_name: [],
            filter: null,
            hideZero: true
        });
        this.filter = useState({
            selected_journal: [],
            selected_group: [],
            selected_comparison: [],
        });
        this.active_id = this.props.action.context.active_id
        this.load_data();
    }
    async load_data() {
        this.state.filter = await this.orm.call("consolidation.period", "get_filter", [this.active_id]);
        this.state.data = await this.orm.call("consolidation.period", "view_report", [this.active_id,this.filter]);
    }
    async applyFilter(ev){
        this.filter_root.el.querySelector('.comparison_filter').classList.add('d-none')
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter');
            let index = this.state.journal.indexOf(ev.target.textContent);
            this.state.journal.splice(index, 1);
            index = this.filter.selected_journal.indexOf(parseInt(ev.target.getAttribute('value')));
            this.filter.selected_journal.splice(index, 1);
        } else {
            ev.target.classList.add('selected-filter');
            this.state.journal.push(ev.target.textContent)
            this.filter.selected_journal.push(parseInt(ev.target.getAttribute('value')))
        }
        this.state.data = await this.orm.call("consolidation.period", "view_report", [this.active_id,this.filter]);
        if (this.filter.selected_journal[0] == null){
            this.filter_root.el.querySelector('.comparison_filter').classList.remove('d-none')
        }
        // Update the innerHTML of the code target element with the result value
        this.journal.el.querySelector('.code').innerHTML = this.state.journal;
    }
    async applyGroupFilter(ev){
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter');
            this.filter.selected_group.pop([ev.target.getAttribute('value')])
            this.state.selected_group_name.pop([ev.target.textContent])
        } else {
            ev.target.classList.add('selected-filter');
            this.filter.selected_group.push(ev.target.getAttribute('value'))
            this.state.selected_group_name.push([ev.target.textContent])
        }
        this.state.data = await this.orm.call("consolidation.period", "view_report", [this.active_id,this.filter]);
        this.group.el.querySelector('.code').innerHTML = this.state.selected_group_name.join(",");
    }
    async applyComparison(ev){
        this.filter_root.el.querySelector('.journals_filter').classList.add('d-none')
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter');
            let index = this.state.comparison.indexOf(ev.target.textContent);
            this.state.comparison.splice(index, 1);
            index = this.filter.selected_comparison.indexOf(parseInt(ev.target.getAttribute('value')));
            this.filter.selected_comparison.splice(index, 1);
        } else {
            ev.target.classList.add('selected-filter');
            this.state.comparison.push(ev.target.textContent)
            this.filter.selected_comparison.push(parseInt(ev.target.getAttribute('value')))
        }
        this.state.data = await this.orm.call("consolidation.period", "view_report", [this.active_id,this.filter]);
        if (this.filter.selected_comparison[0] == null){
            this.filter_root.el.querySelector('.journals_filter').classList.remove('d-none')
        }
        // Update the innerHTML of the code target element with the result value
        this.comparison.el.querySelector('.code').innerHTML = this.state.comparison;
    }
    async unfoldAll(ev) {
        /**
         * Unfolds all items in the table body if the event target does not have the 'selected-filter' class,
         * or folds all items if the event target has the 'selected-filter' class.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        if (!ev.target.classList.contains("selected-filter")) {
            for (var length = 0; length < this.tbody.el?.children.length; length++) {
                $(this.tbody.el.children[length])[0].classList.add('show')
            }
            ev.target.classList.add("selected-filter");
        } else {
            for (var length = 0; length < this.tbody.el?.children.length; length++) {
                $(this.tbody.el.children[length])[0].classList.remove('show')
            }
            ev.target.classList.remove("selected-filter");
        }
    }
    async hideAtZero(ev){
    /**
     * Asynchronously toggles the visibility of elements with the class 'hide-at-zero'.
     * Elements with the 'hide-at-zero' class will have the 'd-none' class toggled.
     * @returns {Promise<void>} A Promise that resolves when the operation is complete.
     */
     this.state.hideZero = !this.state.hideZero
     ev.target.classList.toggle("selected-filter");

    }
    async print_pdf(ev) {
        /**
        * Print PDF Method
        * This method is triggered when the "Print PDF" button is clicked.
        * It retrieves the report data and performs an action to generate and download a PDF report.
        */
        ev.preventDefault();
        return this.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'cyllo_consolidation.consolidated_balance',
            'report_file': 'cyllo_consolidation.consolidated_balance',
            'data': {
                'data': this.state,
                'report_name': this.props.action.display_name
            },
            'display_name': this.props.action.display_name,
        });
    }
    async print_xlsx(ev) {
        /**
         * Generates and downloads an XLSX report based on the profit and loss data.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        var action = {
            'data': {
                'model': 'consolidation.period',
                'options': JSON.stringify(this.state),
                'data': JSON.stringify(this.state),
                'output_format': 'xlsx',
                'report_name': this.props.action.display_name,
            },
        };
        BlockUI;
        await download({
            url: '/xlsx_reports',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        });
    }
}
ConsolidatedBalance.template = 'con_bal_template';
actionRegistry.add("con_bal", ConsolidatedBalance);