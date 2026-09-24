/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv } from "@odoo/owl";

export class ImportedTableListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
        
        useSubEnv({
            openImportWizard: this.openImportWizard.bind(this),
        });
    }

    /**
     * Handler for the "Import New Table" button
     */
    async openImportWizard() {
        this.action.doAction("cyllo_analytics.action_import_xlsx_wizard", {
            onClose: () => {
                this.model.load();
            },
        });
    }
}

registry.category("views").add("imported_table_list", {
    ...listView,
    Controller: ImportedTableListController,
});
