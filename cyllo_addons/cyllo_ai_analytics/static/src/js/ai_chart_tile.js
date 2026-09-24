/** @odoo-module **/
/**
 * Renders a sheet's chart inside the cyllo_ai chatbot by reusing the dashboard's
 * OWN chart component (GraphTile), which self-fetches its data from `item`. This
 * gives the exact same chart as the dashboard — same type, colours, formatters —
 * with no rebuild.
 *
 * It registers into cyllo_ai's "cyllo_ai.chat_chart" slot, so ChatResponse can
 * render it without cyllo_ai depending on analytics.
 */
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { GraphTile } from "@cyllo_analytics/js/presentation/components/graph_tile";

export class AiChartTile extends Component {
    static components = { GraphTile };
    static props = {
        item: { type: Object },
        theme: { type: String, optional: true },
        themeColor: { type: [Object, Boolean], optional: true },
        isDarkMode: { type: Boolean, optional: true },
    };
    // Size the chart CARD to the chat panel. GraphTile otherwise falls back to
    // its 440x400 default (defaultProps.style), which overflows the narrow chat
    // and creates an inner scroll. width:100% fits the panel; the fixed height
    // gives GraphTile's flex:1 chart root a definite box to fill.
    get chartStyle() {
        return { width: "100%", height: "360px" };
    }

    static template = xml`
        <div class="cy-ai-chat-chart" style="width:100%;">
            <GraphTile item="props.item"
                       style="chartStyle"
                       theme="props.theme or ''"
                       themeColor="props.themeColor"
                       isDarkMode="props.isDarkMode or false"/>
        </div>`;
}

registry.category("cyllo_ai.chat_chart").add("component", AiChartTile);
