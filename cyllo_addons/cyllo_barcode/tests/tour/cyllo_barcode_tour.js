/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { _t } from "@web/core/l10n/translation";

registry.category("web_tour.tours").add('cy_barcode_main', {
    test: true,
    url: '/web#action=cyllo_barcode_tags',
    steps: () => [{
        trigger: ".cyllo-barcode__scanner-section",
        content: _t("Click here to Open Camera."),
        position: "left",
    },{
        trigger: ".btn-primary",
        content: _t("Click here to Close Camera."),
        position: "left",
    },{
        trigger: ".col-md-4.mr-3.main-barcode-button",
        content: _t("Click here to Open Inventory Adjustment."),
        position: "left",
    },{
        trigger: ".fa-sign-out",
        content: _t("Click here to Close the current window."),
        position: "left",
    },{
        trigger: ".w-50.main-barcode-button:contains('Batch')",
        content: _t("Click here to Open Batch Transfer."),
        position: "left",
    },{
        trigger: ".fa-sign-out",
        content: _t("Click here to Close the current window."),
        position: "left",
    },{
        trigger: ".cy-barcode__btn:contains('Delivery')",
        content: _t("Click here to open Operations."),
        position: "left",
    },
]});
