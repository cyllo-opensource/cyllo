/** @odoo-module **/

import {Component, useState, onMounted, useRef, useEffect} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {formatCurrency} from "@web/core/currency";


export class CRMDashboard extends Component {
    static template = "crm_dashboard.crm_dashboard_template";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.notification = useService("notification");

        // Refs for charts
        this.revenueChartRef = useRef("revenueChart");
        this.pipelineChartRef = useRef("pipelineChart");
        this.activitiesChartRef = useRef("activitiesChart");
        this.crmDashboardChartGrids = useRef("crmDashboardChartGrids");

        // State management
        this.state = useState({
            metrics: [],
            filters: {
                dateRange: "this_month",
                dateFrom: "",
                dateTo: "",
                salesTeam: "",
                salesperson: "",
            },
            hideSalespersonFilter: false,
            salesTeams: [],
            salespersons: [],
            revenueData: [],
            pipeline: [],
            activities: [],
            topPerformers: [],
            isLoading: true,
            isSampleData: false,
            leadNotifications: [],
            unreadVisibleCount: 0,
            showFilters: false,
            showAllNotifications: false,
        });
        this.charts = {};

        useEffect(
            () => {
                const count = this.state.leadNotifications.filter(
                    (n) => !n.is_read && !n.is_dismissed_notification
                ).length;
                this.state.unreadVisibleCount = count;
            },
            () => [this.state.leadNotifications.map((n) => n.is_read)]
        );

