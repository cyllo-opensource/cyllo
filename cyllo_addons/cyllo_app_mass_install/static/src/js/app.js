/** @odoo-module **/

import {Component} from "@odoo/owl";

/**
 * Apps Component for handling app selection.
 */
export class Apps extends Component {
    static template = "cyllo_app_mass_install.apps";

    /**
     * Handles the selection of an app.
     * Toggles the isSelected state and triggers an event to update selected apps.
     *
     * @param {number} app_id - ID of the selected app.
     */
    select_app(app_id) {
        this.env.bus.trigger("update_selected_apps", {
            app_id: app_id
        });
    }
}
