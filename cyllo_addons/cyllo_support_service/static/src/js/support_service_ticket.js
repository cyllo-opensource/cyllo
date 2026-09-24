/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.SupportTicketLayout = publicWidget.Widget.extend({
    selector: '.oe_support_service_ticket',
    events: {
        'change .oe_apply_layout input': '_onApplyTicketLayoutChange',
    },

    _onApplyTicketLayoutChange:function(event) {
        var value = event.target.value
        var isList = value === 'list';
        const activeClasses = event.target.parentElement.dataset.activeClasses.split(' ');
        jsonrpc('/support-service-ticket/save_support_service_ticket_layout_mode', {
            'layout_mode': isList ? 'list' : 'grid',
        });
        event.target.parentElement.querySelectorAll('.btn').forEach((btn) => {
            activeClasses.map(c => btn.classList.toggle(c));
        });
        var $grid = this.$el.find('#ticket_content');
        $grid.toggleClass('o_support_ticket_layout_list', isList);
    }
});

export default {
    SupportTicketLayout: publicWidget.registry.SupportTicketLayout,
}