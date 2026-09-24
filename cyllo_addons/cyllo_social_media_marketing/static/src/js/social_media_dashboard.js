/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { loadJS } from "@web/core/assets";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PlatformPickerDialog } from "./platform_picker_dialog";
import { ConnectAccountDialog } from "./connect_account_dialog";
import { connectAccountPlatforms } from "./platform_registry";
import { streamPlatforms } from "./streams/stream_registry";

const actionRegistry = registry.category("actions");

export class AudienceChart extends Component {
    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        this.tooltipEl = null;
        onMounted(() => this.renderChart());
        onPatched(() => this.renderChart());
        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
            }
            if (this.tooltipEl) {
                this.tooltipEl.remove();
            }
        });
    }

    getOrCreateTooltip(chart) {
        if (!this.tooltipEl) {
            this.tooltipEl = document.createElement("div");
            this.tooltipEl.className = "o_audience_chart_tooltip";
            chart.canvas.parentNode.appendChild(this.tooltipEl);
        }
        return this.tooltipEl;
    }

    externalTooltipHandler(context) {
        const { chart, tooltip } = context;
        const tooltipEl = this.getOrCreateTooltip(chart);
        if (tooltip.opacity === 0) {
            tooltipEl.style.opacity = 0;
            return;
        }
        const point = tooltip.dataPoints && tooltip.dataPoints[0];
        if (point) {
            tooltipEl.innerHTML = `
                <div class="o_audience_chart_tooltip_date">${point.label}</div>
                <div class="o_audience_chart_tooltip_value">
                    <span class="o_audience_chart_tooltip_dot"></span>${point.formattedValue}
                </div>`;
        }
        const gap = 10;
        const containerWidth = chart.canvas.parentNode.offsetWidth;
        let left = chart.canvas.offsetLeft + tooltip.caretX + gap;
        if (left + tooltipEl.offsetWidth > containerWidth) {
            left = chart.canvas.offsetLeft + tooltip.caretX - gap - tooltipEl.offsetWidth;
        }
        tooltipEl.style.opacity = 1;
        tooltipEl.style.left = left + "px";
        tooltipEl.style.top =
            chart.canvas.offsetTop + tooltip.caretY - tooltipEl.offsetHeight / 2 + "px";
    }

    renderChart() {
        if (!this.canvasRef.el || typeof Chart === "undefined") {
            return;
        }
        if (this.chart) {
            this.chart.destroy();
        }
        let history = this.props.account.audience_history || [];
        if (history.length === 1) {
            history = [{ date: "", followers_count: 0 }, ...history];
        }
        this.chart = new Chart(this.canvasRef.el, {
            type: "line",
            data: {
                labels: history.map((point) => point.date),
                datasets: [{
                    data: history.map((point) => point.followers_count),
                    borderColor: "#849600",
                    backgroundColor: "rgba(132, 150, 0, 0.12)",
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointBackgroundColor: "#849600",
                    pointHoverRadius: 5,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                devicePixelRatio: window.devicePixelRatio || 2,
                animation: false,
                interaction: { mode: "index", intersect: false },
                layout: { padding: { top: 4, right: 2, bottom: 2, left: 2 } },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: false,
                        mode: "index",
                        intersect: false,
                        external: (context) => this.externalTooltipHandler(context),
                    },
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: false,
                        beginAtZero: true,
                        suggestedMax: Math.max(...history.map((p) => p.followers_count), 1) * 1.15,
                    },
                },
            },
        });
    }
}
AudienceChart.template = "cyllo_social_media_marketing.AudienceChart";
AudienceChart.props = ["account"];

export class SocialMediaDashboard extends Component {
    static components = { AudienceChart };

