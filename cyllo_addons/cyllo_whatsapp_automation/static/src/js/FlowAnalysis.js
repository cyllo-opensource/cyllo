/**@odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, useRef } from  "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";

/**
 * FlowAnalysis Component
 *
 * This component is used for analyzing WhatsApp flows. It fetches flow data,
 * displays user responses, and provides features for downloading reports
 * in Excel and PDF formats.
 */
class FlowAnalysis extends Component {
    /**
     * Setup lifecycle method to initialize the component.
     */
    async setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.root = useRef("root");
        this.state = useState({
            data: {},
            contentViews: {},
        });
        onWillStart(async () => {
            await this.orm.call("whatsapp.flows", "send_data", [this.props.action.context['active_id']], {}).then((data) => {
                this.state.data = data;
            });
            this.state.data.screens.forEach(screen => {
                screen.contents.forEach(content => {
                    this.state.contentViews[content.id] = 'list';
                });
            });
        });
    }

    /**
     * Download Excel report for the current flow analysis.
     */
    async download_excel_report(){
        var self = this
        var data = this.state.data
        var datas = {
            'data':self.state.data,
        }
         var action = {
            'data': {
               'model': 'whatsapp.flows',
                'data': JSON.stringify(datas),
                'output_format': 'xlsx',
                'report_action': self.props.action.xml_id,
                'report_name': 'Whatsapp Flows Report',
            }
         }
         BlockUI;
         await download({
            url: '/flow_report',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => self.call('crash_manager', 'rpc_error', error),
         });
    }

    /**
     * Download PDF report for the current flow analysis.
     */
    download_pdf_report(){
        var self = this;
        var action_title = self.props.action.display_name;
        return self.action.doAction({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: 'cyllo_whatsapp_automation.flow_analysis_report_template',
            report_file: 'cyllo_whatsapp_automation.flow_analysis_report_template',
            data: { data: self.state.data },
            display_name: action_title
        });
    }

    /**
     * Show responses for a specific content item.
     * @param {number} content_id - The ID of the content item.
     */
    show_response(content_id) {
        $(this.root.el.querySelector(`#right-button-${content_id}`)).addClass('d-none');
        $(this.root.el.querySelector(`#down-button-${content_id}`)).removeClass('d-none');
        $(this.root.el.querySelector(`#view-container-${content_id}`)).removeClass('d-none');
        if (this.state.contentViews[content_id] === 'list') {
            $(this.root.el.querySelector(`#input_table-${content_id}`)).removeClass('d-none');
        } else {
            $(this.root.el.querySelector(`#input_table-${content_id}`)).addClass('d-none');
        }
        if (this.state.contentViews[content_id] === 'graph') {
            $(this.root.el.querySelector(`#input_graph-${content_id}`)).removeClass('d-none');
        } else {
            $(this.root.el.querySelector(`#input_graph-${content_id}`)).addClass('d-none');
        }
    }

    /**
     * Hide responses for a specific content item.
     * @param {number} content_id - The ID of the content item.
     */
    hide_response(content_id) {
        $(this.root.el.querySelector(`#right-button-${content_id}`)).removeClass('d-none');
        $(this.root.el.querySelector(`#down-button-${content_id}`)).addClass('d-none');
        $(this.root.el.querySelector(`#view-container-${content_id}`)).addClass('d-none');
        if (this.state.contentViews[content_id] === 'list') {
            $(this.root.el.querySelector(`#input_table-${content_id}`)).addClass('d-none');
        }
        if (this.state.contentViews[content_id] === 'graph') {
            $(this.root.el.querySelector(`#input_graph-${content_id}`)).addClass('d-none');
        }
    }

    /**
     * Open the partner form view for a specific partner.
     * @param {number} partner_id - The ID of the partner.
     */
    open_partner(partner_id) {
        this.action.doAction({
            name: "Partner",
            type: "ir.actions.act_window",
            res_model: "res.partner",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            res_id: partner_id,
        });
    }

    /**
     * Toggle the view mode to "Graph" for a specific content item.
     * @param {number} content_id - The ID of the content item.
     */
    toggleGraphView(content_id) {
        this.state.contentViews[content_id] = 'graph';
        $(this.root.el.querySelector(`#input_table-${content_id}`)).addClass('d-none');
        google.charts.load('current', { 'packages': ['corechart'] });
        const drawChart = (content, dataArray) => {
            const data = google.visualization.arrayToDataTable(dataArray);
            const options = {
                title: content.label,
            };
            const chartElement = document.getElementById(`input_graph-${content_id}`);
            const chart = new google.visualization.PieChart(chartElement);
            chart.draw(data, options);
        };
        google.charts.setOnLoadCallback(() => {
            this.state.data.screens.forEach((screen) => {
                screen.contents.forEach((content) => {
                    if (content.id === content_id) {
                        const groupedResponses = {};
                        content.user_responses.forEach((response) => {
                            const userInput = response.user_input;
                            const partner = response.partner;
                            if (!groupedResponses[userInput]) {
                                groupedResponses[userInput] = { count: 0, partners: [] };
                            }
                            groupedResponses[userInput].count++;
                            groupedResponses[userInput].partners.push(partner);
                        });
                        const dataArray = [['Options', 'Count']];
                        for (const [userInput, details] of Object.entries(groupedResponses)) {
                            const partnersList = details.partners.join(', ');
                            const label = `${userInput} (${partnersList})`;
                            dataArray.push([label, details.count]);
                        }
                        drawChart(content, dataArray);
                        $(this.root.el.querySelector(`#input_graph-${content_id}`)).removeClass('d-none');
                    }
                });
            });
        });
    }

    /**
     * Toggle the view mode to "List" for a specific content item.
     * @param {number} content_id - The ID of the content item.
     */
    toggleListView(content_id) {
        this.state.contentViews[content_id] = 'list';
        $(this.root.el.querySelector(`#input_table-${content_id}`)).removeClass('d-none');
        $(this.root.el.querySelector(`#input_graph-${content_id}`)).addClass('d-none');
    }
}
/**
 * Register the FlowAnalysis component as an action in the registry.
 */
FlowAnalysis.template = "cyllo_whatsapp_automation.FlowAnalysis";
registry.category("actions").add("flow_analysis_tag", FlowAnalysis);
