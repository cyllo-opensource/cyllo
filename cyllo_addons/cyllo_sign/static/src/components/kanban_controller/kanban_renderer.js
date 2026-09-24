/** @odoo-module */
import { KanbanSignRecord } from './kanban_record';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';


export class KanbanSignRenderer extends KanbanRenderer {
    async setup() {
        super.setup(...arguments);
    }
}
KanbanSignRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: KanbanSignRecord,
};
