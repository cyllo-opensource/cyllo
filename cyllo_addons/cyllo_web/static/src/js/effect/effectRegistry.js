/** @odoo-module **/

import { registry } from "@web/core/registry";
import { NotificationPanel } from "./effect/effects";

const effectRegistry = registry.category("effects");

function notificationPanelEffect(env, params = {}) {
    const title = params.title || "Notification";
    const message = params.message || "A notification occurred.";
    const description = params.description;
    const type = params.notificationType || "error";
    const time = params.time || 3000;
    const animation = params.animation || true;


    if (env.services.user.showEffect) {
        return {
            Component: NotificationPanel,
            props: { title, message, description, type, time, animation },
        };
    }
    env.services.notification.add(message, { type, title });
}

effectRegistry.add("notification_panel", notificationPanelEffect);

//Usage
/**
 * this.env.services.effect.add({
 *             title: "Flow validation failed",
 *             message: "Unable to save the record.",
 *             description: "",
 *             type: "notification_panel",
 *             notificationType: "error",
 *             time:1000
 *             animation:false,
 *         });
 */



