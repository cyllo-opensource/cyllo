/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class GreenMetricsDashboard extends Component {
    setup() {
        this.user = useService("user");
        this.orm = useService("orm");
        this.action = useService("action");
        this.gasChartRef = useRef("gasChart");
        this.scopeChartRef = useRef("scopeChart");
        this.targetChartRef = useRef("targetChart");
        this.airTrendChartRef = useRef("airTrendChart");
        this.soundChartRef = useRef("soundChart");
        this.waterChartRef = useRef("waterChart");
        
        this.state = useState({ 
            dashboardData: {},
            waterDateFilter: 'yearly',
            waterScopeFilter: ['all'],
            waterStartDate: '',
            waterEndDate: '',
        });
        this.gasChart = null;
        this.scopeChart = null;
        this.targetChart = null;
        this.airTrendChart = null;
        this.soundChart = null;
        this.waterChart = null;

        onWillStart(async () => {
            this.state.canCreateProject = await this.user.hasGroup('project.group_project_user');
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (e) {
                try {
                    await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
                } catch (e2) {
                    console.error("Failed to load Chart.js");
                }
            }
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadData() {
        // Prepare scope filter for backend (comma separated string)
        const scopeFilterStr = Array.isArray(this.state.waterScopeFilter) ? this.state.waterScopeFilter.join(',') : this.state.waterScopeFilter;
        
        this.state.dashboardData = await this.orm.call(
            "carbon.activity", 
            "get_dashboard_data", 
            [],
            {
                water_date_filter: this.state.waterDateFilter,
                water_scope_filter: scopeFilterStr,
                water_start_date: this.state.waterStartDate,
                water_end_date: this.state.waterEndDate
            }
        );
        if (this.state.dashboardData) {
            this.renderCharts();
        }
    }

    async onWaterDateFilterChange(ev) {
        this.state.waterDateFilter = ev.target.value;
        await this.loadData();
    }

    async onWaterDateRangeChange() {
        if (this.state.waterStartDate && this.state.waterEndDate) {
            await this.loadData();
        }
    }

    createInitiative(projectType = 'green') {
        if (!this.state.canCreateProject) return;
        let projectData = this.state.dashboardData?.projects;
        if (projectType === 'water') projectData = this.state.dashboardData?.water_projects;
        if (projectType === 'sound') projectData = this.state.dashboardData?.sound_projects;

        const projectId = projectData?.project_id;
        if (!projectId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'project.task',
            views: [[false, 'form']],
            context: { default_project_id: projectId },
        }, {
            onClose: async () => {
                await this.loadData();
            }
        });
    }

    buyCredits() {
        this.action.doAction("cyllo_green_metrics.action_buy_credit");
    }

    openTasks(projectType = 'green', stageId) {
        let projectData = this.state.dashboardData?.projects;
        if (projectType === 'water') projectData = this.state.dashboardData?.water_projects;
        if (projectType === 'sound') projectData = this.state.dashboardData?.sound_projects;

        const projectId = projectData?.project_id;
        const projectName = projectType.charAt(0).toUpperCase() + projectType.slice(1) + " Initiatives";
        
        if (!projectId) return;
        let domain = [['project_id', '=', projectId]];
        if (stageId) {
            domain.push(['stage_id', '=', stageId]);
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: projectName,
            res_model: 'project.task',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: {
                default_project_id: projectId,
                create: Boolean(this.state.canCreateProject),
            },
        }, {
            onClose: async () => {
                await this.loadData();
            }
        });
    }

    renderCharts() {
        if (!this.state.dashboardData) return;

        if (this.gasChart) this.gasChart.destroy();
        if (this.scopeChart) this.scopeChart.destroy();
        if (this.targetChart) this.targetChart.destroy();
        if (this.airTrendChart) this.airTrendChart.destroy();
        if (this.soundChart) this.soundChart.destroy();
        if (this.waterChart) this.waterChart.destroy();

        // 1. Overall Gas Emissions (Doughnut)
        const gasData = this.state.dashboardData.gas;
        if (gasData && gasData.labels.length > 0 && this.gasChartRef.el) {
            this.gasChart = new Chart(this.gasChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: gasData.labels,
                    datasets: [{
                        data: gasData.values,
                        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'],
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
                    }
                }
            });
        }

        // 2. Scope Breakdown (Doughnut)
        const scopeData = this.state.dashboardData.scope_breakdown;
        if (scopeData && scopeData.length > 0 && this.scopeChartRef.el) {
            // Assign color property to each item
            scopeData.forEach(s => {
                if (s.name.includes('Scope 1')) s.color = '#10b981';
                else if (s.name.includes('Scope 2')) s.color = '#3b82f6';
                else if (s.name.includes('Scope 3')) s.color = '#f59e0b';
                else s.color = '#8b5cf6';
            });

            const labels = scopeData.map(s => s.name);
            const values = scopeData.map(s => s.value);
            const colors = scopeData.map(s => s.color);

            this.scopeChart = new Chart(this.scopeChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        // 3. Target vs Actual (Gauge - half doughnut)
        const capData = this.state.dashboardData.cap_data;
        if (capData && this.targetChartRef.el) {
            const target = capData.targeted_achievement || 0.0;
            const used = capData.used || 0.0;
            const isReached = used <= target;
            
            let chartData, chartColors, chartLabels;
            if (target <= 0.0) {
                chartData = [used];
                chartColors = ['#6366f1'];
                chartLabels = ['Used'];
            } else if (isReached) {
                chartData = [used, target - used];
                chartColors = ['#10b981', '#e5e7eb'];
                chartLabels = ['Used', 'Remaining Target'];
            } else {
                chartData = [target, used - target];
                chartColors = ['#ef4444', '#f87171'];
                chartLabels = ['Target Limit', 'Exceeded Amount'];
            }

            this.targetChart = new Chart(this.targetChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: chartColors,
                        borderWidth: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    cutout: '75%',
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        // Helper to configure gradients for Line Charts
        const setupGradient = (canvasEl, colorStart, colorEnd) => {
            const ctx = canvasEl.getContext('2d');
            const grad = ctx.createLinearGradient(0, 0, 0, 250);
            grad.addColorStop(0, colorStart);
            grad.addColorStop(1, colorEnd);
            return grad;
        };

        // 4. Air Emissions Trend (Line)
        const airTrendData = this.state.dashboardData.air_trend;
        if (airTrendData && airTrendData.labels.length > 0 && this.airTrendChartRef.el) {
            const grad = setupGradient(this.airTrendChartRef.el, 'rgba(16, 185, 129, 0.3)', 'rgba(16, 185, 129, 0.0)');
            this.airTrendChart = new Chart(this.airTrendChartRef.el, {
                type: 'line',
                data: {
                    labels: airTrendData.labels,
                    datasets: [{
                        label: 'Air Emissions (t CO2e)',
                        data: airTrendData.values,
                        borderColor: '#10b981',
                        backgroundColor: grad,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointBackgroundColor: '#10b981',
                        pointHoverRadius: 7,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // 5. Water Pollution Trend (Line)
        const waterData = this.state.dashboardData.water;
        if (waterData && waterData.labels.length > 0 && this.waterChartRef.el) {
            const grad = setupGradient(this.waterChartRef.el, 'rgba(59, 130, 246, 0.3)', 'rgba(59, 130, 246, 0.0)');
            this.waterChart = new Chart(this.waterChartRef.el, {
                type: 'line',
                data: {
                    labels: waterData.labels,
                    datasets: [{
                        label: `Water Usage (${this.state.dashboardData.water_cap_data?.unit || 'L'})`,
                        data: waterData.values,
                        borderColor: '#3b82f6',
                        backgroundColor: grad,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointBackgroundColor: '#3b82f6',
                        pointHoverRadius: 7,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // 6. Sound Emissions Trend (Line)
        const soundData = this.state.dashboardData.sound;
        if (soundData && soundData.labels.length > 0 && this.soundChartRef.el) {
            const grad = setupGradient(this.soundChartRef.el, 'rgba(245, 158, 11, 0.3)', 'rgba(245, 158, 11, 0.0)');
            this.soundChart = new Chart(this.soundChartRef.el, {
                type: 'line',
                data: {
                    labels: soundData.labels,
                    datasets: [{
                        label: 'Sound Level (dB)',
                        data: soundData.values,
                        borderColor: '#f59e0b',
                        backgroundColor: grad,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointBackgroundColor: '#f59e0b',
                        pointHoverRadius: 7,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    // --- MULTI-SELECT SCOPE HANDLERS ---
    async toggleScopeAll(ev) {
        const checked = ev.target.checked;
        if (checked) {
            const allScopeIds = (this.state.dashboardData.scopes || []).map(s => s.id.toString());
            this.state.waterScopeFilter = ['all', ...allScopeIds];
        } else {
            this.state.waterScopeFilter = [];
        }
        await this.loadData();
    }

    async toggleScope(scopeId, ev) {
        const idStr = scopeId.toString();
        let currentFilters = [...this.state.waterScopeFilter];
        
        if (ev.target.checked) {
            if (idStr === 'no_scope') {
                currentFilters = ['no_scope'];
            } else {
                currentFilters = currentFilters.filter(f => f !== 'no_scope');
                if (!currentFilters.includes(idStr)) {
                    currentFilters.push(idStr);
                }
            }
        } else {
            currentFilters = currentFilters.filter(f => f !== idStr && f !== 'all');
        }
        
        const allScopeIds = (this.state.dashboardData.scopes || []).map(s => s.id.toString());
        const expectedCount = allScopeIds.length;
        const actualCount = currentFilters.filter(f => f !== 'all' && f !== 'no_scope').length;
        
        if (actualCount === expectedCount && expectedCount > 0) {
            if (!currentFilters.includes('all')) currentFilters.push('all');
        } else {
            currentFilters = currentFilters.filter(f => f !== 'all');
        }
        
        this.state.waterScopeFilter = currentFilters;
        await this.loadData();
    }

    isScopeSelected(id) {
        const idStr = id.toString();
        if (idStr === 'no_scope') {
            return this.state.waterScopeFilter.includes('no_scope');
        }
        return this.state.waterScopeFilter.includes(idStr) || this.state.waterScopeFilter.includes('all');
    }

    isAllSelected() {
        return this.state.waterScopeFilter.includes('all');
    }

    getSelectedScopesText() {
        if (this.isAllSelected()) return "All Scopes";
        if (!this.state.waterScopeFilter || this.state.waterScopeFilter.length === 0) return "No Scopes Selected";
        if (this.state.waterScopeFilter.length === 1 && this.state.waterScopeFilter[0] === 'no_scope') return "No Scope Only";
        
        const count = this.state.waterScopeFilter.filter(f => f !== 'all').length;
        return `${count} Scopes Selected`;
    }
}

GreenMetricsDashboard.template = "cyllo_green_metrics.GreenDashboard";
registry.category("actions").add("green_metrics_dashboard", GreenMetricsDashboard);
