/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class TicketIssueSuggestions extends Component {
    static template = "cyllo_helpdesk.TicketIssueSuggestions";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            issues: [],
            isAdding: false,
            newIssueName: "",
        });

        onWillStart(async () => {
            await this.loadIssues();
        });
    }

    async loadIssues() {
        try {
            const issues = await this.orm.searchRead(
                "helpdesk.common.issue",
                [["active", "=", true]],
                ["id", "name", "color"],
                { order: "sequence, id", limit: 30 }
            );
            this.state.issues = issues;
        } catch (e) {
            this.state.issues = [];
        }
    }

    async selectIssue(issueName) {
        if (this.props.record) {
            await this.props.record.update({ name: issueName });
        }
    }

    toggleAdd(show) {
        this.state.isAdding = show;
        this.state.newIssueName = "";
    }

    async createAndSelectIssue() {
        const name = this.state.newIssueName.trim();
        if (!name) {
            return;
        }
        try {
            const [newId] = await this.orm.create("helpdesk.common.issue", [{ name: name }]);
            this.state.issues.push({ id: newId, name: name });
            await this.selectIssue(name);
            this.toggleAdd(false);
        } catch (error) {
            this.notification.add("Could not create issue suggestion", { type: "danger" });
        }
    }

    onKeyDown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.createAndSelectIssue();
        } else if (ev.key === "Escape") {
            this.toggleAdd(false);
        }
    }
}

export const ticketIssueSuggestionsWidget = {
    component: TicketIssueSuggestions,
};

registry.category("view_widgets").add("ticket_issue_suggestions", ticketIssueSuggestionsWidget);
