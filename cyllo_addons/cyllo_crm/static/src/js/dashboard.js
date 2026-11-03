/** @odoo-module **/

import {Component, useState, onMounted, useRef, useEffect} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {formatCurrency} from "@web/core/currency";

// Options shown in the Date Range checkbox dropdown (same design as the
// Sales Team / Sales Persons dropdowns)
const DATE_RANGE_OPTIONS = [
    {value: "today", label: "Today"},
    {value: "this_week", label: "This Week"},
    {value: "this_month", label: "This Month"},
    {value: "this_quarter", label: "This Quarter"},
    {value: "this_year", label: "This Year"},
    {value: "custom", label: "Custom Range"},
];

export class CRMDashboard extends Component {
    static template = "crm_dashboard.crm_dashboard_template";

    get dateRangeOptions() {
        return DATE_RANGE_OPTIONS;
    }

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
                salesTeams: [],
                salesPersons: [],
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
            // Body only renders once the first data fetch has finished —
            // cards don't flash "empty state → real data" on page load
            hasLoaded: false,
            // Bumped on every data refresh; drives the post-render chart init
            dataTick: 0,
            showAllNotifications: false,
            // Staged filter selections — only "Apply" commits these
            // into state.filters and re-renders the dashboard.
            filterDraft: {
                dateRange: "this_month",
                dateFrom: "",
                dateTo: "",
                salesTeams: [],
                salesPersons: [],
            },
            openDropdown: null,
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

        // Charts are (re)created AFTER the DOM renders the dashboard body:
        // the canvas refs only exist once hasLoaded is true, and after every
        // data refresh (apply filter, refresh button)
        useEffect(
            () => {
                if (this.state.hasLoaded) {
                    this.initializeCharts();
                }
            },
            () => [this.state.hasLoaded, this.state.dataTick]
        );

