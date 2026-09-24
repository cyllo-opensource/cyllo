/** @odoo-module **/
import { registry } from "@web/core/registry";

async function studioReload(env, action) {
    env.bus.trigger("CLEAR-CACHES");
    const controller = env.services.action.currentController;
    if (controller) {
        // Prevent action_service from restoring old model config (which has stale
        // activeFields from before the arch change). Without this, ListController
        // reuses props.state.modelState.config → model fetches without the new
        // field → record.data lacks it → cell is invisible despite header showing.
        const savedGetLocalState = controller.getLocalState;
        controller.getLocalState = null;
        controller.exportedState = null;
        try {
            await env.services.action.doAction('soft_reload');
        } finally {
            controller.getLocalState = savedGetLocalState;
        }
    } else {
        env.services.action.doAction('soft_reload');
    }
}

registry.category("actions").add("studio_reload", studioReload);
