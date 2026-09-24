/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * IncidentRequestForm Widget
 * --------------------------
 * Handles dynamic behavior of the incident request form on the portal.
 *
 * Features:
 *  - Automatically selects the receptor based on the chosen initiator.
 *  - Fetches the related receptor via RPC from `/employee/parent`.
 */
publicWidget.registry.IncidentRequestForm = publicWidget.Widget.extend({
    selector: '.cy-incident_requests_form',
    events: {
        'change select[name="initiator"]': '_onChangeInitiator',
    },
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },
    /**
     * @private
     */
    _onChangeInitiator: function (ev) {
        var selectedInitiatorId = $(ev.currentTarget).val();
        this.rpc("/employee/parent", {
            employee_id: selectedInitiatorId,
        }).then(function (data) {
            var receptorName = data.receptor_id;
            this.$el.find('select[name="receptor"]').find('option').filter(function() {
                return $(this).text().trim() === receptorName.trim();
            }).prop('selected', true);
        });
    }
});