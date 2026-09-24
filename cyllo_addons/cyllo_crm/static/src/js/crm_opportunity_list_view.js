/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CrmOpportunityDashboard } from './crm_opportunity_dashboard';
/**
 * A renderer for the stock move dashboard list view.
 */
export class CrmOpportunityDashboardRenderer extends ListRenderer {};

CrmOpportunityDashboardRenderer.template = 'cyllo_crm.CrmOpportunityListView';
CrmOpportunityDashboardRenderer.components= Object.assign({}, ListRenderer.components, {CrmOpportunityDashboard})
export const CrmOpportunityListView = {
    ...listView,
    Renderer: CrmOpportunityDashboardRenderer,
};
registry.category("views").add("crm_opportunity_dashboard_list", CrmOpportunityListView);
