/** @odoo-module */
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {DocListController} from "./docListController";
import {DocListRenderer} from "./docListRenderer";

const docListView = {
    ...listView,
    Controller: DocListController,
    Renderer: DocListRenderer
}
registry.category("views").add("doc_list_view", docListView);
