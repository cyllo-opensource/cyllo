/** @odoo-module */

import {registry} from "@web/core/registry";
import {calendarView} from "@web/views/calendar/calendar_view";
import {DocCalenderController} from "./docCalenderController";
import {DocCalenderModel} from "./docCalenderModel";
import {DocCalenderRenderer} from "./docCalenderRenderer";


export const docCalenderView = {
    ...calendarView,
    Controller: DocCalenderController,
    Model: DocCalenderModel,
    Renderer: DocCalenderRenderer
};

registry.category("views").add("doc_calender_view", docCalenderView);