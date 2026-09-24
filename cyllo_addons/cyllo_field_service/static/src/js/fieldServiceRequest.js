/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
publicWidget.registry.fieldServiceRequest = publicWidget.Widget.extend({
    selector: '.o_portal_fs_service_request',
    events: {
        'change select[name="partner_id"]': '_onSaleOrderChange',
    },
    init() {
        this.orm = this.bindService("orm");
        this.rpc = this.bindService("rpc");
    },
    async _onSaleOrderChange(ev){
        var partnerId = parseInt(ev.target.value)
        var SaleOrderId = this.el.querySelector('select[name="sale_order"]');
        var $SaleSelect = $('select[name="sale_order"]');
        var sale_orders = await this.orm.searchRead(
                "sale.order",
                [
                    ["partner_id", "=", partnerId],
                    ["state", "=", "sale"],
                ],
                ["id", "name", "display_name"]
            );
        $SaleSelect.empty();
        $SaleSelect.append($('<option>'));
        sale_orders.forEach(function (order) {
                $SaleSelect.append($('<option>').val(order.id).text(order.display_name));
            });
    },
});
