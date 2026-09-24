/** @odoo-module */

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PayrollDashboard extends Component {

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        // ---------------- STATE ----------------
        this.state = useState({
            employees: 0,
            contracts: 0,
            generated: 0,
            paid: 0,
            warnings: [],
            batches: [],

            // Employee Cost Data
            employee_cost_year_labels: [],
            employee_cost_year_data: [],
            employee_cost_month_labels: [],
            employee_cost_month_data: [],

            employee_cost_day_labels: [],
            employee_cost_day_data: [],

            // Payroll Distribution Data
            payroll_dist_year_labels: [],
            payroll_dist_year_data: [],
            payroll_dist_year_type_ids: [],

            payroll_dist_month_labels: [],
            payroll_dist_month_data: [],
            payroll_dist_month_type_ids: [],

            payroll_dist_day_labels: [],
            payroll_dist_day_data: [],
            payroll_dist_day_type_ids: [],

            // Global Filter
            dashboard_period: "year",   // default
            employee_cost_chart_type: "bar",
            payroll_dist_chart_type: "pie",
            stats_year: {},
            stats_month: {},
            stats_day: {},
        });

        this.employeeCostChart = null;
        this.payrollPieChart = null;

        // ---------------- LOAD DATA ----------------
        onWillStart(async () => {
            const data = await this.orm.call(
                "employee.payslip",
                "get_payroll_dashboard_data",
                []
            );
            Object.assign(this.state, data);
        });

        // ---------------- MOUNT ----------------
        onMounted(() => {
            this.renderEmployeeCostChart();
            this.renderPayrollPieChart();
        });

        // ---------------- FILTER HANDLER ----------------
        this.onGlobalFilterChange = (ev) => {
            // t-model updates state automatically, but we ensure re-render
            const period = this.state.dashboard_period;
            if (this.state.stats_year && this.state.stats_month && this.state.stats_day) {
                let stats = this.state.stats_year;
                if (period === 'month') stats = this.state.stats_month;
                if (period === 'day') stats = this.state.stats_day;

                this.state.generated = stats.generated || 0;
                this.state.paid = stats.paid || 0;
            }
            this.renderEmployeeCostChart();
            this.renderPayrollPieChart();
        };
    }

    setChartType(type) {
        this.state.employee_cost_chart_type = type;
        this.renderEmployeeCostChart();
    }

    setPayrollDistChartType(type) {
        this.state.payroll_dist_chart_type = type;
        this.renderPayrollPieChart();
    }

    onFilterChange(period) {
        this.state.dashboard_period = period;
        if (this.state.stats_year && this.state.stats_month && this.state.stats_day) {
            let stats = this.state.stats_year;
            if (period === 'month') stats = this.state.stats_month;
            if (period === 'day') stats = this.state.stats_day;
            this.state.generated = stats.generated || 0;
            this.state.paid = stats.paid || 0;
        }
        this.renderEmployeeCostChart();
        this.renderPayrollPieChart();
    }

    // ================= EMPLOYEE COST CHART =================
    renderEmployeeCostChart() {
        let labels = this.state.employee_cost_year_labels;
        let data = this.state.employee_cost_year_data;

        if (this.state.dashboard_period === 'month') {
            labels = this.state.employee_cost_month_labels;
            data = this.state.employee_cost_month_data;
        }
        else if (this.state.dashboard_period === 'day') {
            labels = this.state.employee_cost_day_labels;
            data = this.state.employee_cost_day_data;
        }

        if (this.employeeCostChart) {
            this.employeeCostChart.destroy();
        }
        const ctx = document.getElementById("employeeCostChart");

        const type = this.state.employee_cost_chart_type;
        const config = {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: "Net Salary",
                    data: data,
                    backgroundColor: type === "line" ? "rgba(155, 89, 182, 0.2)" : (type === 'pie' || type === 'doughnut') ? [
                        "#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6", "#1abc9c", "#34495e", "#95a5a6"
                    ] : "rgba(155, 89, 182, 0.6)",
                    borderColor: "rgba(155, 89, 182, 1)",
                    borderWidth: 1,
                    fill: type === "line",
                    borderRadius: type === "bar" ? 8 : 0,
                    tension: type === "line" ? 0.4 : 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: type === 'pie' || type === 'doughnut',
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                const value = (context.parsed && context.parsed.y !== undefined) ? context.parsed.y : context.parsed;
                                if (value !== null && value !== undefined) {
                                    label += value.toLocaleString();
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: (type === 'pie' || type === 'doughnut') ? {} : {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };

        this.employeeCostChart = new Chart(ctx, config);
    }

    openBatchList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payslip Batches",
            res_model: "employee.payslip.batch",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openEmployees() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Employees",
            res_model: "hr.employee",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Contracts",
            res_model: "hr.contract",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "open"]],
            target: "current",
        });
    }
    openPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payslips",
            res_model: "employee.payslip",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
    openPaidPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paid Payslips",
            res_model: "employee.payslip",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["state", "=", "paid"]],
        });
    }
    openBatch(ev) {
        const batchId = parseInt(ev.currentTarget.dataset.id);
        if (!batchId) {
            console.warn("Invalid batch ID:", batchId);
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payslip Batch",
            res_model: "employee.payslip.batch",
            res_id: batchId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }

    onWarningClick(ev) {
        const label = ev.currentTarget.dataset.id;
        if (!label) {
            return;
        }
        if (label === "Draft Payslips") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Draft Payslips",
                res_model: "employee.payslip",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["state", "=", "draft"]],
                target: "current",
            });
        }
        if (label === "Employees Without Running Contracts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Running Contracts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["contract_id", "=", false]],
                target: "current",
            });
        }
        if (label === "Employees With Both New And Running Contracts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees With Both New And Running Contracts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [
                    ["contract_ids.state", "=", "open"],
                    ["contract_ids.state", "=", "draft"],
                ],
                target: "current",
            });
        }
        if (label === "Employees Without Bank Accounts") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Bank Accounts",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["bank_account_id", "=", false]],
                target: "current",
            });
        }
        if (label === "Nearly Expired Contracts (Next 30 Days)") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Nearly Expired Contracts",
                res_model: "hr.contract",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [
                    ["state", "=", "open"],
                    ["date_end", "!=", false],
                    ["date_end", ">=", moment().format("YYYY-MM-DD")],
                    ["date_end", "<=", moment().add(30, "days").format("YYYY-MM-DD")],
                ],
                target: "current",
            });
        }
        if (label === "Employees Without Identification Number") {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Employees Without Identification Number",
                res_model: "hr.employee",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                domain: [["identification_id", "=", false]],
                target: "current",
            });
        }

    }


    // ================= PAYROLL PIE =================
    renderPayrollPieChart() {

        if (this.payrollPieChart) {
            this.payrollPieChart.destroy();
        }

        const chartEl = document.getElementById("payrollPieChart");

        let labels = this.state.payroll_dist_year_labels;
        let data = this.state.payroll_dist_year_data;

        if (this.state.dashboard_period === 'month') {
            labels = this.state.payroll_dist_month_labels;
            data = this.state.payroll_dist_month_data;
        } else if (this.state.dashboard_period === 'day') {
            labels = this.state.payroll_dist_day_labels;
            data = this.state.payroll_dist_day_data;
        }

        const type = this.state.payroll_dist_chart_type;

        // Common click handler logic
        const clickHandler = (evt, elements) => {
            if (elements.length > 0) {
                const index = elements[0].index;
                let typeIds = this.state.payroll_dist_year_type_ids;

                if (this.state.dashboard_period === 'month') {
                    typeIds = this.state.payroll_dist_month_type_ids;
                } else if (this.state.dashboard_period === 'day') {
                    typeIds = this.state.payroll_dist_day_type_ids;
                }

                const typeId = typeIds[index];
                this.openStructureType(typeId);
            }
        };

        const config = {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: "Amount",
                    data: data,
                    backgroundColor: [
                        "#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6",
                        "#1abc9c", "#34495e", "#95a5a6", "#d35400", "#bdc3c7"
                    ],
                    // Bar/Line specific
                    borderColor: type === 'line' ? "#3498db" : undefined,
                    fill: type === 'line',
                    tension: type === 'line' ? 0.4 : 0,
                    borderRadius: type === 'bar' ? 6 : 0,
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                // ✅ CLICK ACTION
                onClick: clickHandler,

                plugins: {
                    legend: {
                        position: "bottom",
                        display: type === 'pie' || type === 'doughnut',
                    },
                    tooltip: {
                        enabled: true,
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                const value = (context.parsed && context.parsed.y !== undefined) ? context.parsed.y : context.parsed;
                                if (value !== null && value !== undefined) {
                                    if (type === 'bar' || type === 'line') {
                                        if (label) label += ': ';
                                        label += value.toLocaleString();
                                    } else {
                                        // Pie/Doughnut
                                        if (context.label) label = context.label + ': ';
                                        label += value.toLocaleString();
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: (type === 'pie' || type === 'doughnut') ? {} : {
                    y: { beginAtZero: true }
                }
            }
        };

        this.payrollPieChart = new Chart(chartEl, config);
    }

    openStructureType(typeId) {
        if (!typeId) return;

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Salary Structures",
            res_model: "hr.payroll.structure",
            domain: [['struct_type_id', '=', typeId]],
            views: [[false, "tree"], [false, "form"]],
            view_mode: "tree,form",
            target: "current",
        });
    }
}

// ================= TEMPLATE =================

PayrollDashboard.template = "cyllo_payroll_management.PayrollDashboard"
registry.category("actions").add(
    "hr_payroll_dashboard",
    PayrollDashboard
);
