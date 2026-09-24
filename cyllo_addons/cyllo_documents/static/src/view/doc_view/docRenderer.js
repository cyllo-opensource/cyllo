/** @odoo-module */

import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {DocRecord} from "./docRecord";

export class DocRenderer extends KanbanRenderer {
    static template = "docRenderer"
    static props = [
        ...KanbanRenderer.props,
        'selection?',
    ]
    static components = {
        ...KanbanRenderer.components,
        DocRecord,
    }
}
