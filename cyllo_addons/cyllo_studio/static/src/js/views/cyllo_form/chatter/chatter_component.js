/** @odoo-module **/

/**
 * ChatterComponent
 *
 * This component provides Studio functionality to add or remove
 * the Chatter section in a form view.
 *
 * Props:
 *  - model: string, the model technical name
 *  - viewId: number, the current form view ID
 *  - path: string (default "/form"), the xpath of the Chatter in the view
 *
 * Services:
 *  - rpc: to call server-side methods for adding/removing Chatter
 *  - action: to trigger client-side actions (e.g., reload view)
 *  - ui: used to block/unblock the UI while processing
 *
 * Methods:
 *  - onClick(): triggers the add/remove chatter RPC call and reloads the view
 */
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

export class ChatterComponent extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
    }

    get showPlaceholder() {
        // Prevent adding chatter to specific models that don't support it
        const unsupportedModels = ['mail.activity.type', 'mail.activity.plan'];
        if (unsupportedModels.includes(this.props.model)) {
            return false;
        }
        const h = this.props.hasChatter;
        return h === false || h === 'false' || h === undefined || h === null;
    }

    /**
     * Handles click to add or remove Chatter
     * Calls the server RPC and reloads the form view
     */
    async onClick() {
        this.env.services.ui.block();
        try {
            const position = "inside"
            await this.rpc("cyllo_studio/add_remove/chatter", {
                model: this.props.model,
                view_id: this.props.viewId,
                path: this.props.path,
                view_type: "form",
                position
            })
        } finally {
            this.env.services.ui.unblock();
        }
        this.action.doAction('studio_reload')
    }
}
ChatterComponent.template = "cyllo_studio.ChatterComponent";
ChatterComponent.defaultProps = {
    path: "/form",
}
