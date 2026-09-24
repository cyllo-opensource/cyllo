/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { useService } from "@web/core/utils/hooks";
import { CreateProductWizard } from "./productWizard";

patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },

    createProduct() {
        this.dialog.add(CreateProductWizard, {
            title: "New Product",
        });
    },
});