/** @odoo-module */
import { registry } from "@web/core/registry";
import { activityView } from "@mail/views/web/activity/activity_view";
import { CylloActivityController } from "./cyllo_activity_controller";
import { CylloActivityRenderer } from "@cyllo_studio/js/views/cyllo_activity/cyllo_activity_renderer";

/**
 * CylloActivityView
 *
 * Extends the standard activity view with custom controller and renderer
 */
export const CylloActivityView = {
	...activityView,
	Controller: CylloActivityController,
	Renderer: CylloActivityRenderer,
};

registry.category("views").add("n_activity", activityView);
registry.category("views").add("activity", CylloActivityView, { force: true });