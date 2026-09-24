/** @odoo-module */
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {SheetListRenderer} from "./listRenderer";
import {SheetListController} from "./listController";

export const sheetListView = {
    ...listView,
    Controller: SheetListController,
    Renderer: SheetListRenderer,
};

registry.category("views").add("cy_spreadsheet_list", sheetListView);