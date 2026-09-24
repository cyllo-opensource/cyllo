/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class TaxReturnListController extends ListController {
    async createRecord() {
        this.actionService.doAction({
            name: "Tax Return",
            type: "ir.actions.act_window",
            res_model: "tax.return.wizard",
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("views").add("tax_return_list", {
    ...listView,
    Controller: TaxReturnListController,
});
