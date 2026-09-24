/** @odoo-module */

import {CalendarRenderer} from "@web/views/calendar/calendar_renderer";
import {CalendarCommonRenderer} from "@web/views/calendar/calendar_common/calendar_common_renderer";
import {CalendarCommonPopover} from "@web/views/calendar/calendar_common/calendar_common_popover";

export class DocCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "DocCalendarCommonPopover.footer"
    }
}

export class DocCalenderCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: DocCalendarCommonPopover
    }
}

export class DocCalenderRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: DocCalenderCommonRenderer,
        week: DocCalenderCommonRenderer,
        month: DocCalenderCommonRenderer,
    }

}
