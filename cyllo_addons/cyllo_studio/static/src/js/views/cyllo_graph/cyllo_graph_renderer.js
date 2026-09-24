/** @odoo-module */

/**
 * Cyllo Studio Graph Renderer
 *
 * This module extends the default Odoo GraphRenderer to integrate
 * Cyllo Studio functionality. Key features include:
 *
 * 1. Patching the setup method to:
 *    - Trigger a "GRAPH_DETAILS" event on mount.
 *    - Provide relevant graph metadata such as:
 *        - Model name
 *        - Metadata (fields, measures)
 *        - View type and ID
 *        - Environment model instance
 *
 * This allows external components or services to listen to graph details
 * and respond accordingly, enabling dynamic interactions within Cyllo Studio.
 */

import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { onMounted } from "@odoo/owl";

export class CylloGraphRenderer extends GraphRenderer {
  setup() {
    super.setup();
    onMounted(() => {
      this.env.bus.trigger("GRAPH_DETAILS", {
        model: this.props.model.metaData.resModel,
        mode: this.props.model.metaData,
        viewType: this.env.config.viewType,
        viewId: this.env.config.viewId,
        allFields: this.props.model.metaData.fields,
        envModel:this.model,
      });
    });
  }
}
