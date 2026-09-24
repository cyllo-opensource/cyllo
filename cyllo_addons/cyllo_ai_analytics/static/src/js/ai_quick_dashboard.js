/** @odoo-module **/
/**
 * Quick-dashboard builder, rendered INSIDE the cyllo_ai chatbot: pick one or
 * more tables → generate chart proposals per table → curate → create the
 * dashboard (atomic backend) → open it. Registered into cyllo_ai's
 * "cyllo_ai.chat_widgets" slot so the chat hosts it without depending on
 * analytics.
 *
 * Tables are picked with the SAME searchable component the sheet uses
 * (Many2XAutocomplete on ir.model, transient=False). Each picked table is an
 * INDEPENDENT source — its charts are single-table, never joined to another
 * table — so a dashboard can span e.g. sales + purchase with no join risk.
 *
 * CONVERSATIONAL: the builder is also driven by chat. The agent can OPEN it
 * pre-seeded ("create a dashboard for sales" → seed_models + auto_generate) and
 * EDIT it live — set a chart's type, keep/drop a chart, add/remove a table,
 * rename, or create — via CY_AI:QD_PATCH. To let the agent reference cards, the
 * ACTIVE widget publishes its state (tables + cards + name) on CY_AI:QD_STATE,
 * which the chatbot folds into the outgoing ui_context. Only the most-recently
 * mounted widget is "active", so patches never hit a stale card set.
 *
 * All reads/writes go through the secured backend methods
 * (suggest_charts_for_table / create_quick_dashboard), which re-check model +
 * field + create access server-side. Chart-type picks are constrained to each
 * chart's `allowed_chart_types` (server also re-validates).
 */
