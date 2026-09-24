/** @odoo-module **/

import { Notification } from "@web/core/notifications/notification";
import { patch } from "@web/core/utils/patch";

// Extend Notification props with "whatsapp" type
patch(Notification, {
    props: {
        ...Notification.props,
        type: {
            ...Notification.props.type,
            validate: (t) =>
                ["warning", "danger", "success", "info", "whatsapp"].includes(t),
        },
    },
});