/** @odoo-module **/
/**
 * Dashboard ↔ cyllo_ai chatbot integration:
 *  - "Explain with AI" chart icon -> CY_AI:EXPLAIN_CHART (insight in the chat).
 *  - Empty dashboard -> a "Create a dashboard with AI" nudge/offer that opens the
 *    quick-dashboard builder widget in the chat.
 *
 * Importing the two widget modules registers their chat renderers (side effect).
 */
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { CylloDashboard } from "@cyllo_analytics/js/cyllo_dashboard";
import "./ai_chart_tile";
import "./ai_quick_dashboard";

const { useEffect, onMounted, onWillUnmount } = owl;

// Distinguishes this module's create-dashboard nudge/offer from any other.
const CREATE_KEY = "create_dashboard";

patch(CylloDashboard.prototype, {
    setup() {
        super.setup();
        // Offer the quick-dashboard builder while the dashboard is EMPTY
        // (`state.showInfo` is the core's own empty-dashboard signal) AND the
        // user can actually create dashboards (`hasAccess` — the same gate as the
        // manual "+ Create" button; creating needs admin-group rights). The nudge
        // bubble (owl) and the greeting/header offer both route here.
        useEffect(
            (empty) => {
                if (empty && this.hasAccess) {
                    this.env.bus.trigger("CY_AI:NUDGE", {
                        label: "Create a dashboard with AI", key: CREATE_KEY,
                        mode: "quick_dashboard", freshPolicy: "always",
                        // The chatbot renders this widget itself on click (after
                        // opening + starting a fresh thread) — no host round-trip,
                        // so the builder shows on the first click.
                        widget: { key: "quick_dashboard" },
                        intro: "Let's build a dashboard — pick a table and I'll suggest charts:",
                    });
                    this.env.bus.trigger("CY_AI:SET_OFFER", {
                        label: "Create dashboard", key: CREATE_KEY,
                        // autoFresh: entering an empty dashboard auto-starts a
                        // clean thread (old one archived to history), so the
                        // create-dashboard context never lands in a prior chat.
                        mode: "quick_dashboard", freshPolicy: "always",
                        autoFresh: true,
                        // Carry the builder so opening the chat via the launcher
                        // icon (not just the nudge) lands straight in the builder.
                        widget: { key: "quick_dashboard" },
                        intro: "Let's build a dashboard — pick a table and I'll suggest charts:",
                    });
                } else {
                    this.env.bus.trigger("CY_AI:CLEAR_NUDGE");
                    this.env.bus.trigger("CY_AI:CLEAR_OFFER");
                }
            },
            () => [this.state.showInfo],
        );
        // Greeting/header OFFER click -> open the builder. (The NUDGE bubble
        // path pushes its widget directly from the chatbot — see the nudge's
        // `widget` above — so we only handle the offer here, avoiding a
        // double-push.)
        const openBuilder = (ev) => {
            if (ev.detail?.key === CREATE_KEY) {
                this.env.bus.trigger("CY_AI:PUSH_MESSAGE", {
                    html: "Let's build a dashboard — pick a table and I'll suggest charts:",
                    widget: { key: "quick_dashboard" },
                });
            }
        };
        useBus(this.env.bus, "CY_AI:CHAT_ACTION", openBuilder);

        // Publish this dashboard's editable state so the chat can change it
        // ("make the revenue chart a pie", "drop the vendor one", "add sales by
        // customer"). The agent's edit_dashboard tool reads it from ui_context.
        onMounted(() => this._publishDashState());
        // A live edit was written server-side -> reload so it shows.
        useBus(this.env.bus, "CY_AI:DASH_APPLY", (ev) => this._onDashApply(ev));
        onWillUnmount(() => {
            this.env.bus.trigger("CY_AI:CLEAR_NUDGE");
            this.env.bus.trigger("CY_AI:CLEAR_OFFER");
            this.env.bus.trigger("CY_AI:DASH_CLEAR");
        });
    },

    /** Publish {config_id, name, sheets:[{id,name,type,allowed_chart_types,model}]}
     *  for the agent's edit_dashboard tool (computed + access-checked server-side). */
    async _publishDashState() {
        if (!this.id) {
            return;
        }
        try {
            const ctx = await this.orm.call(
                "dashboard.sheet", "ai_dashboard_edit_context", [this.id]);
            if (ctx && ctx.config_id) {
                this.env.bus.trigger("CY_AI:DASH_STATE", ctx);
            }
        } catch (_e) {
            // Non-fatal: the dashboard just won't be chat-editable this view.
        }
    },

    /** Reload the dashboard after a live edit (full client-action reload so the
     *  changed sheet types/links are re-read from the DB). Remounting re-publishes
     *  the editable state. */
    _onDashApply(ev) {
        const configId = ev.detail && ev.detail.config_id;
        if (!configId || Number(configId) !== Number(this.id)) {
            return;   // an edit for a different dashboard
        }
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "cy_analytic_dashboard",
                target: "current",
                context: { rec_id: this.id },
            },
            { stackPosition: "replaceCurrentAction" },
        );
    },

    async explainWithAI(item) {
        // Fetch the chart's data for the agent to reason over (the chart itself
        // is rendered by GraphTile, which self-fetches from `item`).
        let rows = [];
        try {
            if (item.query) {
                rows = await this.orm.call("dashboard.config", "sql_execute", [item.query]);
            }
        } catch (_) {
            rows = [];
        }
        // Map the raw column aliases to their human labels so the agent knows
        // what each key means.
        const columns = {};
        (item.axis_ids || []).forEach((a) => {
            if (a.alias) {
                columns[a.alias] = a.name || a.column || a.alias;
            }
        });
        this.env.bus.trigger("CY_AI:EXPLAIN_CHART", {
            chart: {
                item,
                theme: this.themeState.currentTheme,
                themeColor: this.themeState.theme?.theme_color_ids,
                isDarkMode: this.state.darkMode,
            },
            chartContext: {
                title: item.name,
                chart_type: item.type,
                columns,
                rows: Array.isArray(rows) ? rows : [],
            },
        });
    },
});
