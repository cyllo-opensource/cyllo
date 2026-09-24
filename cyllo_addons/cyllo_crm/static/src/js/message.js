/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("pin_message", {
    sequence: 15,
    icon: (component) =>
        component.props.message?.is_pinned ? "fa-thumb-tack diagonal-strike" : "fa-thumb-tack",
    title: (component) =>
        component.props.message?.is_pinned ? _t("Unpin") : _t("Pin"),
    condition: (component) => Boolean(component.props?.message?.id),

    async onClick(component) {
        const orm = component.env.services.orm;
        const notification = component.env.services.notification;
        const message = component.props.message;

        if (!message?.id) {
            console.error('No message ID found');
            notification.add(_t("Failed to toggle pin"), { type: "danger" });
            return;
        }

        try {
            await orm.call("mail.message", "toggle_pin", [[message.id]]);
            message.is_pinned = !message.is_pinned;
            notification.add(
                message.is_pinned ? _t("Message pinned") : _t("Message unpinned"),
                { type: "success" }
            );
        } catch (error) {
            console.error("Pin error:", error);
            notification.add(_t("Failed to toggle pin"), { type: "danger" });
        }
    },
});