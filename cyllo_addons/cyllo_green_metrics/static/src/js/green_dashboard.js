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

    async setDateFilter(value) {
        this.state.waterDateFilter = value;
        await this.loadData();
    }

    // --- METRIC CARD PERCENTAGE HELPERS ---
    getCapUsedPct() {
        const cap = this.state.dashboardData?.cap_data;
        if (!cap || !(cap.cap > 0)) return 0;
        return Math.round((cap.used / cap.cap) * 100);
    }

    getCapRemainingPct() {
        return Math.max(0, 100 - this.getCapUsedPct());
    }

    getCapRemaining() {
        const cap = this.state.dashboardData?.cap_data;
        if (!cap) return 0;
        return Math.max(0, (cap.cap || 0) - (cap.used || 0));
    }

    getPreviousYearPct() {
        const cap = this.state.dashboardData?.cap_data;
        if (!cap || !(cap.targeted_achievement > 0) || !(cap.previous_year_achieved > 0)) return 0;
        return Math.round((cap.previous_year_achieved / cap.targeted_achievement) * 100);
    }

    getWaterUsedPct() {
        const water = this.state.dashboardData?.water_cap_data;
        if (!water || !(water.cap > 0)) return 0;
        return Math.round((water.used / water.cap) * 100);
    }

    getWaterRemainingPct() {
        return Math.max(0, 100 - this.getWaterUsedPct());
    }

    // Sum of a trend chart's values, used for the header badges
    getTrendTotal(key) {
        const trend = this.state.dashboardData?.[key];
        if (!trend || !trend.values) return 0;
        const total = trend.values.reduce((a, b) => a + (b || 0), 0);
        return Math.round(total * 100) / 100;
    }

    // True when a chart's dataset is empty or entirely zero (no data in that range/scope)
    isEmptyChart(key) {
        const data = this.state.dashboardData?.[key];
        if (!data) return true;
        if (Array.isArray(data)) {
            return data.length === 0 || data.reduce((a, s) => a + (s.value || 0), 0) === 0;
        }
        const values = data.values || [];
        return values.length === 0 || values.reduce((a, b) => a + (b || 0), 0) === 0;
    }

    async onWaterDateRangeChange() {
        if (this.state.waterStartDate && this.state.waterEndDate) {
            // End date cannot be earlier than the start date — clamp it to the start
            if (this.state.waterEndDate < this.state.waterStartDate) {
                this.state.waterEndDate = this.state.waterStartDate;
            }
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

        // --- Olive palette & shared Chart.js plugins (reference design) ---
        const OLIVE = ['#3e4a1f', '#55661d', '#6f8422', '#8ba32a', '#a9c04a', '#c3d26c', '#d9e19a'];

        const fmtNum = (v) => {
            const r = Math.round(v * 1000) / 1000;
            return r.toLocaleString('en-US');
        };

        // Center text (doughnut totals) — opts: {title, sub, big, dy}
        const gmCenterText = {
            id: 'gmCenterText',
            afterDraw(chart, args, opts) {
                if (!opts || !opts.title) return;
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data.length) return;
                const arc = meta.data[0];
                const x = arc.x;
                const y = arc.y + (opts.dy || 0);
                const ctx = chart.ctx;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                if (opts.big) {
                    ctx.fillStyle = '#171b26';
                    ctx.font = '800 28px Roboto, sans-serif';
                    ctx.fillText(opts.title, x, y);
                } else {
                    ctx.fillStyle = '#171b26';
                    ctx.font = '700 20px Roboto, sans-serif';
                    ctx.fillText(opts.title, x, y - 8);
                    if (opts.sub) {
                        ctx.fillStyle = '#6b7280';
                        ctx.font = '500 11px Roboto, sans-serif';
                        ctx.fillText(opts.sub, x, y + 14);
                    }
                }
                ctx.restore();
            }
        };

        // Percentage labels drawn on each doughnut slice
        const gmArcLabels = {
            id: 'gmArcLabels',
            afterDraw(chart, args, opts) {
                if (!opts || opts.display === false) return;
                const meta = chart.getDatasetMeta(0);
                const data = chart.data.datasets[0].data || [];
                const total = data.reduce((a, b) => a + b, 0);
                if (!total || !meta || !meta.data.length) return;
                const ctx = chart.ctx;
                meta.data.forEach((arc, i) => {
                    const pct = Math.round((data[i] / total) * 100);
                    if (pct < 4) return;   // skip tiny slices
                    const mid = (arc.startAngle + arc.endAngle) / 2;
                    const r = (arc.innerRadius + arc.outerRadius) / 2;
                    ctx.save();
                    ctx.translate(arc.x + Math.cos(mid) * r, arc.y + Math.sin(mid) * r);
                    let ang = mid;
                    if (ang > Math.PI / 2 || ang < -Math.PI / 2) ang += Math.PI;
                    ctx.rotate(ang);
                    ctx.fillStyle = '#fff';
                    ctx.font = '600 10px Roboto, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(pct + '%', 0, 0);
                    ctx.restore();
                });
            }
        };

        // Re-center the gauge dome horizontally (Chart.js fits the full circle from the left edge)
        const gmGaugeCenter = {
            id: 'gmGaugeCenter',
            afterUpdate(chart) {
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data.length || !chart.chartArea) return;
                const targetX = chart.chartArea.left + chart.chartArea.width / 2;
                meta.data.forEach(el => {
                    const dx = targetX - el.x;
                    if (Math.abs(dx) > 0.5) el.x += dx;
                });
            }
        };

        // Dotted ridge inside the gauge, drawn as sampled dots along the arc
        const gmGaugeDots = {
            id: 'gmGaugeDots',
            afterDraw(chart, args, opts) {
                if (!opts || opts.display === false) return;
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data.length) return;
                const first = meta.data[0];
                const last = meta.data[meta.data.length - 1];
                const r = first.innerRadius - (first.outerRadius - first.innerRadius) * 0.25;
                if (r <= 0) return;
                const ctx = chart.ctx;
                ctx.save();
                ctx.fillStyle = '#c3cbae';
                const steps = 16;
                for (let i = 0; i <= steps; i++) {
                    const t = i / steps;
                    const a = first.startAngle + (last.endAngle - first.startAngle) * t;
                    const x = first.x + Math.cos(a) * r;
                    const y = first.y + Math.sin(a) * r;
                    ctx.beginPath();
                    ctx.arc(x, y, 1.4, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        };

        // Pointer marker on the gauge at the end of the used arc
        const gmGaugePointer = {
            id: 'gmGaugePointer',
            afterDraw(chart, args, opts) {
                if (!opts || opts.display === false) return;
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data.length) return;
                const idx = Math.min(Math.max(opts.pointerIdx, 0), meta.data.length - 1);
                const arcEl = meta.data[idx];
                const angle = arcEl.endAngle;
                const rMid = arcEl.innerRadius + (arcEl.outerRadius - arcEl.innerRadius) * 0.5;
                const x = arcEl.x + Math.cos(angle) * rMid;
                const y = arcEl.y + Math.sin(angle) * rMid;
                const ctx = chart.ctx;
                ctx.save();
                ctx.shadowColor = 'rgba(124, 154, 30, 0.55)';
                ctx.shadowBlur = 12;
                ctx.beginPath();
                ctx.arc(x, y, 7, 0, Math.PI * 2);
                ctx.fillStyle = '#fff';
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.beginPath();
                ctx.arc(x, y, 3.5, 0, Math.PI * 2);
                ctx.fillStyle = '#55661d';
                ctx.fill();
                ctx.restore();
            }
        };

        // Shared olive doughnut legend (manual items — avoids Chart.js default quirks), caps at 4 + "+N"
        const oliveLegend = () => ({
            position: 'right',
            labels: {
                usePointStyle: true,
                pointStyle: 'circle',
                boxWidth: 8,
                boxHeight: 8,
                font: { size: 11 },
                color: '#374151',
                padding: 10,
                generateLabels(chart) {
                    const ds = chart.data.datasets[0];
                    const bg = ds.backgroundColor || [];
                    const items = (chart.data.labels || []).map((label, i) => ({
                        text: label,
                        fillStyle: bg[i] || '#9ca3af',
                        strokeStyle: bg[i] || '#9ca3af',
                        lineWidth: 0,
                        hidden: !chart.getDataVisibility(i),
                        index: i,
                    }));
                    const max = 4;
                    if (items.length > max) {
                        items.push({
                            text: '+' + (items.length - max),
                            fillStyle: '#9ca3af',
                            strokeStyle: '#9ca3af',
                            lineWidth: 0,
                            hidden: false,
                            index: -1,
                        });
                    }
                    return items;
                },
                onClick(e, item, legend) {
                    if (item.index === -1) return;
                    const chart = legend.chart;
                    chart.toggleDataVisibility(item.index);
                    chart.update();
                }
            }
        });

        // 1. Overall Gas Emissions (Doughnut, olive palette, % labels, center total)
        const gasData = this.state.dashboardData.gas;
        if (gasData && gasData.labels.length > 0 && this.gasChartRef.el) {
            const gasTotal = gasData.values.reduce((a, b) => a + b, 0);
            const unit = this.state.dashboardData.cap_data?.unit || 't CO2e';
            this.gasChart = new Chart(this.gasChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: gasData.labels.map((l, i) => l || ('Gas ' + (i + 1))),
                    datasets: [{
                        data: gasData.values,
                        backgroundColor: gasData.values.map((_, i) => OLIVE[i % OLIVE.length]),
                        borderColor: '#f6f7f3',
                        borderWidth: 1,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    layout: { padding: 4 },
                    plugins: {
                        legend: oliveLegend(),
                        tooltip: { enabled: true },
                        gmCenterText: { title: fmtNum(gasTotal), sub: unit },
                        gmArcLabels: { display: true }
                    }
                },
                plugins: [gmCenterText, gmArcLabels]
            });
        }

        // 2. Scope Breakdown (Doughnut — same panel design as Overall Gas Emissions)
        const scopeData = this.state.dashboardData.scope_breakdown;
        if (scopeData && scopeData.length > 0 && this.scopeChartRef.el) {
            const unit = this.state.dashboardData.cap_data?.unit || 't CO2e';
            const scopeTotal = scopeData.reduce((a, s) => a + (s.value || 0), 0);
            const labels = scopeData.map((s, i) => s.name || ('Scope ' + (i + 1)));
            const values = scopeData.map(s => s.value);

            this.scopeChart = new Chart(this.scopeChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: values.map((_, i) => OLIVE[i % OLIVE.length]),
                        borderColor: '#f6f7f3',
                        borderWidth: 1,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    layout: { padding: 4 },
                    plugins: {
                        legend: oliveLegend(),
                        tooltip: { enabled: true },
                        gmCenterText: { title: fmtNum(scopeTotal), sub: unit },
                        gmArcLabels: { display: true }
                    }
                },
                plugins: [gmCenterText, gmArcLabels]
            });
        }

        // 3. Target vs Actual (Gauge — olive gradient, dotted ridge, pointer, center %)
        const capData = this.state.dashboardData.cap_data;
        if (capData && this.targetChartRef.el) {
            const target = capData.targeted_achievement || 0.0;
            const used = capData.filtered_used || 0.0;
            const pct = target > 0 ? Math.min(Math.round((used / target) * 100), 100) : 0;

            let segmentData, segmentColors, pointerIdx;
            const grad = ['#c9d586', '#b7c95c', '#a9c04a', '#9cb43a', '#8ba32a', '#7c9224', '#6a7d1d', '#55661d'];
            if (target <= 0) {
                segmentData = [100];
                segmentColors = ['#c3d26c'];
                pointerIdx = -1;
            } else if (pct <= 0) {
                segmentData = [100];
                segmentColors = ['#e6e8e0'];
                pointerIdx = -1;
            } else {
                segmentData = [];
                segmentColors = [];
                for (let k = 0; k < 8; k++) {
                    segmentData.push(pct / 8);
                    segmentColors.push(grad[k]);
                }
                if (pct < 100) {
                    segmentData.push(100 - pct);
                    segmentColors.push('#e6e8e0');
                }
                pointerIdx = 7;
            }

            this.targetChart = new Chart(this.targetChartRef.el, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: segmentData,
                        backgroundColor: segmentColors,
                        borderWidth: 1,
                        borderColor: '#f6f7f3',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    rotation: -90,
                    circumference: 180,
                    cutout: '70%',
                    layout: { padding: 10 },
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false },
                        gmCenterText: { title: pct + '%', big: true, dy: -20 },
                        gmGaugeDots: { display: true },
                        gmGaugePointer: { display: target > 0 && pointerIdx >= 0, pointerIdx: pointerIdx }
                    }
                },
                plugins: [gmCenterText, gmGaugeDots, gmGaugePointer, gmGaugeCenter]
            });
        }

        // Shared builder: horizontal-bar trend chart (gray bars, olive highlight on current point)
        const makeBarTrend = (chartRef, trendData, highlightColor) => {
            const labels = (trendData.labels || []).map(l => (l || '').replace(/\s+\d{4}$/, '') || l);
            const values = (trendData.values || []).map(v => v || 0);
            const el = chartRef.el;
            if (!el) return null;

            const now = new Date();
            const short = now.toLocaleString('en-US', { month: 'short' });
            const monthLabel = short + ' ' + now.getFullYear();
            const dayLabel = String(now.getDate()).padStart(2, '0') + ' ' + short;
            let hlIdx = labels.indexOf(monthLabel);
            if (hlIdx < 0) hlIdx = undefined; // fallback below works on original labels
            if (hlIdx === undefined) {
                const orig = trendData.labels || [];
                let oi = orig.indexOf(monthLabel);
                if (oi < 0) oi = orig.indexOf(dayLabel);
                if (oi < 0) oi = orig.length - 1;
                hlIdx = oi;
            }
            hlIdx = Math.max(0, Math.min(hlIdx, labels.length - 1));

            return new Chart(el, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: values.map((_, i) => (i === hlIdx ? highlightColor : '#d7d9df')),
                        borderRadius: 6,
                        categoryPercentage: 0.6,
                        barPercentage: 0.8,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: true } },
                    scales: {
                        x: {
                            grid: { display: false },
                            border: { display: false },
                            ticks: {
                                color: (ctx) => (ctx && ctx.index === hlIdx ? '#171b26' : '#9ca3af'),
                                maxRotation: 0,
                                font: { size: 11 }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f3f4f6' },
                            border: { display: false },
                            ticks: { color: '#9ca3af', font: { size: 10 }, maxTicksLimit: 6 }
                        }
                    }
                }
            });
        };

        // 4. Air Emission Trend (Bar)
        const airTrendData = this.state.dashboardData.air_trend;
        if (airTrendData && airTrendData.labels.length > 0) {
            this.airTrendChart = makeBarTrend(this.airTrendChartRef, airTrendData, '#8ba32a');
        }

        // 5. Water Usage Trend (Bar)
        const waterData = this.state.dashboardData.water;
        if (waterData && waterData.labels.length > 0) {
            this.waterChart = makeBarTrend(this.waterChartRef, waterData, '#55661d');
        }

        // 6. Sound Level Trend (Bar)
        const soundData = this.state.dashboardData.sound;
        if (soundData && soundData.labels.length > 0) {
            this.soundChart = makeBarTrend(this.soundChartRef, soundData, '#a9c04a');
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
