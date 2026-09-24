/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

export const debugNotificationService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        if (session.debug_denied) {
            notification.add(_t("Debug mode is restricted by your administrator."), {
                type: "warning",
                sticky: false,
            });
        }
        if (session.is_profile_readonly) {
            notification.add(_t("This profile is in Read-Only mode. Some actions are restricted."), {
                type: "warning",
                sticky: true,
            });
        }
    },
};

registry.category("services").add("debug_notification", debugNotificationService);
