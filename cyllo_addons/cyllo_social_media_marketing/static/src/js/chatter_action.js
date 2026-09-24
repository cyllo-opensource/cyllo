/* @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";


messageActionsRegistry.add("create_lead", {
    condition: (component) => component.canReplyTo,
    icon: "fa-check",
    title: () => _t("Convert to Lead"),
    onClick: (component) => component.createLead(),
    sequence: 0,
})