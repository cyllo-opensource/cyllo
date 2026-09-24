/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype,{
    async onPagerUpdate({ offset, resIds }){
        super.onPagerUpdate({offset, resIds});
        this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
    }
});