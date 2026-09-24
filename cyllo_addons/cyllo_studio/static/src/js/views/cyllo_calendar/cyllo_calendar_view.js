/** @odoo-module **/

/**
 * cylloCalendarView
 *
 * Custom calendar view for Odoo Studio.
 *
 * Extends the default Odoo calendar view by replacing the renderer
 * with the custom `cylloCalendarRenderer`. This allows the Studio
 * interface to interact with calendar details and emit events.
 *
 * Key Features:
 *  - Uses a custom renderer to trigger 'CALENDAR_DETAILS' event
 *  - Preserves all base calendar view functionality
 *  - Can be force-registered to override default calendar view
 */
import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { cylloCalendarRenderer } from "./cyllo_calendar_renderer";

export const cylloCalendarView = {
   ...calendarView,
   Renderer: cylloCalendarRenderer,
}
registry.category("views").add("calendar", cylloCalendarView, {force: true});
