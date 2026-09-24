/* @odoo-module */
import { Notebook } from "@web/core/notebook/notebook";
import { patch } from "@web/core/utils/patch";


patch(Notebook.prototype, {
    setup() {
        super.setup();
    }
})
Notebook.props = {
    ...Notebook.props,
    resId: { type: Number, optional:true }
}