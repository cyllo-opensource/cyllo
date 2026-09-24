/** @odoo-module **/
import {useService} from "@web/core/utils/hooks";
import {Component, useState} from "@odoo/owl";

/**
 * SelectedAppDetails component to display details of a selected app.
 * @extends Component
 */
export class SelectedAppDetails extends Component {
    static template = "cyllo_app_mass_install.selected_app_details";

    /**
     * Sets up the component's state and services.
     */
    async setup() {
        super.setup(...arguments);
        this.state = useState({
            selectedApp: null,
            loading: false,
        });
        this.ormService = useService("orm");
    }

    /**
     * Displays details of the selected app.
     * @param {Object} appDetails - Details of the selected app.
     */
    showDetails(appDetails) {
        this.state.selectedApp = appDetails;
    }

    unlinkApps(app) {
        this.env.delete_app(app);
    }

    /**
     * Installs the selected apps.
     * @param {Array} apps_to_install - Array of app IDs to be installed.
     */
    async installApps(apps_to_install) {
        try {
            this.env.skip(apps_to_install);
        } catch (error) {
        }
    }
}
SelectedAppDetails.props = {
    ...Component.props,
    SelectedAppsCount: {
        type: Object,
        optional: true
    },
    AppsToInstall: {
        type: Array,
        optional: true
    }
}
