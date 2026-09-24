/* @odoo-module */
import publicWidget from "@web/legacy/js/public/public_widget";
import { PortalHomeCounters } from '@portal/js/portal';
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.portalAddressAdd = publicWidget.Widget.extend({
    selector: '.portal_address_add_temp',
    events: {
        'change .country': '_onChangeCountry', // Change event for the country select element
    },
    // Handler for the change event on the country select element
    _onChangeCountry: function(ev) {
        var self = this;
        var selectedCountryId = self.target.children[1][7].value;
        var stateDiv = $(self.target.children[1].children[0].children[12])
        var states = jsonrpc(`/web/dataset/call_kw/res.country.state/search_read`, {
                model: "res.country.state",
                method: "search_read",
                args: [[['country_id', '=', parseInt(selectedCountryId)]]],
                kwargs: {},
            }).then(function (states) {
            if (states.length == 0) {
                stateDiv.hide();
            }else{
            stateDiv.show();
            var optionsHTML = '';
            states.forEach(function(state) {
                optionsHTML += '<option value="' + state.id + '" t-att-selected="state.id == partner.state_id.id">' + state.name + ' </option>';
            });
            $(self.target.children[1][8])[0].innerHTML = optionsHTML;
            }
        });
    }
});

publicWidget.registry.PortalHomeCounters.include({
    /**
     * @override
     */
     async _updateCounters(elem) {
        const numberRpc = 3;
        const needed = Object.values(this.el.querySelectorAll('[data-placeholder_count]'))
                                .map(documentsCounterEl => documentsCounterEl.dataset['placeholder_count']);
        const counterByRpc = Math.ceil(needed.length / numberRpc);  // max counter, last can be less
        const countersAlwaysDisplayed = this._getCountersAlwaysDisplayed();

        const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(async i => {
            const documentsCountersData = await this.rpc("/my/counters", {
                counters: needed.slice(i * counterByRpc, (i + 1) * counterByRpc)
            });
            Object.keys(documentsCountersData).forEach(counterName => {
                const documentsCounterEl = this.el.querySelector(`[data-placeholder_count='${counterName}']`);
                documentsCounterEl.textContent = documentsCountersData[counterName];
                // The element is hidden by default, only show it if its counter is > 0 or if it's in the list of counters always shown
                if (documentsCountersData[counterName] >= 0 || countersAlwaysDisplayed.includes(counterName)) {
                    documentsCounterEl.parentElement.parentElement.parentElement.parentElement.classList.remove('d-none');
                if(documentsCounterEl.dataset['placeholder_count']=='login_and_security'){
                    documentsCounterEl.classList.remove('rounded-pill')
                    documentsCounterEl.classList.add('rounded-pill-login-security')
                }
                if(documentsCounterEl.dataset['placeholder_count']=='address_count'){
                    documentsCounterEl.classList.remove('rounded-pill')
                    documentsCounterEl.classList.add('rounded-pill-address')
                }
                if(documentsCounterEl.dataset['placeholder_count']=='invoice_count'){
                    documentsCounterEl.classList.remove('rounded-pill')
                    documentsCounterEl.classList.add('rounded-pill-invoice')
                }
                if(documentsCounterEl.dataset['placeholder_count']=='order_count'){
                    documentsCounterEl.classList.remove('rounded-pill')
                    documentsCounterEl.classList.add('rounded-pill-order')
                }
                if(documentsCounterEl.dataset['placeholder_count']=='quotation_count'){
                    documentsCounterEl.classList.remove('rounded-pill')
                    documentsCounterEl.classList.add('rounded-pill-quotation')
                }
                }
            });
            return documentsCountersData;
        });
        return Promise.all(proms).then((results) => {
            this.el.querySelector('.o_portal_doc_spinner').remove();
        });
    },
});
