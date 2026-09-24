/** @odoo-module **/
import { listView } from '@web/views/list/list_view';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { formView } from "@web/views/form/form_view";
import { calendarView } from "@web/views/calendar/calendar_view";
import { pivotView } from "@web/views/pivot/pivot_view";
import { graphView } from "@web/views/graph/graph_view";
import { activityView } from "@mail/views/web/activity/activity_view";
import { hierarchyView } from "@web_hierarchy/hierarchy_view";

listView.icon = "ri-table-line"
kanbanView.icon = "ri-align-item-top-line"
formView.icon = "ri-profile-line"
calendarView.icon = "ri-calendar-line"
pivotView.icon = "ri-layout-2-line"
graphView.icon = "ri-line-chart-line"
activityView.icon = "ri-time-line"
hierarchyView.icon = "ri-organization-chart"