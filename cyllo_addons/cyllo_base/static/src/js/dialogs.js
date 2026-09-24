/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
/*Patch the dialog box and changing the tittle*/
patch(Dialog.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.title.startsWith("Odoo")) {
            this.props.title = this.props.title.replace("Odoo", "Cyllo");
        }
        if (typeof this.data.scrollToOrigin !== "function") {
            this.data.scrollToOrigin = () => { };
        }
    }
});