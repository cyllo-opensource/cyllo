/* @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

// Adding a new message action to create a ticket
messageActionsRegistry.add("create_ticket", {
    condition: (component) => component.canReplyTo,
    icon: "fa-user-plus",
    title: () => _t("Create Ticket"),
    onClick: (component) => component.createTicket(),
    sequence: 0,
})