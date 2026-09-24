/** @odoo-module */
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from '@web/core/registry';
import {useEffect} from "@odoo/owl";

export class BarcodeKanbanController extends KanbanController {
    static template = "BarcodeKanbanController";

    setup() {
        super.setup();
        this.breadcrumbTitle = this.getBreadcrumbTitle();
        useEffect(() => {
            this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", {show: true})
            return () => {
                this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", {show: true})
            }
        })
    }

    handleGoBack() {
        window.history.go(-1)
    }
    handleGoToDashboard() {
     this.actionService.doAction({
        type: 'ir.actions.client',
        tag: 'cyllo_barcode_tags',
    });
    }
    getBreadcrumbTitle() {
        const batchName = localStorage.getItem('cyllo-barcode-batch-name');
        if (batchName) {
          return batchName;
        }

       const operationName = localStorage.getItem('cyllo-barcode-operation-name');
       if (operationName) {
         return operationName;
       }
    }

}

export const barcodeKanbanView = {
    ...kanbanView,
    Controller: BarcodeKanbanController,
}
registry.category("views").add("barcode_kanban", barcodeKanbanView);
