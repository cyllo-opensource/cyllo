/** @odoo-module */

/**
 *
 * ReportView Component
 *
 * This component provides a frontend interface for fetching and displaying
 * reports from the Odoo backend. It loads report metadata and QWeb templates,
 * and allows users to open reports in a new browser tab.
 *
 * Features:
 * 1. Fetches report data using `jsonrpc` and `orm.call`.
 * 2. Stores report metadata and QWeb code in reactive state.
 * 3. Handles report click events to fetch the corresponding QWeb code and open the report.
 *
 * Dependencies:
 * - Layout, CogMenu, SearchBar components.
 * - Odoo services: rpc, orm, action.
 */
import { registry } from '@web/core/registry';
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";
const { Component, mount } = owl
export class ReportView extends Component {
    setup() {
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.state = useState({
            reportData: {},
            QwebCode: {},
        })
        this.loadData();
    }
    /**
     * Fetches all report metadata from the backend using jsonrpc.
     * Populates `state.reportData`.
     */
    async loadData() {
        this.state.reportData = await jsonrpc('/web/dataset/call_kw/ir.actions.report/get_values', {
            model: 'ir.actions.report',
            method: 'get_values',
            args: [[]],
            kwargs: {},
        });
    }

    /**
     * Handles the click event on a report.
     * Fetches the corresponding QWeb template and opens the report in a new tab.
     *
     * @param {Event} ev - The click event
     * @param {Object} data - The report data object
     */
    async ReportOnClick(ev, data) {
        this.state.QwebCode = await this.orm.call("ir.actions.report", "get_qweb", [data], {});
        const reportUrl = `/my_module/report/${data.id}`;
        window.open(reportUrl, "_blank");
    }
}
ReportView.template = "report_view.report_view"
registry.category("actions").add("report_view", ReportView)
ReportView.components = {
    Layout,
    CogMenu,
    SearchBar
}