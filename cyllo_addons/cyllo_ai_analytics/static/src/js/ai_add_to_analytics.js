/** @odoo-module **/
import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AiAddToAnalytics extends Component {
    static props = { chartConfig: { type: Object, optional: true } };

    static template = xml`
        <t t-if="source">
            <button t-if="!state.dashboard" class="btn btn-primary btn-sm cy-ai-add-analytics"
                    t-att-disabled="state.saving" t-on-click="onAdd"
                    title="Save this chart as a dashboard and sheet in Cyllo Analytics">
                <i t-att-class="state.saving ? 'fa fa-spinner fa-spin me-1' : 'ri-add-line me-1'" />
                Add to Analytics
            </button>
            <button t-else="" class="btn btn-secondary btn-sm cy-ai-add-analytics" t-on-click="onOpen">
                <i class="ri-external-link-line me-1" />
                Open dashboard
            </button>
        </t>`;

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ saving: false, dashboard: null });
    }

    /** The chart's data source set by render_chart, or null if it has none. */
    get source() {
        return (this.props.chartConfig && this.props.chartConfig.cyllo_source) || null;
    }

    /** Create the dashboard + sheet in Cyllo Analytics from the chart's source. */
    async onAdd() {
        this.state.saving = true;
        try {
            const title = (this.props.chartConfig.title && this.props.chartConfig.title.text) || "";
            this.state.dashboard = await this.orm.call(
                "dashboard.sheet", "add_chat_chart_to_analytics", [this.source, title]);
            this.notification.add(
                `Dashboard "${this.state.dashboard.name}" added to Cyllo Analytics.`,
                { type: "success" });
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || "Could not add the chart to Analytics.",
                { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    /** Open the created dashboard in Cyllo Analytics. */
    onOpen() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cy_analytic_dashboard",
            target: "current",
            context: { rec_id: this.state.dashboard.dashboard_id },
        });
    }
}

registry.category("cyllo_ai.chart_actions").add("add_to_analytics", AiAddToAnalytics);
