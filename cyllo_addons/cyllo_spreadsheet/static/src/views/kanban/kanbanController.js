/** @odoo-module */
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {useSpreadsheet} from "../../hooks/useSpreadsheet";

export class SheetKanbanController extends KanbanController {
    static template = "SheetKanbanController";

    setup() {
        super.setup();
        this.spreadsheet = useSpreadsheet()
    }
}