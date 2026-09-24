/** @odoo-module */
import {registry} from "@web/core/registry";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {SheetKanbanRenderer} from "./kanbanRenderer";
import {SheetKanbanController} from "./kanbanController";

export const sheetKanbanView = {
    ...kanbanView,
    Controller: SheetKanbanController,
    Renderer: SheetKanbanRenderer,
};

registry.category("views").add("cy_spreadsheet_kanban", sheetKanbanView);