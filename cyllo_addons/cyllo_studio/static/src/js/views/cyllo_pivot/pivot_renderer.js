/** @odoo-module **/

/**
 * CylloPivotRenderer
 *
 * Custom renderer extending Odoo's `PivotRenderer` to provide
 * enhanced pivot view integration in Cyllo Studio.
 *
 * Features:
 * 1. Inherits all rendering logic from Odoo’s base `PivotRenderer`.
 * 2. On mount, broadcasts pivot metadata through the event bus.
 * 3. Exposes key details such as:
 *    - View type and view ID.
 *    - Associated model and fields.
 *    - Active measures and metadata for the pivot view.
 *
 * Purpose:
 * Enables Cyllo Studio to intercept and customize pivot view
 * rendering, making pivot metadata available for other Studio
 * components (e.g., editors, sidebars).
 */
import {
    onMounted,
} from "@odoo/owl";
import {
    PivotRenderer
} from "@web/views/pivot/pivot_renderer";

export class CylloPivotRenderer extends PivotRenderer {
    setup() {
        super.setup();
        onMounted(() => {
            this.env.bus.trigger("PIVOT_DETAILS", {
                viewType: this.env.config.viewType,
                viewId: this.env.config.viewId,
                envModel: this,
                model: this.props.model.metaData.resModel,
                active_fields: this.props.model.metaData.fields,
                measure: this.model.metaData.measures,
                metaData: this.model.metaData,
                activeFields: this.model.metaData.fields,
            });
        });
    }
}
CylloPivotRenderer.template = "cyllo_studio.StudioPivotRenderer"
CylloPivotRenderer.components = {
    ...PivotRenderer.components,
};