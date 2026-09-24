/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.BackendLinkClick = publicWidget.Widget.extend({
    selector: '#o_backend_user_dropdown_link',  // your link ID
    events: {
        'click': '_onClickLink',
    },

    _onClickLink: function (ev) {
        ev.preventDefault();
        localStorage.setItem("isSidebarOn", true)
        localStorage.setItem("cy_selected_app", 0 || false)
        window.location.href = '/web';
    },
});