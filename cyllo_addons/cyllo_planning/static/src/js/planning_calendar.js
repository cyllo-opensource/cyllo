/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarModel } from "@web/views/calendar/calendar_model";

patch(CalendarModel.prototype, {
    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(...arguments);
        if (rawRecord.is_conflict) {
            result.title = "⚠️ " + (result.title || "");
        }
        return result;
    }
});
