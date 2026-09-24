/** @odoo-module */
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {MoveLineRenderer} from "./moveLineRenderer";

export const moveLineView = {
    ...listView,
    Renderer: MoveLineRenderer,
};

registry.category("views").add("reconcile_one2many_click", moveLineView);
