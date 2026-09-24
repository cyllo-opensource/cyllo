/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CrmLeadDashboard } from './crm_lead_dashboard';
/**
 * A renderer for the stock move dashboard list view.
 */
export class CrmLeadDashboardRenderer extends ListRenderer {};

CrmLeadDashboardRenderer.template = 'cyllo_crm.CrmLeadListView';
CrmLeadDashboardRenderer.components= Object.assign({}, ListRenderer.components, {CrmLeadDashboard})
export const CrmLeadListView = {
    ...listView,
    Renderer: CrmLeadDashboardRenderer,
};
registry.category("views").add("crm_lead_dashboard_list", CrmLeadListView);
