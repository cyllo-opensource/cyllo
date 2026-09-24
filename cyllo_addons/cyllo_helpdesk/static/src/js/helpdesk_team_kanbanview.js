/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { HelpdeskOverview } from './helpdesk_overview';


export class HelpdeskDashBoardKanbanRenderer extends KanbanRenderer {
    setup() {
    super.setup()
    this.overView = this.props.list.evalContext.overview;
    }
};

HelpdeskDashBoardKanbanRenderer.template = 'cyllo_helpdesk.HelpdeskTeamKanbanView';
HelpdeskDashBoardKanbanRenderer.components= Object.assign({}, KanbanRenderer.components, {HelpdeskOverview})

export const HelpdeskDashBoardKanbanView = {
    ...kanbanView,
    Renderer: HelpdeskDashBoardKanbanRenderer,
};

registry.category("views").add("helpdesk_dashboard_kanban", HelpdeskDashBoardKanbanView);
