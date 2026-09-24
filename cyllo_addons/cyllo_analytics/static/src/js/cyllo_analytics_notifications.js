/** @odoo-module **/

import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

/**
 * Global service to handle analytics alerts and real-time graph refreshes.
 */
export const analyticsNotificationService = {
    dependencies: ["bus_service", "notification", "action"],
    start(env, { bus_service, notification, action }) {
        // Inject premium styles for notifications
        const style = document.createElement('style');
        style.textContent = `
            .cyllo-dash-link {
                transition: all 0.2s ease-in-out;
                opacity: 0.85;
            }
            .cyllo-dash-link:hover {
                color: #059669 !important;
                opacity: 1;
                text-decoration: none !important;
            }
            .cyllo-dash-link i {
                transition: transform 0.2s ease-in-out;
            }
            .cyllo-dash-link:hover i {
                transform: translateX(4px);
            }
            .cyllo-alert-icon-bg {
                background: rgba(16, 185, 129, 0.12) !important;
                border-radius: 8px;
                padding: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .cyllo_alert_notify {
                border-left: 4px solid #10B981 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            }
        `;
        document.head.appendChild(style);

        // Listen for alert notifications
        bus_service.subscribe("cyllo_analytics_alert", (payload) => {
            const dashboardAction = "cyllo_analytics.cyllo_dashboard_action";
            const message = markup(`
                <div class="d-flex flex-column gap-1 py-1">
                    <div style="font-size: 13px; color: #4B5563; line-height: 1.4;">
                        ${payload.message}
                    </div>
                    <a href="/web#action=${dashboardAction}&active_id=${payload.id}" 
                       class="cyllo-dash-link mt-1 fw-bold d-flex align-items-center" 
                       style="color: #10B981; cursor: pointer; font-size: 12px; text-decoration: none;">
                        Go to Dashboard
                        <i class="ri-arrow-right-s-line ms-1" style="font-size: 15px;"></i>
                    </a>
                </div>
            `);

            notification.add(message, {
                title: payload.title,
                type: payload.type || "warning",
                sticky: payload.sticky || false,
                className: "cyllo_alert_notify"
            });
        });

        // Listen for real-time graph refreshes - standard bus channel
        bus_service.subscribe("notification", (payload) => {
            if (payload.type === "refresh_graph") {
                env.bus.trigger("REFRESH_GRAPH", payload);
            }
        });
    },
};

registry.category("services").add("cyllo_analytics_notifications", analyticsNotificationService);
