/** @odoo-module **/
import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { SupportServiceOverview } from './support_service_overview';


export class SupportServiceDashBoardKanbanRenderer extends KanbanRenderer {
    /* Extending KanbanRenderer to add the dashboard in the kanban view of support service team */
    setup() {
        super.setup()
        this.overView = this.props.list.evalContext.overview;
    }
}

SupportServiceDashBoardKanbanRenderer.template = 'cyllo_support_service.SupportServiceTeamKanbanView';
SupportServiceDashBoardKanbanRenderer.components= Object.assign({}, KanbanRenderer.components, {SupportServiceOverview})

export const SupportServiceDashBoardKanbanView = {
    ...kanbanView,
    Renderer: SupportServiceDashBoardKanbanRenderer,
};
// Adding view into the registry
registry.category("views").add("support_service_dashboard_kanban", SupportServiceDashBoardKanbanView);
