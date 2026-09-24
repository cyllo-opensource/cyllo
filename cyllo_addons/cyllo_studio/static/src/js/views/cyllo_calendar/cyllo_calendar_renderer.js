/** @odoo-module **/

/**
 * cylloCalendarRenderer
 *
 * Extends the standard Odoo CalendarRenderer to trigger a custom
 * event with detailed calendar information for Odoo Studio.
 *
 * Responsibilities:
 *  - Inherits all default calendar rendering behavior
 *  - Emits 'CALENDAR_DETAILS' on mount with model metadata, view info, and active fields
 *
 * Triggered event payload:
 *  - model: The model name of the calendar
 *  - viewId: Current view ID
 *  - viewType: Type of the current view (calendar)
 *  - mode: Metadata for the calendar mode
 *  - activeFields: Active fields in the calendar view
 *  - calendar_info: Full calendar model information
 */
import {
    CalendarRenderer
} from "@web/views/calendar/calendar_renderer";
import {
    CalendarController
} from "@web/views/calendar/calendar_controller";
import {
    onMounted
} from "@odoo/owl";

CalendarController.template = 'cyllo_studio.CylloCalendarController'

export class cylloCalendarRenderer extends CalendarRenderer {
    setup() {
        super.setup();
        onMounted(() => {
            this.env.bus.trigger("CALENDAR_DETAILS", {
                model: this.props.model.meta.resModel,
                viewId: this.env.config.viewId,
                viewType: this.env.config.viewType,
                mode: this.props.model.meta,
                activeFields: this.props.model.meta.activeFields,
                calendar_info: this.props.model
            });
        });
    }
}
