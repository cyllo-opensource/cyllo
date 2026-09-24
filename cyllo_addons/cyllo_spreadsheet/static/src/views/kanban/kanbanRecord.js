/** @odoo-module */
import {KanbanRecord, CANCEL_GLOBAL_CLICK} from "@web/views/kanban/kanban_record";

export class SheetKanbanRecord extends KanbanRecord {
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        const {record} = this.props;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "main_spreadsheet",
            context: {
                resId: record.resId
            }
        })
    }
}