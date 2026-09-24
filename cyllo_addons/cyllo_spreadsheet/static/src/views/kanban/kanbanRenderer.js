/** @odoo-module */
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {SheetKanbanRecord} from "./kanbanRecord";

export class SheetKanbanRenderer extends KanbanRenderer {
}

SheetKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: SheetKanbanRecord
}