    async setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.streamPlatforms = streamPlatforms;
        this.state = useState({
            activeTab: 'all',
            accounts: false,
            posts: false,
            activePosts: false,
            refreshingAudience: false,
            isAdmin: false,
            campaigns: []
        });
        onWillStart(async () => {
            this.state.isAdmin = await this.user.hasGroup("cyllo_social_media_marketing.group_social_media_administrator");
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
            } catch (e) {
                try {
                    await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
                } catch (e2) {
                    console.error("Failed to load Chart.js");
                }
            }
            try {
                const results = await this.orm.call("social.media.post", "get_dashboard_data", [""]);
                this.setDashboardData(results);
            } catch (error) {
                if (error?.message !== "Component is destroyed") {
                    throw error;
                }
            }
        });
    }

    OpenPlatformPicker() {
        this.dialog.add(PlatformPickerDialog, {
            onSelectPlatform: (platform) => this.OpenView(platform),
        });
    }

    OpenAudienceGraph(account) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${account.account_name} — Followers`,
            res_model: "social.media.snapshot",
            views: [[false, "graph"]],
            domain: [["platform", "=", account.platform], ["account_res_id", "=", account.id]],
            target: "current",
        });
    }

    OpenCampaigns() {
        this.action.doAction("cyllo_social_media_marketing.action_view_social_campaigns");
    }

    OpenCampaign(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "utm.campaign",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    setDashboardData(results) {
        this.state.accounts = results.dashboard_data;
        this.state.posts = results.posts;
        this.state.campaigns = results.campaigns || [];
        this.filterPosts();
    }

    async RefreshDashboardData() {
        const results = await this.orm.call("social.media.post", "get_dashboard_data", [""]);
        this.setDashboardData(results);
    }

    async RefreshAudience() {
        if (this.state.refreshingAudience) {
            return;
        }
        this.state.refreshingAudience = true;
        try {
            await this.orm.call("social.media.snapshot", "action_capture_audience_snapshots", []);
            const results = await this.orm.call("social.media.post", "get_dashboard_data", [""]);
            this.setDashboardData(results);
        } catch (error) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    message: "Could not refresh audience data. Please try again.",
                    type: "warning",
                },
            });
        } finally {
            this.state.refreshingAudience = false;
        }
    }

    OpenConnectModal(platform) {
        this.dialog.add(ConnectAccountDialog, {
            platform,
            onConnected: () => this.RefreshDashboardData(),
        });
    }

    setActiveTab(ev, tab) {
        this.state.activeTab = tab;
        this.filterPosts()
    }
    filterPosts() {
        if (this.state.activeTab === 'all') {
            this.state.activePosts = this.state.posts;
            return;
        }
        const postField = streamPlatforms.get(this.state.activeTab, false)?.postField;
        this.state.activePosts = postField
            ? this.state.posts.filter((post) => post[postField])
            : this.state.posts;
    }

    get groupedPosts() {
        const groups = [];
        for (const [platform, config] of streamPlatforms.getEntries()) {
            if (!config.postField) {
                continue;
            }
            const posts = this.state.activePosts.filter((post) => post[config.postField]);
            if (posts.length) {
                groups.push({ platform, label: config.label, icon: config.icon, color: config.color, posts });
            }
        }
        return groups;
    }

    async OpenView(model) {
        var model_exist = await this.orm.call("social.media.post", "get_model", ["", model], {});
        if (!model_exist) {
            const entry = connectAccountPlatforms.get(model, false);
            const moduleLabel = entry ? entry.moduleLabel : "required";
            this.dialog.add(ConfirmationDialog, {
                title: "Module Not Installed",
                body: `The ${moduleLabel} module isn't installed yet. Install it from Apps to connect a ${moduleLabel} account.`,
                confirmLabel: "Go to Apps",
                confirm: () => {
                    this.action.doAction({
                        type: "ir.actions.act_window",
                        name: "Apps",
                        res_model: "ir.module.module",
                        views: [[false, "kanban"]],
                        context: entry ? { search_default_name: moduleLabel } : {},
                        target: "current",
                    });
                },
                cancel: () => {},
            });
            return
        }
        this.OpenConnectModal(model);
    }

    ViewAccounts(account) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: account.platform,
            res_id: account.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    CreatePost() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'social.media.post',
            views: [[false, "form"]],
            target: "current",
        });
    }

    OpenFeed(feed) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: 'Post',
            res_model: "social.media.post",
            res_id: feed,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async OpenOnPlatform(ev, feed, platform) {
        ev.stopPropagation();
        const action = await this.orm.call("social.media.post", "action_open_on_platform", [feed, platform]);
        this.action.doAction(action);
    }

    OpenModal() {
        this.state.showModal = true;
    }

    CloseModal() {
        this.state.showModal = false;
    }

    audiencePercent(account) {
        if (!account.audience_baseline) {
            return 0;
        }
        return Math.round((account.audience_delta / account.audience_baseline) * 100);
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = deserializeDateTime(dateStr);
            return date.toFormat("dd MMM yyyy, HH:mm");
        } catch (e) {
            return dateStr;
        }
    }
}

SocialMediaDashboard.template = "cyllo_social_media_marketing.SocialMediaDashboard";
actionRegistry.add("social_media_dashboard", SocialMediaDashboard);
