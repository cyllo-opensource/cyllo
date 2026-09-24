/** @odoo-module **/

/**
 * Cyllo Studio Graph Controller Patch
 *
 * This module extends the default Odoo GraphController to integrate
 * Cyllo Studio custom functionality. Key enhancements include:
 *
 * 1. Patching the GraphController's setup method to add:
 *    - RPC service injection for backend communication.
 *    - Action service injection to trigger Odoo actions.
 *    - Mounted hook that ensures the graph view is created if missing.
 *    - Emitting a 'graphDetails' event with view type, model, active fields,
 *      and measure metadata for external listeners.
 *
 * 2. createGraphView method:
 *    - Creates a graph view by sending the view architecture to the backend
 *      via RPC.
 *    - Blocks the UI during the RPC call to prevent user interaction.
 *    - Reloads the studio interface after successfully creating the view.
 *
 * 3. Extends the GraphController components to include the custom Layout component.
 * 4. Sets a custom template: "studio.CylloGraphView".
 *
 * This patch allows seamless creation and integration of graph views in
 * Cyllo Studio while maintaining compatibility with Odoo's standard graph views.
 */
import { patch } from "@web/core/utils/patch";
import { GraphController } from "@web/views/graph/graph_controller";
import { useService } from "@web/core/utils/hooks";
import { useRef, onMounted } from "@odoo/owl";
import { Layout } from "@web/search/layout";

patch(GraphController.prototype, {
    setup() {
        super.setup();
        this.rpc = useService('rpc')
        this.action = useService('action')
        onMounted(async () => {
            if (!this.env.config.viewId) {
                await this.createGraphView()
            }
            this.env.bus.trigger('graphDetails', {
                view_type: this.env.config.viewType,
                model: this.model.env.searchModel.resModel,
                envModel: this,
                active_fields: this.props.fields,
                measure: this.model.metaData.measure,
            });
        })
    },

    async createGraphView() {

        this.env.services.ui.block();
        try {
            await this.rpc("cyllo_studio/graph/add_view", {
                arch: this.env.config.viewArch.outerHTML,
                model: this.props.resModel,
            })
        } finally {
            this.env.services.ui.unblock();
        }
        this.action.doAction("studio_reload");

    }
})

GraphController.components = {
    ...GraphController.components,
    Layout,
}
GraphController.template = "studio.CylloGraphView"
