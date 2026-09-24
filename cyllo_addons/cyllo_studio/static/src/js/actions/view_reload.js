/** @odoo-module **/
import { registry } from "@web/core/registry";
/**
 * Reloads the current view in Odoo.
 *
 * This function triggers a cache clear event and performs a soft reload
 * of the current action. It can be used to refresh the UI after changes
 * to data, views, or configurations.
 *
 * @param {Object} env - The Owl component environment, containing bus and services.
 * @param {Object} action - The current action object (not used directly in this implementation).
 */
export async function viewReload(env, action) {
     env.bus.trigger("CLEAR-CACHES");
     env.services.action.doAction('soft_reload')

}

registry.category("actions").add("view_reload", viewReload);
