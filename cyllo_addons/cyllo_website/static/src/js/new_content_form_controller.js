/** @odoo-module **/
import { NewContentFormController } from '@website/js/new_content_form'
import { patch } from "@web/core/utils/patch";

patch(NewContentFormController.prototype, {
    setup() {
        super.setup();
    },

    async saveButtonClicked(params = {}) {
        params = {...params, computePath: () => this.computePath()}
        return await super.saveButtonClicked(params);
    }
})