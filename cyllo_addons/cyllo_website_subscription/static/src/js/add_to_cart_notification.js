/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AddToCartNotification } from "@website_sale/js/notification/add_to_cart_notification/add_to_cart_notification";

patch(AddToCartNotification.prototype, {
    getFormattedPrice(line) {
        let price = super.getFormattedPrice(line);
        if (line.subscription_duration) {
            price += line.subscription_duration;
        }
        return price;
    }
});
