/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";
import { useService } from "@web/core/utils/hooks";
import { useRef,onMounted } from "@odoo/owl";

patch(GraphController.prototype, {
    getContext() {
        const { measure, groupBy, mode, modes } = this.model.metaData;
        const context = {
            graph_measure: measure,
            graph_mode: mode,
            graph_modes: modes,
            graph_groupbys: groupBy.map((gb) => gb.spec),
        };
        if (mode !== "pie") {
            context.graph_order = this.model.metaData.order;
            context.graph_stacked = this.model.metaData.stacked;
            if (mode === "line") {
                context.graph_cumulated = this.model.metaData.cumulated;
            }
        }
        return context;
    }
});