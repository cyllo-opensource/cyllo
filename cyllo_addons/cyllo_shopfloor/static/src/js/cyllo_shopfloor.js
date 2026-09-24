/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillDestroy, onMounted } from "@odoo/owl";

class ShopFloorScreen extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = this.env.services.bus_service;
        this.userService = useService("user");

        this.state = useState({
            workcenters: [],
            selectedWorkcenter: null,
            selectedProduction: null,
            groupedWorkOrders: [],
            currentFilter: "ready",
            employees: [],
            selectedEmployee: null,
            isManager: false,
        });

        this.lastSyncTime = Date.now();

        onWillStart(async () => {
            this.state.isManager = await this.userService.hasGroup("cyllo_shopfloor.group_cyllo_shopfloor_manager");
            await this.fetchEmployees();
            await this.fetchWorkcenters();
            this.busService.addChannel("shopfloor_channel");
            this._onBusNotification = this._onBusNotification.bind(this);
            this.busService.addEventListener("notification", this._onBusNotification);
            const context = this.props.action?.context || {};
            if (context.default_production_id) {
                const targetMoId = context.default_production_id;

                const targetData = await this.orm.searchRead(
                    "mrp.workorder",
                    [["production_id", "=", targetMoId], ["state", "!=", "cancel"]],
                    ["workcenter_id"],
                    { limit: 1 }
                );

                if (targetData.length > 0) {
                    const targetWcId = targetData[0].workcenter_id[0];
                    this.state.selectedWorkcenter = this.state.workcenters.find((wc) => wc.id === targetWcId);
                    this.state.currentFilter = "all";
                    this.state.selectedProduction = targetMoId;
                    await this.loadWorkOrders();
                }
            }
        });

        this.timerInterval = setInterval(() => {
            const now = Date.now();
            const minutesSinceSync = (now - this.lastSyncTime) / 60000;

            for (const group of this.state.groupedWorkOrders) {
                for (const workOrder of group.workOrders) {
                    if (workOrder.is_user_working && this.state.selectedWorkcenter?.working_state !== "blocked") {
                        workOrder.display_duration = workOrder.base_duration + minutesSinceSync;
                    }
                }
            }
        }, 1000);

        onWillDestroy(() => {
            clearInterval(this.timerInterval);
            this.busService.removeEventListener("notification", this._onBusNotification);
        });
    }

    _onBusNotification({ detail: notifications }) {
        for (const { type, payload } of notifications) {
            if (type === "workorder_updated") {
                this.fetchWorkcenters();
                if (this.state.selectedWorkcenter && payload.workcenter_id === this.state.selectedWorkcenter.id) {
                    this.loadWorkOrders();
                }
            }
        }
    }

    async fetchEmployees() {
        this.state.employees = await this.orm.searchRead(
            "hr.employee",
            [],
            ["id", "name", "user_id", "image_128"]
        );

        this.state.selectedEmployee = this.state.employees.find(
            (employee) =>
                employee.user_id &&
                employee.user_id[0] === this.userService.userId
        ) || null;
    }

    selectEmployee(employee) {
        this.state.selectedEmployee = employee;
    }

    goHome() {
        window.location.href = '/web';
    }

    getShopfloorContext() {
        const ctx = { from_shopfloor: true };
        if (this.state.selectedEmployee) {
            ctx.employee_id = this.state.selectedEmployee.id;
        }
        return ctx;
    }

    async fetchWorkcenters() {
        const fetchedWorkcenters = await this.orm.searchRead(
            "mrp.workcenter",
            [],
            ["id", "name", "code", "working_state", "oee", "blocked_time"]
        );

        const metrics = await this.orm.call("mrp.workcenter", "get_shopfloor_dashboard_metrics", []);

        for (const wc of fetchedWorkcenters) {
            wc.metrics = metrics[wc.id] || {
                in_progress: 0,
                completed: 0,
                canceled: 0,
                total: 0,
            };
        }

        this.state.workcenters = fetchedWorkcenters;

        if (this.state.selectedWorkcenter) {
            const updatedWorkcenter = this.state.workcenters.find(
                (wc) => wc.id === this.state.selectedWorkcenter.id
            );
            if (updatedWorkcenter) {
                this.state.selectedWorkcenter = updatedWorkcenter;
            }
        }
    }

    async selectWorkcenter(workcenter) {
        this.state.selectedWorkcenter = workcenter;
        this.state.selectedProduction = null;
        await this.loadWorkOrders();
    }

    async loadWorkOrders() {
        if (!this.state.selectedWorkcenter) return;

        const domain = [
            ["workcenter_id", "=", this.state.selectedWorkcenter.id],
            ["production_state", "!=", "draft"],
        ];

        if (this.state.currentFilter === "cancel") {
            domain.push(["production_state", "=", "cancel"]);
        } else {
            if (this.state.currentFilter === "ready") {
            domain.push(["state", "!=", "cancel"]);
                domain.push(["production_state", "in", ["confirmed", "progress"]]);
            } else if (this.state.currentFilter === "done") {
                domain.push(["state", "!=", "cancel"]);
                domain.push(["production_state", "in", ["to_close", "done"]]);
            }
        }

        const rawWorkOrders = await this.orm.searchRead(
            "mrp.workorder",
            domain,
            [
                "id", "name", "production_id", "state", "duration", "is_user_working",
                "working_state", "product_id", "qty_production", "production_state",
                "shopfloor_blocking_wo_id", "time_ids"
            ]
        );

        this.lastSyncTime = Date.now();
        let allTimeIds = [];
        rawWorkOrders.forEach(wo => {
            if (wo.time_ids) allTimeIds.push(...wo.time_ids);
        });

        const activeTimers = {};
        if (allTimeIds.length > 0) {
            const timers = await this.orm.searchRead(
                "mrp.workcenter.productivity",
                [["id", "in", allTimeIds], ["date_end", "=", false]],
                ["workorder_id", "date_start"]
            );

            timers.forEach(t => {
                if (t.date_start && t.workorder_id) {
                    const dateStr = t.date_start.replace(" ", "T") + "Z";
                    const startTime = new Date(dateStr).getTime();
                    const elapsedMinutes = (Date.now() - startTime) / 60000;

                    const woId = t.workorder_id[0];
                    if (!activeTimers[woId]) activeTimers[woId] = 0;

                    activeTimers[woId] += Math.max(0, elapsedMinutes);
                }
            });
        }

        const grouped = {};
        for (const workOrder of rawWorkOrders) {
            const productionId = workOrder.production_id ? workOrder.production_id[0] : 0;
            const productionName = workOrder.production_id ? workOrder.production_id[1] : "Unknown MO";

            const rawProductName = workOrder.product_id ? workOrder.product_id[1] : "Unknown Product";
            const cleanProductName = rawProductName.replace(/^\[.*?\]\s*/, "");

            const liveElapsed = activeTimers[workOrder.id] || 0;
            workOrder.base_duration = (workOrder.duration || 0) + liveElapsed;
            workOrder.display_duration = workOrder.base_duration;

            if (!grouped[productionId]) {
                grouped[productionId] = {
                    production_id: productionId,
                    production_name: productionName,
                    product_name: cleanProductName,
                    qty: workOrder.qty_production || 0,
                    production_state: workOrder.production_state || "draft",
                    workOrders: [],
                };
            }
            grouped[productionId].workOrders.push(workOrder);
        }

        this.state.groupedWorkOrders = Object.values(grouped);

        const productionIds = this.state.groupedWorkOrders.map(g => g.production_id).filter(id => id);

        if (productionIds.length > 0) {
            const missingData = await this.orm.call(
                "mrp.production",
                "get_shopfloor_missing_components",
                [productionIds]
            );

            const moData = await this.orm.searchRead(
                "mrp.production",
                [["id", "in", productionIds]],
                ["id", "employee_ids"]
            );

            const otherWorkOrders = await this.orm.searchRead(
                "mrp.workorder",
                [
                    ["production_id", "in", productionIds],
                    ["state", "not in", ["done", "cancel"]],
                    ["workcenter_id", "!=", this.state.selectedWorkcenter.id]
                ],
                ["production_id", "name", "workcenter_id"],
                { order: "id asc" }
            );

            const nextWoByMo = {};
            for (const wo of otherWorkOrders) {
                const moId = wo.production_id[0];
                if (!nextWoByMo[moId]) {
                    nextWoByMo[moId] = [];
                }
                nextWoByMo[moId].push(wo);
            }

            for (const group of this.state.groupedWorkOrders) {
                group.missingComponents = missingData[group.production_id] || [];
                group.next_work_orders = nextWoByMo[group.production_id] || [];

                group.mo_employees = [];
                const mo = moData.find(m => m.id === group.production_id);

                if (mo && mo.employee_ids && Array.isArray(mo.employee_ids)) {
                    for (const empId of mo.employee_ids) {
                        const emp = this.state.employees.find(e => e.id === empId);
                        group.mo_employees.push({
                            id: empId,
                            name: emp ? emp.name : "Operator"
                        });
                    }
                }
            }
        }
    }

    selectProduction(productionId) {
        this.state.selectedProduction = productionId;
    }

    clearProductionSelection() {
        this.state.selectedProduction = null;
    }

    async goToWorkCenter(workcenterId, productionId, ev) {
        if (ev) ev.stopPropagation();
        const targetWorkcenter = this.state.workcenters.find((wc) => wc.id === workcenterId);
        if (targetWorkcenter) {
            this.state.currentFilter = "ready";
            await this.selectWorkcenter(targetWorkcenter);
            this.selectProduction(productionId);
        } else {
            // this.env.services.notification.add("Target workcenter not found.", { type: "warning" });
        }
    }

    clearSelection() {
        this.state.selectedWorkcenter = null;
        this.state.selectedProduction = null;
        this.state.groupedWorkOrders = [];
    }

    setFilter(filterValue) {
        this.state.currentFilter = filterValue;
        this.loadWorkOrders();
    }

    async blockWorkcenter(workcenterId, ev) {
        if (ev) ev.stopPropagation();
        this.action.doAction("mrp.act_mrp_block_workcenter_wo", {
            additionalContext: { default_workcenter_id: workcenterId },
            onClose: () => {
                this.fetchWorkcenters();
            },
        });
    }

    async unblockWorkcenter(workcenterId, ev) {
        if (ev) ev.stopPropagation();
        await this.orm.call("mrp.workcenter", "unblock", [workcenterId], {
            context: { from_shopfloor: true }
        });
        await this.fetchWorkcenters();
    }

    async startWorkOrder(workOrderId) {
        if (!this.state.selectedEmployee) {
            this.state.selectedEmployee = this.state.employees.find(
                (e) => e.user_id && e.user_id[0] === this.userService.userId
            );

            if (!this.state.selectedEmployee) {
                // this.env.services.notification.add("Your user account has no linked employee.", { type: "warning" }); Todo: check if it has any use
                return;
            }
        }

        await this.orm.call("mrp.workorder", "button_start", [[workOrderId]], {
            context: this.getShopfloorContext()
        });
    }

    async pauseWorkOrder(workOrderId) {
        await this.orm.call("mrp.workorder", "button_pending", [[workOrderId]], {
            context: this.getShopfloorContext()
        });
    }

    async finishWorkOrder(workOrderId) {
        if (!this.state.selectedEmployee) {
            // this.env.services.notification.add("Please select an operator first.", { type: "warning" }); Todo: check if it has any use
            return;
        }

        const action = await this.orm.call("mrp.workorder", "button_finish", [[workOrderId]], {
            context: this.getShopfloorContext()
        });

        if (action && action.type === "trigger_close_production") {
            await this.closeProduction(action.mo_id);
            return;
        }

        if (action && typeof action === "object" && action.type !== "ir.actions.act_window_close") {
            this.action.doAction(action, {
                onClose: () => {
                    this.loadWorkOrders();
                    this.fetchWorkcenters();
                },
            });
            return;
        }

        this.loadWorkOrders();
        this.fetchWorkcenters();
    }

    async openBlockingWorkOrder(workOrderId, ev) {
        if (ev) ev.stopPropagation();
        if (!workOrderId) return;

        const targetData = await this.orm.read(
            "mrp.workorder",
            [workOrderId],
            ["workcenter_id", "production_id"]
        );

        if (targetData.length > 0) {
            const targetWcId = targetData[0].workcenter_id[0];
            const targetMoId = targetData[0].production_id[0];

            const targetWorkcenter = this.state.workcenters.find((wc) => wc.id === targetWcId);

            if (targetWorkcenter) {
                this.state.currentFilter = "ready";
                await this.selectWorkcenter(targetWorkcenter);
                this.selectProduction(targetMoId);
            } else {
                // this.env.services.notification.add(
                //     "Cannot navigate: target workcenter not found.",
                //     { type: "warning" }
                // ); Todo: check if it has any use
            }
        }
    }

    formatDuration(minutes) {
        if (!minutes || minutes < 0) return "00:00:00";
        const totalSeconds = Math.floor(minutes * 60);
        const hours = Math.floor(totalSeconds / 3600).toString().padStart(2, "0");
        const mins = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, "0");
        const secs = (totalSeconds % 60).toString().padStart(2, "0");
        return `${hours}:${mins}:${secs}`;
    }

    async actionOpenProduction(productionId) {
        if (!productionId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            res_id: productionId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async actionOpenProductCatalog(productionId) {
        if (!productionId) return;
        this.action.doAction("cyllo_shopfloor.action_mrp_add_component_wizard", {
            additionalContext: { default_production_id: productionId },
            onClose: () => {
                this.loadWorkOrders();
            },
        });
    }

    async actionScrapComponent(productionId) {
        if (!productionId) return;
        this.action.doAction("cyllo_shopfloor.action_mrp_scrap_component_wizard", {
            additionalContext: { default_production_id: productionId },
            onClose: () => {
                this.loadWorkOrders();
            },
        });
    }

    async closeProduction(productionId) {
        if (!productionId) return;

        const action = await this.orm.call("mrp.production", "action_shopfloor_close_mo", [[productionId]]);

        if (action && typeof action === "object") {
            this.action.doAction(action, {
                onClose: () => {
                    this.loadWorkOrders();
                    this.fetchWorkcenters();
                },
            });
        } else {
            this.clearSelection();
            this.loadWorkOrders();
        }
    }

    async actionAddWorkOrder(productionId) {
        if (!productionId) return;
        this.action.doAction(
            {
                name: "Add Work Order",
                type: "ir.actions.act_window",
                res_model: "mrp.add.workorder.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_production_id: productionId,
                    default_workcenter_id: this.state.selectedWorkcenter ? this.state.selectedWorkcenter.id : false,
                },
            },
            {
                onClose: () => {
                    this.loadWorkOrders();
                },
            }
        );
    }

    async actionRerouteWorkOrder(productionId) {
        if (!productionId) return;

        const group = this.state.groupedWorkOrders.find((g) => g.production_id === productionId);
        if (!group || group.workOrders.length === 0) return;

        const activeWorkOrder = group.workOrders.find((wo) => !["done", "cancel"].includes(wo.state));

        if (!activeWorkOrder) {
            // this.env.services.notification.add("All work orders for this MO are already completed.", {
            //     type: "warning",
            // }); Todo: check if it has any use
            return;
        }

        this.action.doAction(
            {
                name: "Reroute Work Order",
                type: "ir.actions.act_window",
                res_model: "mrp.reroute.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_workorder_id: activeWorkOrder.id,
                    default_production_id: productionId,
                },
            },
            {
                onClose: () => {
                    this.fetchWorkcenters();
                    this.loadWorkOrders();
                },
            }
        );
    }

    async viewWorksheet(workOrderId) {
        if (!workOrderId) return;
        const action = await this.orm.call("mrp.workorder", "action_show_shopfloor_worksheet", [[workOrderId]]);
        this.action.doAction(action);
    }
}

ShopFloorScreen.template = "cyllo_shopfloor.ShopfloorTemplate";
registry.category("actions").add("shopfloor_screen", ShopFloorScreen);
