/** @odoo-module */
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {ListController} from "@web/views/list/list_controller";
import {MoveLineRenderer} from "./moveLineRenderer";

class ReconcileMoveLineController extends ListController {}
ReconcileMoveLineController.template = "cyllo_accounting.ReconcileMoveLineController";

export const moveLineView = {
    ...listView,
    Controller: ReconcileMoveLineController,
    Renderer: MoveLineRenderer,
};

registry.category("views").add("reconcile_one2many_click", moveLineView);