        onMounted(() => {
            this.loadInitialData();
        });
    }

    onToggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    onToggleNotifications() {
        this.state.showAllNotifications = !this.state.showAllNotifications;
    }

    async loadInitialData() {
        await this.loadUserContext();
        // Load sales teams and salespersons first
        await this.loadSalesTeams();
        await this.loadSalespersons();
        await this.loadCompanyData();
        // Then load dashboard data
        await this.loadDashboardData();
        await this.loadNotifications();
    }

    async loadUserContext() {
        try {
            const context = await this.orm.call(
                "crm.lead",
                "get_dashboard_user_context",
                []
            );
            this.state.hideSalespersonFilter = !!context.hide_salesperson_filter;
            if (this.state.hideSalespersonFilter && context.current_team_id) {
                this.state.filters.salesTeam = String(context.current_team_id);
            }
            if (this.state.hideSalespersonFilter && context.current_user_id) {
                this.state.filters.salesperson = String(context.current_user_id);
            }
        } catch (error) {
            console.warn("Error loading dashboard user context:", error);
        }
    }

    async loadDashboardData() {
        try {
            // Build domain based on current filters
            const domain = this.buildDomain();

            // Try to fetch real data from Odoo models
            const data = await this.orm.call("crm.lead", "get_dashboard_data", [
                domain, this.state.filters.dateRange
            ]);
            if (this.isDashboardDataEmpty(data)) {
                this.loadSampleData();
            } else {
                this.updateState(data);
            }
        } catch (error) {
            console.warn("Failed to load dashboard data, using sample data:", error);
            this.loadSampleData();
        }
        this.initializeCharts();
    }

    async loadCompanyData() {
        const companyData = await this.orm.searchRead(
            'res.company',
            [['id', '=', this.company.currentCompany?.id]],
            ['currency_id']
        );
        this.companyData = companyData[0];
    }

    isDashboardDataEmpty(data) {
        const metrics = data?.metrics || {};
        const metricValues = [
            metrics.total_revenue?.value,
            metrics.active_leads?.value,
            metrics.conversion_rate?.value,
            metrics.deals_closed?.value,
        ];
        const hasMetricValue = metricValues.some((value) => Number(value || 0) > 0);
        const hasTrendData = (data?.revenue_trend || []).some(
            (item) => Number(item.revenue || 0) > 0 || Number(item.leads || 0) > 0
        );
        const hasDashboardLists = [
            data?.pipeline,
            data?.activities,
            data?.top_performers,
        ].some((items) => Array.isArray(items) && items.length > 0);

        return !hasMetricValue && !hasTrendData && !hasDashboardLists;
    }

    loadSampleData() {
        const sampleData = {
            metrics: {
                total_revenue: {value: 468000, change: 12.5},
                active_leads: {value: 1275, change: 8.2, records: []},
                conversion_rate: {value: 24.8, change: -2.1},
                deals_closed: {value: 89, change: 15.3, records: []},
            },
            revenue_trend: [
                {month: "Jan", revenue: 65000, leads: 120},
                {month: "Feb", revenue: 59000, leads: 98},
                {month: "Mar", revenue: 80000, leads: 145},
                {month: "Apr", revenue: 81000, leads: 167},
                {month: "May", revenue: 95000, leads: 189},
                {month: "Jun", revenue: 88000, leads: 156},
            ],
            pipeline: [
                {stage: "New", value: 35, color: "#3B82F6"},
                {stage: "Qualified", value: 28, color: "#10B981"},
                {stage: "Proposal", value: 22, color: "#F59E0B"},
                {stage: "Won", value: 15, color: "#EF4444"},
            ],
            activities: [
                {day: "Mon", calls: 24, emails: 45, meetings: 8},
                {day: "Tue", calls: 28, emails: 52, meetings: 12},
                {day: "Wed", calls: 32, emails: 38, meetings: 10},
                {day: "Thu", calls: 26, emails: 41, meetings: 9},
                {day: "Fri", calls: 30, emails: 48, meetings: 15},
                {day: "Sat", calls: 18, emails: 22, meetings: 4},
                {day: "Sun", calls: 12, emails: 18, meetings: 2},
            ],
            top_performers: [
                {name: "Sarah Johnson", deals: 23, amount: 125000},
                {name: "Mike Chen", deals: 19, amount: 98000},
                {name: "Emily Davis", deals: 17, amount: 87000},
                {name: "Alex Rodriguez", deals: 15, amount: 76000},
            ],
        };

        this.updateState(sampleData, true);
    }

    onMetricClick(metric, action) {
        const recordIds = Array.isArray(metric?.records)
            ? metric.records
            : [];
        if (recordIds.length > 0) {
            return action.doAction({
                name: metric.label,
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                views: [[false, 'kanban'], [false, 'form']],
                target: 'current',
                domain: [['id', 'in', recordIds]],
            });
        }
    }

    updateState(data, isSampleData = false) {
        this.state.isSampleData = isSampleData;

        // Update metrics
        this.state.metrics = [
            {
                type: "revenue",
                label: data.metrics.total_revenue.label,
                value: data.metrics.total_revenue.value,
                formatted_value: formatCurrency(
                    data.metrics.total_revenue.value, this.companyData.currency_id[0]
                ),
                change: data.metrics.total_revenue.change,
                records: [],
                icon: "ri-money-dollar-circle-line",
            },
            {
                type: "leads",
                label: "Active Leads",
                value: data.metrics.active_leads.value,
                formatted_value: this.formatNumber(data.metrics.active_leads.value),
                change: data.metrics.active_leads.change,
                records: data.metrics.active_leads.records || [],
                icon: "ri-group-line",
            },
            {
                type: "conversion",
                label: "Conversion Rate",
                value: data.metrics.conversion_rate.value,
                formatted_value: data.metrics.conversion_rate.value + "%",
                change: data.metrics.conversion_rate.change,
                records: [],
                icon: "ri-focus-2-line",
            },
            {
                type: "deals",
                label: "Deals Closed",
                value: data.metrics.deals_closed.value,
                formatted_value: data.metrics.deals_closed.value.toString(),
                change: data.metrics.deals_closed.change,
                records: data.metrics.deals_closed.records || [],
                icon: "ri-award-line",
            },
        ];

        // Update other data
        this.state.revenueData = data.revenue_trend;
        this.state.pipeline = data.pipeline;
        this.state.activities = data.activities;

        // Format top performers
        this.state.topPerformers = data.top_performers.map((performer) => ({
            ...performer,
            initials: performer.name
                .split(" ")
                .map((n) => n[0])
                .join(""),
            formatted_amount: formatCurrency(performer.amount, this.companyData.currency_id[0]),
        }));

        this.state.isLoading = false;
    }

    initializeCharts() {
        // Destroy existing charts
        Object.values(this.charts).forEach((chart) => chart?.destroy());

        this.createRevenueChart();
        this.createPipelineChart();
        this.createActivitiesChart();
    }

    createRevenueChart() {
        const ctx = this.revenueChartRef.el.getContext("2d");
        const data = this.state.revenueData;

        this.charts.revenue = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map((d) => d.month),
                datasets: [
                    {
                        label: "Revenue",
                        data: data.map((d) => d.revenue),
                        borderColor: "#3B82F6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        yAxisID: "y",
                    },
                    {
                        label: "Leads",
                        data: data.map((d) => d.leads),
                        borderColor: "#10B981",
                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4,
                        yAxisID: "y1",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                scales: {
                    y: {
                        type: "linear",
                        display: true,
                        position: "left",
                        title: {
                            display: true,
                            text: "Revenue ($)",
                        },
                    },
                    y1: {
                        type: "linear",
                        display: true,
                        position: "right",
                        title: {
                            display: true,
                            text: "Leads",
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                },
                plugins: {
                    legend: {
                        display: true,
                        position: "top",
                    },
                    tooltip: {
                        mode: "index",
                        intersect: false,
                    },
                },
            },
        });
    }

    createPipelineChart() {
        const ctx = this.pipelineChartRef.el.getContext("2d");
        const data = this.state.pipeline;

        this.charts.pipeline = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map((d) => d.stage),
                datasets: [
                    {
                        data: data.map((d) => d.value),
                        backgroundColor: data.map((d) => d.color),
                        borderWidth: 0,
                        hoverOffset: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "60%",
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.label + ": " + context.parsed + "%";
                            },
                        },
                    },
                },
            },
        });
    }

    // Generate colors dynamically for activity types matching the dashboard theme
    generateColor(index, total) {
        // Predefined colors matching the dashboard design
        const dashboardColors = [
            {background: "rgba(239, 68, 68, 0.85)", border: "rgba(239, 68, 68, 1)"}, // Red (Call)
            {background: "rgba(34, 197, 94, 0.85)", border: "rgba(34, 197, 94, 1)"}, // Green (Email)
            {
                background: "rgba(59, 130, 246, 0.85)",
                border: "rgba(59, 130, 246, 1)",
            }, // Blue
            {
                background: "rgba(249, 115, 22, 0.85)",
                border: "rgba(249, 115, 22, 1)",
            }, // Orange
            {
                background: "rgba(168, 85, 247, 0.85)",
                border: "rgba(168, 85, 247, 1)",
            }, // Purple
            {
                background: "rgba(236, 72, 153, 0.85)",
                border: "rgba(236, 72, 153, 1)",
            }, // Pink
            {
                background: "rgba(14, 165, 233, 0.85)",
                border: "rgba(14, 165, 233, 1)",
            }, // Sky Blue
            {
                background: "rgba(132, 204, 22, 0.85)",
                border: "rgba(132, 204, 22, 1)",
            }, // Lime
        ];

        // Return color from predefined set, cycling if more activities than colors
        return dashboardColors[index % dashboardColors.length];
    }

    // Process data for the chart
    processActivityData(data) {
        const dateGroups = {};
        const activityTypes = new Set();
        // First pass: collect all activity types and group by date
        data.forEach((activity) => {
            const deadline = activity.date_deadline;
            const name = activity.name;

            activityTypes.add(name);

            if (!dateGroups[deadline]) {
                dateGroups[deadline] = {};
            }
            if (!dateGroups[deadline][name]) {
                dateGroups[deadline][name] = 0;
            }
            dateGroups[deadline][name]++;
        });

        // Ensure all dates have all activity types (with 0 if not present)
        const allActivityTypes = Array.from(activityTypes);
        Object.keys(dateGroups).forEach((date) => {
            allActivityTypes.forEach((activityType) => {
                if (!dateGroups[date][activityType]) {
                    dateGroups[date][activityType] = 0;
                }
            });
        });
        return {dateGroups: dateGroups, activityTypes: allActivityTypes};
    }

    createActivitiesChart() {
        const ctx = this.activitiesChartRef.el.getContext("2d");
        const data = this.state.activities;
        const {dateGroups, activityTypes} = this.processActivityData(data);
        const dates = Object.keys(dateGroups).sort();

        // Format dates for display
        const formattedDates = dates.map((date) => {
            const d = new Date(date);
            return d.toLocaleDateString("en-us", {month: "short", day: "numeric"});
        });

        // Create datasets for each activity type with dynamic colors
        const datasets = activityTypes.map((activityType, index) => {
            const colors = this.generateColor(index, activityTypes.length);
            const data = dates.map((date) => dateGroups[date][activityType] || 0);
            return {
                label: activityType,
                data: data,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
            };
        });
        this.charts.activities = new Chart(ctx, {
            type: "bar",
            data: {
                labels: formattedDates,
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                        },
                    },
                    tooltip: {
                        mode: "index",
                        intersect: false,
                        backgroundColor: "rgba(0,0,0,0.8)",
                        titleColor: "#fff",
                        bodyColor: "#fff",
                        borderColor: "#ddd",
                        borderWidth: 1,
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Date",
                            font: {
                                weight: "bold",
                            },
                        },
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Number of Activities",
                            font: {
                                weight: "bold",
                            },
                        },
                        grid: {
                            color: "rgba(0,0,0,0.1)",
                        },
                        ticks: {
                            stepSize: 1,
                        },
                    },
                },
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                animation: {
                    duration: 1500,
                    easing: "easeInOutQuart",
                },
            },
        });
    }

    async onViewReportsClick() {
        await this.action.doAction({
            name: "CRM Analysis",
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [
                [false, "graph"],
                [false, "pivot"],
            ],
            context: {
                group_by: ["stage_id", "user_id"],
                graph_measure: "expected_revenue",
            },
        });
    }

    // Filter event handlers
    onDateRangeChange(ev) {
        this.state.filters.dateRange = ev.target.value;
        if (ev.target.value !== "custom") {
            this.state.filters.dateFrom = "";
            this.state.filters.dateTo = "";
            this.loadDashboardData();
        }
    }

    onCustomDateChange() {
        if (this.state.filters.dateFrom && this.state.filters.dateTo) {
            this.loadDashboardData();
        }
    }

    async onSalesTeamChange(ev) {
        this.state.filters.salesTeam = ev.target.value;
        this.state.filters.salesperson = ""; // Reset salesperson
        await this.loadSalespersons();
        this.loadDashboardData();
    }

    onSalespersonChange(ev) {
        this.state.filters.salesperson = ev.target.value;
        this.loadDashboardData();
    }

    // Filter actions
    onApplyFilters() {
        if (this.state.filters.dateRange === "custom") {
            if (!this.state.filters.dateFrom || !this.state.filters.dateTo) {
                this.notification.add("Please select both start and end dates", {
                    type: "warning",
                });
                return;
            }
        }
        this.loadDashboardData();
    }

    async onResetFilters() {
        Object.assign(this.state.filters, {
            dateRange: "this_month",
            dateFrom: "",
            dateTo: "",
            salesTeam: "",
            salesperson: "",
        });
        await this.loadSalespersons();
        this.loadDashboardData();
    }

    // Individual filter clearing
    clearDateFilter() {
        this.state.filters.dateRange = "this_month";
        this.state.filters.dateFrom = "";
        this.state.filters.dateTo = "";
        this.loadDashboardData();
    }

    async clearSalesTeamFilter() {
        this.state.filters.salesTeam = "";
        this.state.filters.salesperson = "";
        await this.loadSalespersons();
        this.loadDashboardData();
    }

    clearSalespersonFilter() {
        this.state.filters.salesperson = "";
        this.loadDashboardData();
    }

    // Helper methods for filters
    hasActiveFilters() {
        const f = this.state.filters;
        return f.dateRange !== "this_month" || f.salesTeam || f.salesperson;
    }

    getDateRangeLabel() {
        const labels = {
            today: "Today",
            this_week: "This Week",
            this_month: "This Month",
            this_quarter: "This Quarter",
            this_year: "This Year",
            custom: `${this.state.filters.dateFrom} - ${this.state.filters.dateTo}`,
        };
        return labels[this.state.filters.dateRange] || "This Month";
    }

    getSalesTeamName() {
        const team = this.state.salesTeams.find(
            (t) => t.id == this.state.filters.salesTeam
        );
        return team ? team.name : "";
    }

    getSalespersonName() {
        const person = this.state.salespersons.find(
            (p) => p.id == this.state.filters.salesperson
        );
        return person ? person.name : "";
    }

    // Data loading methods
    async loadSalesTeams() {
        try {
            const teams = await this.orm.searchRead(
                "crm.team",
                [["active", "=", true]],
                ["id", "name"],
                {order: "name"}
            );
            this.state.salesTeams = teams;
        } catch (error) {
            console.error("Error loading sales teams:", error);
            this.state.salesTeams = [];
        }
    }

    async loadSalespersons() {
        try {
            if (this.state.hideSalespersonFilter) {
                this.state.salespersons = [];
                return;
            }
            let domain = [["active", "=", true]];

            if (this.state.filters.salesTeam) {
                // Get users from selected team
                const teamUsers = await this.orm.searchRead(
                    "crm.team",
                    [["id", "=", parseInt(this.state.filters.salesTeam)]],
                    ["member_ids"]
                );
                if (teamUsers.length > 0 && teamUsers[0].member_ids.length > 0) {
                    domain.push(["id", "in", teamUsers[0].member_ids]);
                }
            }

            const users = await this.orm.searchRead(
                "res.users",
                domain,
                ["id", "name"],
                {order: "name"}
            );
            this.state.salespersons = users;
        } catch (error) {
            console.error("Error loading salespersons:", error);
            this.state.salespersons = [];
        }
    }

    buildDomain() {
        let domain = [];

        // Date filter
        const dateRange = this.getDateRange();
        if (dateRange.start && dateRange.end) {
            domain.push(["create_date", ">=", dateRange.start]);
            domain.push(["create_date", "<=", dateRange.end]);
        }

        // Sales team filter
        if (this.state.filters.salesTeam) {
            domain.push(["team_id", "=", parseInt(this.state.filters.salesTeam)]);
        }

        // Salesperson filter
        if (this.state.filters.salesperson) {
            domain.push(["user_id", "=", parseInt(this.state.filters.salesperson)]);
        }

        return domain;
    }

    getDateRange() {
        const today = new Date();
        let start, end;

        switch (this.state.filters.dateRange) {
            case "today":
                start = new Date(today.setHours(0, 0, 0, 0));
                end = new Date(today.setHours(23, 59, 59, 999));
                break;

            case "this_week":
                const startOfWeek = new Date(today);
                const endOfWeek = new Date(today);
                startOfWeek.setDate(today.getDate() - today.getDay());
                endOfWeek.setDate((today.getDate() - today.getDay()) + 6);
                start = new Date(startOfWeek.setHours(0, 0, 0, 0));
                end = new Date(endOfWeek.setHours(23, 59, 59, 999));
                break;

            case "this_month":
                start = new Date(today.getFullYear(), today.getMonth(), 1);
                end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;

            case "this_quarter":
                const quarter = Math.floor(today.getMonth() / 3);
                start = new Date(today.getFullYear(), quarter * 3, 1);
                end = new Date(today.getFullYear(), quarter * 3 + 3, 0);
                break;

            case "this_year":
                start = new Date(today.getFullYear(), 0, 1);
                end = new Date(today.getFullYear(), 11, 31);
                break;

            case "last_month":
                start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                end = new Date(today.getFullYear(), today.getMonth(), 0);
                break;

            case "custom":
                start = this.state.filters.dateFrom
                    ? new Date(this.state.filters.dateFrom)
                    : null;
                end = this.state.filters.dateTo
                    ? new Date(this.state.filters.dateTo)
                    : null;
                break;

            default:
                start = new Date(today.getFullYear(), today.getMonth(), 1);
                end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        }

        return {
            start: start ? start.toISOString().split("T")[0] + " 00:00:00" : null,
            end: end ? end.toISOString().split("T")[0] + " 23:59:59" : null,
        };
    }

    // Utility methods
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + "M";
        } else if (num >= 1000) {
            return (num / 1000).toFixed(0) + "K";
        }
        return num.toString();
    }

    // Chart export
    async exportData(format) {
        const {jsPDF} = window.jspdf;
        let leads = this.revenueChartRef.el;
        let sales = this.pipelineChartRef.el;

        const pdf = new jsPDF(); // Create a new PDF

        if (format === "sale") {
            let salesWrapper = sales.closest("#salesChartWrapper");
            const salesCanvas = await html2canvas(salesWrapper);
            const salesImage = salesCanvas.toDataURL("image/png");

            pdf.addImage(salesImage, "PNG", 10, 10, 190, 100); // x, y, width, height
            pdf.save("sales_chart.pdf");
        } else if (format === "lead") {
            const leadsCanvas = await html2canvas(leads);
            const leadsImage = leadsCanvas.toDataURL("image/png");

            pdf.addImage(leadsImage, "PNG", 10, 10, 190, 100); // x, y, width, height
            pdf.save("leads_chart.pdf");
        }
    }

    // Refresh method
    async refresh() {
        this.state.isLoading = true;
        await this.loadDashboardData();
    }

    willUnmount() {
        // Clean up charts
        Object.values(this.charts).forEach((chart) => chart?.destroy());
    }

    getNotificationIconClass(type) {
        const classes = {
            new_lead: "notification-icon-new",
            lead_updated: "notification-icon-updated",
            stage_changed: "notification-icon-stage",
            activity_due: "notification-icon-activity",
            won: "notification-icon-won",
            lost: "notification-icon-lost",
            email: "notification-icon-email",
            call: "notification-icon-call",
            meeting: "notification-icon-meeting",
            default: "notification-icon-default",
        };

        return classes[type] || classes.default;
    }

    onToggleNotifications() {
        this.state.showAllNotifications = !this.state.showAllNotifications;
    }

    onNotificationClick(ev) {
        const notificationId = ev.currentTarget.dataset.id;
        const notification = this.state.leadNotifications.find(
            (n) => n.id == notificationId
        );
        if (notification && !notification.is_read) {
            this.onMarkNotificationRead(ev);
        }
    }

    async onViewLead(ev) {
        const leadId = parseInt(ev.currentTarget.dataset.leadId);
        if (leadId) {
            try {
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "crm.lead",
                    res_id: leadId,
                    views: [[false, "form"]],
                    target: "current",
                });
            } catch (error) {
                console.error("Error opening lead:", error);
                this.notification.add("Failed to open lead", {type: "danger"});
            }
        }
    }

    async onMarkNotificationRead(ev) {
        ev.preventDefault();

        const clickedElement = ev.currentTarget;
        if (!clickedElement) {
            console.error("Event target is null");
            this.notification.add("Failed to mark as read", {type: "danger"});
            return;
        }

        const rawId = clickedElement.dataset?.id;
        if (!rawId) {
            console.error("No dataset.id found on event target:", clickedElement);
            this.notification.add("Failed to mark as read: Missing ID", {
                type: "danger",
            });
            return;
        }

        const matchedNotification = this.state.leadNotifications.find(
            (n) => n.id === rawId
        );
        if (!matchedNotification) {
            console.error("No matching notification found for ID:", rawId);
            this.notification.add("Failed to mark as read: Invalid notification", {
                type: "danger",
            });
            return;
        }

        const leadId = matchedNotification.lead_id;

        try {
            await this.orm.call("crm.lead", "mark_as_read", [[leadId]]);

            // ✅ Update frontend state
            this.state.leadNotifications = this.state.leadNotifications.map((n) =>
                n.lead_id === leadId ? {...n, is_read: true} : n
            );

            this.notification.add("Marked as read", {type: "success"});
        } catch (error) {
            console.error("Error marking as read:", error);
            this.notification.add("Failed to mark as read", {type: "danger"});
        }
    }

    async onDismissNotification(ev) {
        ev.preventDefault();

        const clickedElement = ev.currentTarget;
        if (!clickedElement) {
            console.error("Event target is null");
            this.notification.add("Failed to dismiss notification", {
                type: "danger",
            });
            return;
        }

        const rawId = clickedElement.dataset?.id;
        if (!rawId) {
            console.error("No dataset.id found on event target:", clickedElement);
            this.notification.add("Failed to dismiss notification: Missing ID", {
                type: "danger",
            });
            return;
        }

        const matchedNotification = this.state.leadNotifications.find(
            (n) => n.id === rawId
        );
        if (!matchedNotification) {
            console.error("No matching notification found for ID:", rawId);
            this.notification.add(
                "Failed to dismiss notification: Invalid notification",
                {type: "danger"}
            );
            return;
        }

        const leadId = matchedNotification.lead_id;

        let notificationElement =
            clickedElement.closest(
                ".o_notification, .notification, .notification-item, .notification-wrapper"
            ) || clickedElement.parentElement;

        try {
            // Remove DOM element
            if (notificationElement) {
            }

            // Debug before filtering
            this.state.leadNotifications.forEach((n) => {
            });

            this.state.leadNotifications = this.state.leadNotifications.filter(
                (n) => n.lead_id !== leadId
            );

            // Call server to mark notification as dismissed
            await this.orm.call("crm.lead", "dismiss_notification", [[leadId]]);
            this.notification.add("Notification dismissed", {type: "success"});
        } catch (error) {
            console.error("Error while dismissing notification:", error);
            this.notification.add("Failed to dismiss notification", {
                type: "danger",
            });
        }
    }

    getNotificationClass(notification) {
        let classes = ["notification-item"];

        if (!notification.is_read) {
            classes.push("unread");
        }

        if (notification.priority) {
            classes.push(`priority-${notification.priority}`);
        }

        if (notification.type) {
            classes.push(`notification-type-${notification.type}`);
        }

        return classes.join(" ");
    }

    getNotificationIcon(type) {
        const icons = {
            new_lead: "fa fa-user-plus",
            lead_updated: "fa fa-edit",
            stage_changed: "fa fa-flag",
            activity_due: "fa fa-clock",
            won: "fa fa-trophy",
            lost: "fa fa-times-circle",
            email: "fa fa-envelope",
            call: "fa fa-phone",
            meeting: "fa fa-calendar",
            default: "fa fa-bell",
        };

        return icons[type] || icons.default;
    }

    formatNotificationTime(dateString) {
        if (!dateString) return "";

        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) {
            return "Just now";
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours > 1 ? "s" : ""} ago`;
        } else if (diffInSeconds < 604800) {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} day${days > 1 ? "s" : ""} ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    // Update your loadNotifications method to handle sample data when real data fails:
    async loadNotifications() {
        try {
            const data = await this.orm.call("crm.lead", "get_notifications", []);
            this.state.leadNotifications = data || [];
        } catch (error) {
            console.warn("Failed to load notifications, using sample data:", error);
            //         Sample notification data for testing
            this.state.leadNotifications = [
                {
                    id: 1,
                    title: "New Lead Created",
                    message: "A new lead has been created and needs attention",
                    type: "new_lead",
                    priority: "high",
                    is_read: false,
                    create_date: new Date().toISOString(),
                    lead_id: 1,
                    lead_name: "John Doe",
                    lead_company: "ABC Corp",
                    lead_stage: "New",
                    lead_expected_revenue: "$5,000",
                },
                {
                    id: 2,
                    title: "Lead Stage Changed",
                    message: "Lead moved to Qualified stage",
                    type: "stage_changed",
                    priority: "normal",
                    is_read: false,
                    create_date: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
                    lead_id: 2,
                    lead_name: "Jane Smith",
                    lead_company: "XYZ Inc",
                    lead_stage: "Qualified",
                    lead_expected_revenue: "$10,000",
                },
                {
                    id: 3,
                    title: "Activity Due",
                    message: "Follow-up call is due today",
                    type: "activity_due",
                    priority: "high",
                    is_read: true,
                    create_date: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
                    lead_id: 3,
                    lead_name: "Bob Johnson",
                    lead_company: "Tech Solutions",
                    lead_stage: "Proposal",
                    lead_expected_revenue: "$15,000",
                },
            ];
        }
    }
}

// Register the component
registry.category("actions").add("crm_dashboard", CRMDashboard);
