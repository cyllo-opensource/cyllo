/** @odoo-module */
import {ListRenderer} from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

export class SheetListRenderer extends ListRenderer {
    static template = "SheetListRenderer";
    static recordRowTemplate = "SheetListRenderer.RecordRaw"

    setup() {
        super.setup()
        this.action = useService("action");
    }

    async onCellClicked(record, column, ev) {
        if (ev.target.special_click) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.client",
            tag: "main_spreadsheet",
            context: {
                resId: record.resId
            }
        })
    }
    get getEmptyRowIds() {
        return []
    }
}