        onMounted(() => {
            this.loadInitialData();
            // Close the checkbox dropdowns when clicking outside the popover
            this._onClickOutsideFilters = (ev) => {
                if (!ev.target.closest(".cy-dropdown")) {
                    this.state.openDropdown = null;
                }
                // Clicking anywhere outside the filter popover (and the
                // Filter button itself) closes the popover entirely
                if (this.state.showFilters
                        && !ev.target.closest(".filters-content")
                        && !ev.target.closest(".cy-dash-filter-btn")) {
                    this.state.showFilters = false;
                    this.state.openDropdown = null;
                }
            };
            document.addEventListener("click", this._onClickOutsideFilters);
        });
    }

    onToggleFilters() {
        this.state.showFilters = !this.state.showFilters;
        if (this.state.showFilters) {
            // Path responds to committed filters; staging starts from those
            Object.assign(this.state.filterDraft, this.state.filters);
        }
        this.state.openDropdown = null;
    }

    toggleFilterDropdown(name) {
        this.state.openDropdown = this.state.openDropdown === name ? null : name;
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
                this.state.filters.salesTeams = [Number(context.current_team_id)];
            }
            if (this.state.hideSalespersonFilter && context.current_user_id) {
                this.state.filters.salesPersons = [Number(context.current_user_id)];
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
        // Note: charts are initialized by the useEffect that runs after the
        // dashboard body renders (see setup()) — refs don't exist before that
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
                {month: "Jan", revenue: 65000, leads: 120, previous_year: 45000},
                {month: "Feb", revenue: 59000, leads: 98, previous_year: 38000},
                {month: "Mar", revenue: 80000, leads: 145, previous_year: 52000},
                {month: "Apr", revenue: 81000, leads: 167, previous_year: 60000},
                {month: "May", revenue: 95000, leads: 189, previous_year: 72000},
                {month: "Jun", revenue: 88000, leads: 156, previous_year: 64000},
            ],
            pipeline: [
                {stage: "New", value: 50, count: 75, color: "#4C5814"},
                {stage: "Proposition", value: 26.7, count: 40, color: "#7E8C2F"},
                {stage: "Won", value: 6.7, count: 10, color: "#A9B85A"},
                {stage: "Qualified", value: 13.7, count: 21, color: "#D3C91F"},
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
        // Mark the body ready + bump the tick so the post-render effect
        // re-creates the charts for this dataset
        this.state.hasLoaded = true;
        this.state.dataTick = (this.state.dataTick || 0) + 1;

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
                unit: "",
            },
            {
                type: "leads",
                label: "Active Leads",
                value: data.metrics.active_leads.value,
                formatted_value: this.formatNumber(data.metrics.active_leads.value),
                change: data.metrics.active_leads.change,
                records: data.metrics.active_leads.records || [],
                icon: "ri-group-line",
                unit: "Units",
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
                unit: "Deals",
            },
        ];

        // Update other data
        this.state.revenueData = data.revenue_trend;
        this.state.pipeline = data.pipeline;
        this.state.activities = data.activities;

        // Empty-dataset flags — drive the grey "No data available" overlays
        // in the chart containers (see .cy-chart-empty in the template)
        this.state.trendEmpty = !data.revenue_trend
            || !data.revenue_trend.length
            || data.revenue_trend.every((d) => !d.leads && !d.revenue);
        this.state.activitiesEmpty = !data.activities
            || !data.activities.length;

        // HTML legend for the Activities Overview card (mirrors chart datasets)
        const activityTypeNames = Array.from(
            new Set((data.activities || []).map((a) => a.name))
        );
        this.state.activityLegend = activityTypeNames.map((name, index) => ({
            name,
            color: this.generateColor(index, Math.max(activityTypeNames.length, 8)).border,
        }));

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

    themeColor(name, fallback) {
        // Resolve a CSS variable (defined in dashboard_style.css) at runtime
        // so canvas colors stay in sync with the dashboard theme
        const val = getComputedStyle(document.documentElement)
            .getPropertyValue(name)
            .trim();
        return val || fallback;
    }

    createRevenueChart() {
        const ctx = this.revenueChartRef.el.getContext("2d");
        const data = this.state.revenueData;

        // Greyed-out look when the period has no data at all — an opaque
        // "No data available" overlay (.cy-chart-empty) sits on top of it.
        const trendEmpty = this.state.trendEmpty;
        const revColor = trendEmpty
            ? this.themeColor("--cy-line-muted", "#B9B7A8")
            : this.themeColor("--cy-line-dark", "#4C5814");
        const leadColor = trendEmpty
            ? this.themeColor("--cy-gray-light", "#BEC0B2")
            : this.themeColor("--cy-line-lead", "#D3C91F");

        this.charts.revenue = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map((d) => d.month),
                datasets: [
                    {
                        label: "Revenue",
                        data: data.map((d) => d.revenue),
                        borderColor: revColor,
                        backgroundColor: this.themeColor(
                            "--cy-accent-fill",
                            "rgba(126, 140, 47, 0.12)"
                        ),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4,
                        pointBackgroundColor: revColor,
                        yAxisID: "y1",
                    },
                    {
                        label: "Lead",
                        data: data.map((d) => d.leads),
                        borderColor: leadColor,
                        backgroundColor: "transparent",
                        borderWidth: 2,
                        borderDash: [],
                        fill: false,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4,
                        pointBackgroundColor: leadColor,
                        yAxisID: "y",
                    },
                    {
                        label: "Previous year",
                        data: data.map((d) =>
                            d.previous_year != null
                                ? d.previous_year
                                : Math.round(d.revenue * 0.6)
                        ),
                        borderColor: this.themeColor("--cy-line-muted", "#B9B7A8"),
                        backgroundColor: "transparent",
                        borderWidth: 1.5,
                        borderDash: [3, 3],
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        pointBackgroundColor: this.themeColor(
                            "--cy-line-muted",
                            "#B9B7A8"
                        ),
                        yAxisID: "y1",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    // Inset the plot inside the rounded track (canvas now fills
                    // .chart-container edge to edge — no CSS padding)
                    padding: {top: 16, right: 22, bottom: 8, left: 12},
                },
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                scales: {
                    x: {
                        grid: {
                            display: true,
                            color: this.themeColor("--cy-grid-line", "#F0EFE8"),
                            borderDash: [3, 5],
                            drawTicks: false,
                        },
                        border: {
                            display: false,
                        },
                        ticks: {
                            color: this.themeColor("--cy-tick", "#9A9A8C"),
                            font: {size: 11},
                        },
                    },
                    y: {
                        type: "linear",
                        display: true,
                        position: "left",
                        title: {
                            display: true,
                            text: "Leads",
                            color: this.themeColor("--cy-muted", "#8B8B7E"),
                            font: {size: 11, weight: 500},
                        },
                        border: {
                            display: false,
                        },
                        grid: {
                            color: this.themeColor("--cy-grid-line", "#F0EFE8"),
                            borderDash: [3, 5],
                            drawTicks: false,
                        },
                        ticks: {
                            color: this.themeColor("--cy-tick-lead", "#9FA32E"),
                            font: {size: 11},
                        },
                    },
                    y1: {
                        type: "linear",
                        display: true,
                        position: "right",
                        title: {
                            display: true,
                            text: "Revenue ($)",
                            color: this.themeColor("--cy-muted", "#8B8B7E"),
                            font: {size: 11, weight: 500},
                        },
                        grid: {
                            drawOnChartArea: false,
                            border: {
                                display: false,
                            },
                        },
                        ticks: {
                            color: this.themeColor("--cy-tick", "#9A9A8C"),
                            font: {size: 11},
                        },
                    },
                },
                plugins: {
                    legend: {
                        // HTML legend below the title (see .cy-series-legend)
                        display: false,
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
        const self = this;
        const totalDeals = data.reduce((sum, d) => sum + (d.count || 0), 0);

        const centerText = {
            id: "pipelineCenterText",
            afterDraw(chart) {
                const {ctx} = chart;
                // With no deals the doughnut renders no arc — fall back to
                // the chart-area center and still show the total (0).
                let cx, cy;
                const meta = chart.getDatasetMeta(0);
                if (meta.data.length) {
                    cx = meta.data[0].x;
                    cy = meta.data[0].y;
                } else {
                    const area = chart.chartArea;
                    if (!area) return;
                    cx = (area.left + area.right) / 2;
                    cy = (area.top + area.bottom) / 2;
                }
                ctx.save();
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.font = "500 10px Roboto, sans-serif";
                ctx.fillStyle = self.themeColor("--cy-tick", "#9A9A8C");
                ctx.fillText("Total Deals", cx, cy - 8);
                ctx.font = "700 17px Roboto, sans-serif";
                ctx.fillStyle = self.themeColor("--cy-text", "#24241C");
                ctx.fillText(String(totalDeals), cx, cy + 9);
                ctx.restore();
            },
        };

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
            plugins: [centerText],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {top: 28, right: 28, bottom: 28, left: 28},
                },
                cutout: "62%",
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
        // Palette resolved from the CSS variables (--cy-*) defined in dashboard_style.css
        const paletteVars = [
            ["--cy-accent-light", "#A9B85A"],
            ["--cy-line-dark", "#4C5814"],
            ["--cy-accent", "#7E8C2F"],
            ["--cy-accent-pale", "#C9D49A"],
            ["--cy-accent-darker", "#48521B"],
            ["--cy-gray-soft", "#9B9E91"],
            ["--cy-gray-light", "#BEC0B2"],
            ["--cy-accent-deep", "#5C6A1E"],
        ];

        // Return color from palette, cycling if more activities than colors
        const [name, fallback] = paletteVars[index % paletteVars.length];
        const color = this.themeColor(name, fallback);
        return {
            background: color + "D9", // ~85% alpha
            border: color,
        };
    }

    // Process data for the chart (grouped by month, like the design)
    processActivityData(data) {
        const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const monthGroups = {};
        const activityTypes = new Set();
        // First pass: collect all activity types and group by month
        data.forEach((activity) => {
            const d = new Date(activity.date_deadline);
            const month = MONTHS[d.getMonth()];
            const name = activity.name;

            activityTypes.add(name);

            if (!monthGroups[month]) {
                monthGroups[month] = {};
            }
            if (!monthGroups[month][name]) {
                monthGroups[month][name] = 0;
            }
            monthGroups[month][name]++;
        });

        // Ensure all months have all activity types (with 0 if not present)
        const allActivityTypes = Array.from(activityTypes);
        Object.keys(monthGroups).forEach((month) => {
            allActivityTypes.forEach((activityType) => {
                if (!monthGroups[month][activityType]) {
                    monthGroups[month][activityType] = 0;
                }
            });
        });
        return {dateGroups: monthGroups, activityTypes: allActivityTypes};
    }

    createActivitiesChart() {
        const ctx = this.activitiesChartRef.el.getContext("2d");
        const data = this.state.activities;
        const {dateGroups, activityTypes} = this.processActivityData(data);
        const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const labels = MONTHS.filter((month) => month in dateGroups);

        // Create datasets for each activity type with dynamic colors
        const datasets = activityTypes.map((activityType, index) => {
            const colors = this.generateColor(index, activityTypes.length);
            const data = labels.map((month) => dateGroups[month][activityType] || 0);
            return {
                label: activityType,
                data: data,
                backgroundColor: colors.background,
                borderColor: colors.border,
                borderWidth: 0,
                borderRadius: 12,
                borderSkipped: false,
                categoryPercentage: 0.55,
                barPercentage: 0.8,
            };
        });
        this.charts.activities = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {top: 10, right: 6, bottom: 2, left: 2},
                },
                plugins: {
                    legend: {
                        // HTML legend below the title (see .cy-series-legend)
                        display: false,
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
                        border: {
                            display: false,
                        },
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: this.themeColor("--cy-tick", "#9A9A8C"),
                            font: {size: 11},
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Number of Activities",
                            color: this.themeColor("--cy-muted", "#8B8B7E"),
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        border: {
                            display: false,
                        },
                        grid: {
                            color: this.themeColor("--cy-grid-line", "#F0EFE8"),
                            borderDash: [3, 5],
                            drawTicks: false,
                        },
                        ticks: {
                            stepSize: 1,
                            color: this.themeColor("--cy-tick", "#9A9A8C"),
                            font: {size: 11},
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

    // Filter event handlers — staged: they only update the draft; the
    // dashboard is re-rendered only when "Apply" is clicked.
    async onDraftDateRangeOption(value) {
        const d = this.state.filterDraft;
        d.dateRange = value;
        if (value !== "custom") {
            d.dateFrom = "";
            d.dateTo = "";
        }
    }

    async onDraftSalesTeamOption(teamId) {
        const d = this.state.filterDraft;
        if (!teamId) {
            // "All Teams" clears the selection
            d.salesTeams = [];
        } else {
            // Checkbox behavior: toggle the clicked id in the selection
            const id = Number(teamId);
            d.salesTeams = d.salesTeams.includes(id)
                ? d.salesTeams.filter((x) => x !== id)
                : d.salesTeams.concat([id]);
        }
        d.salesPersons = [];
        // Refresh the persons list for the staged teams (no dashboard reload)
        await this.loadSalespersons(d.salesTeams);
    }

    onDraftSalespersonOption(personId) {
        const d = this.state.filterDraft;
        if (!personId) {
            d.salesPersons = [];
        } else {
            const id = Number(personId);
            d.salesPersons = d.salesPersons.includes(id)
                ? d.salesPersons.filter((x) => x !== id)
                : d.salesPersons.concat([id]);
        }
    }

    // Filter actions
    async onApplyFilters() {
        const d = this.state.filterDraft;
        if (d.dateRange === "custom" && (!d.dateFrom || !d.dateTo)) {
            this.notification.add("Please select both start and end dates", {
                type: "warning",
            });
            return;
        }
        Object.assign(this.state.filters, {
            dateRange: d.dateRange,
            dateFrom: d.dateFrom,
            dateTo: d.dateTo,
            salesTeams: d.salesTeams,
            salesPersons: d.salesPersons,
        });
        this.state.openDropdown = null;
        // Committing the draft closes the popover, like the outside click
        this.state.showFilters = false;
        await this.loadSalespersons();
        this.loadDashboardData();
    }

    async onResetFilters() {
        Object.assign(this.state.filters, {
            dateRange: "this_month",
            dateFrom: "",
            dateTo: "",
            salesTeams: [],
            salesPersons: [],
        });
        Object.assign(this.state.filterDraft, this.state.filters);
        this.state.openDropdown = null;
        await this.loadSalespersons();
        this.loadDashboardData();
    }

    // Individual filter clearing — clears the staged draft; "Apply" commits
    clearDateFilter() {
        this.state.filterDraft.dateRange = "this_month";
        this.state.filterDraft.dateFrom = "";
        this.state.filterDraft.dateTo = "";
    }

    async clearSalesTeamFilter() {
        this.state.filterDraft.salesTeams = [];
        this.state.filterDraft.salesPersons = [];
        await this.loadSalespersons([]);
    }

    clearSalespersonFilter() {
        this.state.filterDraft.salesPersons = [];
    }

    // Helper methods for filters
    hasActiveFilters() {
        const f = this.state.filterDraft;
        return f.dateRange !== "this_month" || f.salesTeams.length
            || f.salesPersons.length || f.dateFrom || f.dateTo;
    }

    getDateRangeLabel() {
        const labels = {
            today: "Today",
            this_week: "This Week",
            this_month: "This Month",
            this_quarter: "This Quarter",
            this_year: "This Year",
            custom: `${this.state.filterDraft.dateFrom} - ${this.state.filterDraft.dateTo}`,
        };
        return labels[this.state.filterDraft.dateRange] || "This Month";
    }

    getSalesTeamsNames() {
        return this.state.salesTeams
            .filter((t) => this.state.filterDraft.salesTeams.includes(t.id))
            .map((t) => t.name)
            .join(", ");
    }

    getSalesPersonsNames() {
        return this.state.salespersons
            .filter((p) => this.state.filterDraft.salesPersons.includes(p.id))
            .map((p) => p.name)
            .join(", ");
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

    async loadSalespersons(teamIds = this.state.filters.salesTeams) {
        try {
            if (this.state.hideSalespersonFilter) {
                this.state.salespersons = [];
                return;
            }
            let domain = [["active", "=", true]];

            const ids = (teamIds || []).map(Number).filter(Boolean);
            if (ids.length) {
                // Members from ALL selected teams (union)
                const teams = await this.orm.searchRead(
                    "crm.team",
                    [["id", "in", ids]],
                    ["member_ids"]
                );
                const members = new Set();
                teams.forEach((t) => (t.member_ids || []).forEach(
                    (m) => members.add(m)
                ));
                if (members.size > 0) {
                    domain.push(["id", "in", Array.from(members)]);
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

        // Sales team filter (multi-select)
        const teamIds = (this.state.filters.salesTeams || []).map(Number);
        if (teamIds.length) {
            domain.push(["team_id", "in", teamIds]);
        }

        // Salesperson filter (multi-select)
        const personIds = (this.state.filters.salesPersons || []).map(Number);
        if (personIds.length) {
            domain.push(["user_id", "in", personIds]);
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
            let salesWrapper = sales.closest(".cy-pipeline-track");
            const salesCanvas = await html2canvas(salesWrapper);
            const salesImage = salesCanvas.toDataURL("image/png");

            pdf.addImage(salesImage, "PNG", 10, 10, 190, 100); // x, y, width, height
            pdf.save("sales_chart.pdf");
        } else if (format === "lead") {
            const leadsCanvas = await html2canvas(leads.closest(".cy-trend-card"));
            const leadsImage = leadsCanvas.toDataURL("image/png");

            pdf.addImage(leadsImage, "PNG", 10, 10, 190, 100); // x, y, width, height
            pdf.save("leads_chart.pdf");
        } else if (format === "report") {
            // Full dashboard report: both charts in one PDF
            const revCanvas = await html2canvas(leads.closest(".cy-trend-card"));
            pdf.addImage(revCanvas.toDataURL("image/png"), "PNG", 10, 10, 190, 90);

            const salesCanvas = await html2canvas(sales.closest(".cy-pipeline-track"));
            pdf.addImage(salesCanvas.toDataURL("image/png"), "PNG", 15, 105, 90, 80);
            pdf.save("crm_dashboard_report.pdf");
        } else if (format === "activity") {
            const activitiesCanvas = await html2canvas(
                this.activitiesChartRef.el.closest(".activities-card")
            );
            pdf.addImage(activitiesCanvas.toDataURL("image/png"), "PNG", 10, 10, 190, 100);
            pdf.save("activities_chart.pdf");
        } else if (format === "performers") {
            const performersCanvas = await html2canvas(
                this.state.topPerformers?.length
                    ? document.querySelector(".cy_crm_dashboard .performers-card")
                    : this.pipelineChartRef.el
            );
            pdf.addImage(performersCanvas.toDataURL("image/png"), "PNG", 10, 10, 190, 100);
            pdf.save("top_performers.pdf");
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
        // Clean up the Outside click listener for the filter dropdowns
        if (this._onClickOutsideFilters) {
            document.removeEventListener("click",
                this._onClickOutsideFilters);
        }
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

    async onClearNotifications() {
        try {
            const leadIds = this.state.leadNotifications
                .map((n) => n.lead_id)
                .filter(Boolean);

            if (leadIds.length) {
                await this.orm.call("crm.lead", "dismiss_notification",
                    [leadIds]);
            }

            this.state.leadNotifications = [];
            this.state.showAllNotifications = false;
            await this.loadNotifications();
            this.notification.add("All notifications cleared",
                {type: "success"});
        } catch (error) {
            console.error("Error while clearing notifications:", error);
            this.notification.add("Failed to clear notifications",
                {type: "danger"});
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
            new_lead: "ri-user-add-line",
            high_value: "ri-vip-crown-line",
            lead_updated: "ri-edit-line",
            stage_changed: "ri-flag-line",
            activity_due: "ri-alarm-line",
            won: "ri-trophy-line",
            lost: "ri-close-circle-line",
            email: "ri-mail-line",
            call: "ri-phone-line",
            meeting: "ri-calendar-line",
            default: "ri-notification-3-line",
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
