/** @odoo-module */

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Component, useState, onWillStart, onWillDestroy, onMounted} from "@odoo/owl";
import {RepairCard} from "../repair_card/repair_card";

export class RepairFloorDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");

        this.state = useState({
            currentFilter: 'confirmed',
            employees: [],
            selectedEmployee: null,
            repairs: {draft: [], confirmed: [], under_repair: [], done: [], cancel: []},
            isManager: false,
            highlightedRepairId: this.props.action?.context?.default_repair_id || null,
        });

        onWillStart(async () => {
            this.state.isManager = await this.user.hasGroup("cyllo_shopfloor_repair.group_shopfloor_repair_manager");
            await this.loadEmployees();
            await this.fetchRepairOrders();
        });
    }

    async loadEmployees() {
        this.state.employees = await this.orm.searchRead(
            "hr.employee", [], ["id", "name", "user_id", "image_128"]);
        const currentUserEmployee = this.state.employees.find(
            employee => employee.user_id?.[0] == this.user.userId)
        this.state.selectedEmployee = currentUserEmployee
            ? currentUserEmployee : this.state.employees?.[0]
    }

    selectEmployee(employee) {
        this.state.selectedEmployee = employee;
    }

    // Simple tab navigation
    setView(viewName) {
        this.state.currentFilter = viewName;
        this.state.highlightedRepairId = null; // Clear isolate mode on tab change
        this.fetchRepairOrders();
    }

    goHome() {
        window.location.href = '/web';
    }

    async fetchRepairOrders() {
        let domain = [["state", "in", ["draft", "confirmed", "under_repair", "done", "cancel"]]];
        if (this.state.highlightedRepairId) {
            domain.push(["id", "=", this.state.highlightedRepairId]);
        }
        
        const records = await this.orm.searchRead(
            "repair.order",
            domain,
            [
                "name", "state", "product_id", "partner_id", "user_id",
                "under_warranty", "operator_ids",
                "current_start_time", "is_timer_running", "total_accumulated_time", "sale_order_id", "tag_ids",
            ]
        );

        const tagIds = [...new Set(records.flatMap(r => r.tag_ids || []))];
        const tagMap = {};
        if (tagIds.length > 0) {
            const tags = await this.orm.searchRead("repair.tags", [["id", "in", tagIds]], ["id", "name"]);
            tags.forEach(t => { tagMap[t.id] = t; });
        }
        this.state.repairs = {draft: [], confirmed: [], under_repair: [], done: [], cancel: []};
        records.forEach(record => {
            record.tags_data = (record.tag_ids || []).map(id => tagMap[id]).filter(Boolean);

            if (this.state.repairs[record.state]) {
                this.state.repairs[record.state].push(record);
            }
        });
        
        if (this.state.highlightedRepairId && records.length > 0) {
            this.state.currentFilter = records[0].state;
        }
    }
}

RepairFloorDashboard.template = "repair_floor.Dashboard";
RepairFloorDashboard.components = {RepairCard};

registry.category("actions").add("repair_floor.dashboard", RepairFloorDashboard);
