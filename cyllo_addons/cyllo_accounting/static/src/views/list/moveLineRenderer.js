/** @odoo-module */
import {ListRenderer} from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

export class MoveLineRenderer extends ListRenderer {
    static template = "MoveLineRenderer";
    static recordRowTemplate = "MoveLineRenderer.RecordRaw"

    setup() {
        super.setup()
        this.action = useService("action");
    }

    get getEmptyRowIds() {
        return []
    }

    handleViewClick(record) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            target: 'current',
            res_id: record.resId,
            res_model: record.resModel,
            views: [[false, 'form']],
        })
    }

}
