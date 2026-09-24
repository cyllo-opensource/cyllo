/** @odoo-module */

import {registry} from "@web/core/registry";
import {DocController} from "./docController";
import {DocRenderer} from "./docRenderer";
import { kanbanView } from "@web/views/kanban/kanban_view";

export const docView = {
    ...kanbanView,
    Controller: DocController,
    Renderer: DocRenderer,
};

registry.category("views").add("doc_kanban_view", docView);
