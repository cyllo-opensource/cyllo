/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.SupportTicketFormLayout = publicWidget.Widget.extend({
    selector: '.cyllo_register_support_ticket_form',
    events: {
        'change select[name="ticket_type"]': '_onTicketTypeChange',
    },

    _onTicketTypeChange: function (event) {
        var value = event.target.value;
        var issueTypeSection = document.getElementById("issue_type_section");

        if (value === "issues") {
            issueTypeSection.style.display = "block";
        } else {
            issueTypeSection.style.display = "none";
        }
    }
});

export default {
    SupportTicketFormLayout: publicWidget.registry.SupportTicketFormLayout,
};