/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("ticket", {
    channel_types: ["channel", "chat", "group", "livechat"],
    help: _t("Create a helpdesk ticket from this conversation"),
    methodName: "execute_command_ticket",
});
