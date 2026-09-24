/**@odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from  "@odoo/owl";

/**
 * FLowPreview Component
 *
 * This component displays a preview of a flow in the Odoo WhatsApp automation module.
 * The URL for the preview is passed as a parameter in the action.
 */
class FLowPreview extends Component {
    /**
     * Setup lifecycle method to initialize the component.
     * It retrieves the preview URL from the action's parameters.
     */
    setup() {
        this.preview_url = this.props.action.params.url
    }
}
/**
 * Register the FLowPreview component as an action in the registry.
 */
FLowPreview.template = "cyllo_whatsapp_automation.FLowPreview";
registry.category("actions").add("flow_preview_tag", FLowPreview);
