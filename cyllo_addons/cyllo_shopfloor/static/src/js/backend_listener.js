/** @odoo-module **/

import { registry } from "@web/core/registry";

export const shopFloorBackendListener = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        bus_service.addChannel("shopfloor_channel");

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { type, payload } of notifications) {
                if (type === "workorder_updated" && payload.source === 'shopfloor') {
                    if (!document.querySelector('.o_shopfloor_screen')) {
                        notification.add(
                            "An operator just updated a work order on the Shop Floor.",
                            {
                                title: "Shop Floor Activity",
                                type: "info",
                                sticky: false,
                            }
                        );
                    }
                }
            }
        });
    }
};
registry.category("services").add("shopfloor_backend_listener", shopFloorBackendListener);
