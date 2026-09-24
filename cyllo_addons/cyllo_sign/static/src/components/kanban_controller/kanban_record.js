/** @odoo-module */
import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class KanbanSignRecord extends KanbanRecord {
    setup() {
        super.setup();
    }
    onGlobalClick(ev) {
        this.resId = this.props.record.evalContext.id
        this.action.doAction({
            'type': 'ir.actions.client',
            'name': this.props.record.evalContext.name,
            'tag': 'sign_configure',
            'params': {
                "res_model": 'sign.template',
                "res_id": this.resId,
            }
        })

    }
}