import { Component, useState, useEffect, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class QuickDashboardWidget extends Component {
    static template = "cyllo_ai_analytics.QuickDashboardWidget";
    static components = { Many2XAutocomplete };
    static props = {
        // Optional seed from the agent's open_quick_dashboard tool.
        seed_models: { type: Array, optional: true },   // [{model, name}]
        auto_generate: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this._cardSeq = 0;   // monotonic → stable per-card ids for the whole life
        const seed = this.props.seed_models || [];
        this.state = useState({
            step: "pick",        // pick | proposing | review | creating | done
            models: seed.map((m) => ({ model: m.model, name: m.name })),
            groups: [],          // [{model, name, cards:[{id, title, dimension, measure, chart_type, allowed_chart_types}]}]
            selected: {},        // cardId -> checked
            name: "",
            dashboard: null,     // {dashboard_id, name, chart_count}
            error: "",
        });

        // This instance is the active builder (the one chat edits target). The
        // most-recently mounted wins; publishing/patching is guarded on it.
        QuickDashboardWidget._active = this;
        useBus(this.env.bus, "CY_AI:QD_PATCH", (ev) => this._onPatch(ev));
        // Publish state to the chat whenever anything the agent cares about
        // changes (tables, cards, selection, chart types, name) — covers the
        // checkbox/select two-way bindings that have no explicit handler.
        useEffect(
            () => { this._publish(); },
            () => [JSON.stringify(this._snapshot())],
        );
        onMounted(() => {
            if (this.props.auto_generate && this.state.models.length) {
                this.onGenerate();
            }
        });
        onWillUnmount(() => {
            if (QuickDashboardWidget._active === this) {
                QuickDashboardWidget._active = null;
                this.env.bus.trigger("CY_AI:QD_CLEAR");
            }
        });
    }

    // -- table picker --------------------------------------------------------

    /** Filter the picker to real tables (non-transient) and hide already-picked
     *  ones — matches the sheet's Tables picker. */
    getDomain() {
        const domain = [["transient", "=", false]];
        const picked = this.state.models.map((m) => m.model);
        if (picked.length) {
            domain.push(["model", "not in", picked]);
        }
        return domain;
    }

    async onSelectModel(records) {
        if (!records || !records.length) {
            return;
        }
        // Read the technical model name + label for the picked ir.model record.
        const [rec] = await this.orm.read("ir.model", [records[0].id], ["model", "name"]);
        if (rec) {
            this._addModel({ model: rec.model, name: rec.name });
        }
    }

    onRemoveModel(model) {
        this._removeModel(model);
    }

    // -- proposal generation -------------------------------------------------

    async onGenerate() {
        if (!this.state.models.length || this.state.step === "proposing") {
            return;
        }
        this.state.step = "proposing";
        this.state.error = "";
        const groups = [];
        for (const m of this.state.models) {
            const g = await this._genGroupFor(m);
            if (g) {
                groups.push(g);
            }
        }
        this.state.groups = groups;
        if (!groups.length) {
            this.state.error = "No useful chart suggestions for the selected table(s).";
            this.state.step = "pick";
            return;
        }
        if (!this.state.name) {
            const names = this.state.models.map((m) => m.name);
            this.state.name = names.length === 1 ? `${names[0]} Dashboard`
                : `${names.slice(0, 2).join(" & ")} Dashboard`;
        }
        this.state.step = "review";
    }

    /** Fetch + shape the proposal group for one table (or null if none). Assigns
     *  each card a stable id and selects it by default. */
    async _genGroupFor(m) {
        let cards = [];
        try {
            cards = await this.orm.call(
                "dashboard.sheet", "suggest_charts_for_table", [m.model]);
        } catch (_e) {
            // keep going for the other tables; a fully-empty result is noted above
        }
        cards = cards || [];
        if (!cards.length) {
            return null;
        }
        cards.forEach((c) => {
            c.id = "c" + (++this._cardSeq);
            if (!c.allowed_chart_types || !c.allowed_chart_types.length) {
                c.allowed_chart_types = [c.chart_type];
            }
            this.state.selected[c.id] = true;
        });
        return { model: m.model, name: m.name, cards };
    }

    // -- create + open -------------------------------------------------------

    /** Flattened checked cards, reduced to the minimal picks the backend
     *  re-validates. Each pick carries its own model + chosen chart type. */
    get checkedPicks() {
        const picks = [];
        this.state.groups.forEach((g) => {
            g.cards.forEach((c) => {
                if (this.state.selected[c.id]) {
                    picks.push({
                        model: g.model,
                        dimension_column: c.dimension.column,
                        measure_column: c.measure.column,
                        chart_type: c.chart_type,
                        title: c.title,
                    });
                }
            });
        });
        return picks;
    }

    async onCreate() {
        const picks = this.checkedPicks;
        if (!picks.length || !this.state.name.trim() || this.state.step === "creating") {
            return;
        }
        this.state.step = "creating";
        this.state.error = "";
        try {
            this.state.dashboard = await this.orm.call(
                "dashboard.sheet", "create_quick_dashboard",
                [this.state.name.trim(), picks]);
            this.state.step = "done";
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message) || "Could not create the dashboard.";
            this.state.step = "review";
        }
    }

    openDashboard() {
        if (!this.state.dashboard) {
            return;
        }
        // The dashboard client action reads the config id from context.rec_id.
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cy_analytic_dashboard",
            target: "current",
            context: { rec_id: this.state.dashboard.dashboard_id },
        });
    }

    // -- shared state mutations (used by both the UI and chat patches) -------

    _addModel({ model, name }) {
        if (model && !this.state.models.some((m) => m.model === model)) {
            this.state.models.push({ model, name: name || model });
        }
    }

    _removeModel(model) {
        const i = this.state.models.findIndex((m) => m.model === model);
        if (i !== -1) {
            this.state.models.splice(i, 1);
        }
        const gi = this.state.groups.findIndex((g) => g.model === model);
        if (gi !== -1) {
            this.state.groups[gi].cards.forEach((c) => { delete this.state.selected[c.id]; });
            this.state.groups.splice(gi, 1);
        }
    }

    _findCard(id) {
        for (const g of this.state.groups) {
            for (const c of g.cards) {
                if (String(c.id) === String(id)) {
                    return c;
                }
            }
        }
        return null;
    }

    // -- conversational bridge (state ⇄ chat) --------------------------------

    /** Compact, agent-facing snapshot: tables + cards (id/title/type/allowed/
     *  kept) + name. Rides in the outgoing ui_context via CY_AI:QD_STATE. */
    _snapshot() {
        const cards = [];
        this.state.groups.forEach((g) => {
            g.cards.forEach((c) => cards.push({
                id: c.id,
                title: c.title,
                dimension: c.dimension && c.dimension.label,
                measure: c.measure && c.measure.label,
                chart_type: c.chart_type,
                allowed_chart_types: c.allowed_chart_types || [],
                selected: !!this.state.selected[c.id],
                model: g.model,
            }));
        });
        return {
            step: this.state.step,
            name: this.state.name,
            tables: this.state.models.map((m) => ({ model: m.model, name: m.name })),
            cards,
        };
    }

    _publish() {
        if (QuickDashboardWidget._active !== this) {
            return;   // only the active builder speaks for the chat
        }
        // Once the dashboard is CREATED, the builder is no longer the thing to
        // edit — the live dashboard is. Stop advertising it as an editable
        // builder so chat edits ("make it a pie") route to the created dashboard
        // (edit_dashboard), not a stale proposal card.
        if (this.state.step === "done") {
            this.env.bus.trigger("CY_AI:QD_CLEAR");
            return;
        }
        this.env.bus.trigger("CY_AI:QD_STATE", this._snapshot());
    }

    /** Apply an agent patch to this builder (see EditQuickDashboardTool). */
    async _onPatch(ev) {
        if (QuickDashboardWidget._active !== this) {
            return;
        }
        const p = (ev && ev.detail) || {};
        switch (p.action) {
            case "set_chart_type": {
                const c = this._findCard(p.card_id);
                if (c && (c.allowed_chart_types || []).includes(p.chart_type)) {
                    c.chart_type = p.chart_type;
                }
                break;
            }
            case "toggle_chart": {
                const c = this._findCard(p.card_id);
                if (c) {
                    this.state.selected[c.id] = !!p.selected;
                }
                break;
            }
            case "add_table": {
                if (p.model && !this.state.models.some((m) => m.model === p.model)) {
                    this._addModel({ model: p.model, name: p.name });
                    const g = await this._genGroupFor({ model: p.model, name: p.name || p.model });
                    if (g) {
                        this.state.groups.push(g);
                    }
                    if (this.state.step === "pick" || this.state.step === "proposing") {
                        this.state.step = "review";
                    }
                }
                break;
            }
            case "remove_table":
                this._removeModel(p.model);
                break;
            case "rename":
                if (p.name) {
                    this.state.name = p.name;
                }
                break;
            case "create":
                await this.onCreate();
                break;
        }
        this._publish();
    }
}

registry.category("cyllo_ai.chat_widgets").add("quick_dashboard", QuickDashboardWidget);
