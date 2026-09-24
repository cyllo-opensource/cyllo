/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart } = owl;

export class CrmOpportunityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            isDashboardVisible: true,
        });

        this.crmOpportunityData = {};

        onWillStart(async () => {
            this.crmOpportunityData = await this.orm.call(
                "crm.lead",
                "retrieve_crm_dashboard"
            );
        });
    }

    toggleDashboardVisibility() {
        this.state.isDashboardVisible = !this.state.isDashboardVisible;
    }

    async setSearchContext(ev, filterType) {
    // Prevent default link behavior
        let filter_name = ev.currentTarget.getAttribute("filter_name");
        let filters = filter_name.split(',');
        let searchItems = this.env.searchModel.getSearchItems((item) => filters.includes(item.name));
        this.env.searchModel.query = [];
        for (const item of searchItems){
            this.env.searchModel.toggleSearchItem(item.id);
        }
    }
}

CrmOpportunityDashboard.template = "cyllo_crm.crm_Opportunity_dashboard";
