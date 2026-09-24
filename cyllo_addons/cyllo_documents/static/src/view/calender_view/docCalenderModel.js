/** @odoo-module */

import { CalendarModel } from "@web/views/calendar/calendar_model";

export class DocCalenderModel extends CalendarModel {
    setup(params, services) {
        params.fieldNames.push("is_locked", "mimetype", "brochure_url", "attachment_id")
        super.setup(params, services);
    }
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(rawRecord);
        result.isLocked = rawRecord["is_locked"] || false
        return result;
    }
}
