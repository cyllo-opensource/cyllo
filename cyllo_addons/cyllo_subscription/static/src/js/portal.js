/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.reason-modal',
    events: {
        'change select[name="reasons"]': '_onReasonsChange',
    },
    _onReasonsChange: function () {
        const el = this.el.querySelector('select[name="reasons"]')
        const customReasonContainer = this.el.querySelector('#custom-reason-container')
        if (el.value === 'other') {
            customReasonContainer.classList.remove('d-none');
        } else {
            customReasonContainer.classList.add('d-none');
        }
    },
});