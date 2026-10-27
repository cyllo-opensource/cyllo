/** @odoo-module */
import {ListRenderer} from "@web/views/list/list_renderer";

export class MoveLineRenderer extends ListRenderer {
    get getEmptyRowIds() {
        return []
    }

    getRowClass(record) {
        const classNames = super.getRowClass(record).split(/\s+/).filter(Boolean);
        const selectedLineIds = this.props.globalState?.selectedLineIds || [];
        if (selectedLineIds.includes(record.resId)) {
            classNames.push("o_reconcile_line_selected");
        }
        return classNames.join(" ");
    }
}

MoveLineRenderer.props = [...ListRenderer.props, "globalState?"];
