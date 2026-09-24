/** @odoo-module */
/**
 * Cyllo Studio Graph View
 *
 * This module customizes the default Odoo Graph View by integrating
 * the CylloGraphRenderer. Key points:
 *
 * 1. Extends the standard `graphView` to use `CylloGraphRenderer`.
 * 2. Registers the customized graph view in the Odoo view registry.
 * 3. Forces the registration to override the default graph view behavior.
 *
 * This enables Cyllo Studio-specific features such as dynamic metadata
 * broadcasting and enhanced graph interactions.
 */
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { CylloGraphRenderer } from "./cyllo_graph_renderer";

export const CylloGraphView = {
  ...graphView,
  Renderer: CylloGraphRenderer,
};

registry.category("views").add("graph", CylloGraphView, { force: true });
