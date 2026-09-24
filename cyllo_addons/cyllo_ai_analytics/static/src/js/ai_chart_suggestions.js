/** @odoo-module **/
/**
 * AI Chart Suggestions — patches the analytics sheet builder (CylloSheet) so the
 * chart-suggestion experience lives INSIDE the cyllo_ai chatbot (Stage 2).
 *
 * Docking is declared via the "cyllo_ai.dock_contexts" registry (the chatbot
 * derives it from the current screen). On the sheet, this module also drives the
 * chatbot through generic bus verbs:
 *   - CY_AI:NUDGE / CLEAR_NUDGE     -> "Chart suggestions?" bubble beside the owl
 *   - CY_AI:SET_OFFER / CLEAR_OFFER -> "Generate charts" button in the greeting
 * and listens for:
 *   - CY_AI:CHAT_ACTION (gen_charts)   -> generate + push suggestion cards
 *   - CY_AI:APPLY_SUGGESTION           -> apply a card to the sheet
 *
 * Apply reuses the sheet's OWN pipeline: buildAxisEntry (the exact axis builder
 * drag-drop uses) + the CY:UPDATE_QUERY bus + onClickSheetType — so an applied
 * suggestion is identical to the user dragging the fields and picking the type.
 */
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { CylloSheet } from "@cyllo_analytics/js/cyllo_sheet";
import { buildAxisEntry } from "@cyllo_analytics/js/drag_n_drop";

const { useEffect, onMounted, onWillUnmount } = owl;

// Identifies this module's nudge/offer/action among any others the chatbot shows.
const NUDGE_KEY = "analytics_charts";
const OFFER_KEY = "gen_charts";

// Dock the chatbot's expanded form on the sheet builder client action. The
// chatbot derives docking from the current screen, so we just declare the
// context here (no lifecycle events to keep in sync).
registry.category("cyllo_ai.dock_contexts").add("cy_analytic_sheet", "cy_analytic_sheet");

patch(CylloSheet.prototype, {
    setup() {
        super.setup();

        // Mark the body while the analytics sheet is open, so the docked chat's
        // split-layout CSS applies here: `body.cy-sheet-active.cy-ai-docked-open
        // .o_action_manager` reserves a right gutter the width of the chat rail,
        // and the fluid sheet reflows BESIDE the chat instead of being overlaid.
        // Paired with removal on unmount so it never leaks to other screens.
        onMounted(() => document.body.classList.add("cy-sheet-active"));

        // Keep the chatbot in sync with the sheet: push the available fields +
        // current chart (for the suggest/edit tools), and fire the nudge/offer.
        // Re-runs whenever the tables, chart type, dimension or measure change,
        // so `current_chart` stays fresh for edits. Start prev at 0 so an
        // existing sheet gets the nudge/offer on load.
        this._aiPrevTableCount = 0;
        this._lastAppliedSuggestion = null;
        useEffect(
            () => {
                const count = (this.state.models || []).length;
                this._pushAiQueryContext(count);
                // Nudge + offer only on the 0 -> first-table transition.
                const prev = this._aiPrevTableCount;
                this._aiPrevTableCount = count;
                if (prev === 0 && count > 0) {
                    // freshPolicy "always": the "Generate charts" offer lives in
                    // the empty state, so clicking the bubble starts a fresh thread.
                    this.env.bus.trigger("CY_AI:NUDGE", {
                        label: "Chart suggestions?", key: NUDGE_KEY,
                        mode: "analytics_suggest", freshPolicy: "always",
                    });
                    this.env.bus.trigger("CY_AI:SET_OFFER", {
                        label: "Generate charts", key: OFFER_KEY,
                        mode: "analytics_suggest", freshPolicy: "always",
                        autoFresh: true,
                    });
                } else if (prev > 0 && count === 0) {
                    this.env.bus.trigger("CY_AI:CLEAR_NUDGE");
                    this.env.bus.trigger("CY_AI:CLEAR_OFFER");
                }
            },
            () => [
                (this.state.models || []).map((m) => m.id || m.table).join(","),
                this.state.selectedType && this.state.selectedType[1],
                (this.query_data.dimension || []).map((d) => d.column).join(","),
                (this.query_data.measure || []).map((m) => m.column).join(","),
            ],
        );

        // The greeting's "Generate charts" offer was clicked -> load suggestions
        // and push them into the chat as cards.
        useBus(this.env.bus, "CY_AI:CHAT_ACTION", (ev) => {
            if (ev.detail?.key === OFFER_KEY) {
                this._generateChartSuggestions();
            }
        });

        // A suggestion card's Apply button was clicked in the chat.
        useBus(this.env.bus, "CY_AI:APPLY_SUGGESTION", (ev) => {
            const suggestion = ev.detail?.suggestion;
            if (suggestion) {
                this.applyAiSuggestion(suggestion);
            }
        });

        // A direct edit from chat ("make it a pie", "by customer"): apply it to
        // the live chart. A full suggestion -> rebuild; a bare type -> just swap.
        useBus(this.env.bus, "CY_AI:APPLY_EDIT", (ev) => {
            const edit = ev.detail || {};
            if (edit.suggestion) {
                this.applyAiSuggestion(edit.suggestion);
            } else if (edit.chart_type) {
                const st = (this.state.sheetTypes || []).find((s) => s.ttype === edit.chart_type);
                if (st) {
                    this.onClickSheetType([st.id, st.ttype]);
                }
            }
        });

        // Don't leave our nudge / offer / query-context active after we leave
        // the sheet. (Docking is derived from the screen by the chatbot itself.)
        onWillUnmount(() => {
            document.body.classList.remove("cy-sheet-active");
            this.env.bus.trigger("CY_AI:CLEAR_NUDGE");
            this.env.bus.trigger("CY_AI:CLEAR_OFFER");
            this.env.bus.trigger("CY_AI:CLEAR_QUERY_CONTEXT");
        });
    },

    /** Push the sheet's available fields + current chart to the chatbot so the
     *  agent's suggest/edit tools can read them from ui_context. Clears when the
     *  sheet has no tables. */
    _pushAiQueryContext(count) {
        if (!count) {
            this.env.bus.trigger("CY_AI:CLEAR_QUERY_CONTEXT");
            return;
        }
        this.env.bus.trigger("CY_AI:SET_QUERY_CONTEXT", {
            sheet_id: this.state.id,
            dimensions: this.dimensions,
            measures: this.measures,
            current_chart: this._aiCurrentChart(),
        });
    },

    /** Describe the chart currently on the sheet for the edit tool. The dim/
     *  measure columns come from the last applied suggestion (the ORIGINAL
     *  available columns, which the tool can match), with labels as a fallback
     *  when the chart was built manually. */
    _aiCurrentChart() {
        const last = this._lastAppliedSuggestion;
        const dim0 = (this.query_data.dimension || [])[0];
        const meas0 = (this.query_data.measure || [])[0];
        return {
            chart_type: this.state.selectedType && this.state.selectedType[1],
            dimension: {
                column: last?.dimension?.column || null,
                label: last?.dimension?.base_label || last?.dimension?.label || dim0?.value || null,
            },
            measure: {
                column: last?.measure?.column || null,
                label: last?.measure?.label || meas0?.value || null,
            },
        };
    },

    /** Load suggestions from the sheet's available fields and push them into the
     *  chat as a bot message with Apply cards. */
    async _generateChartSuggestions() {
        let suggestions = [];
        try {
            suggestions = await this.orm.call(
                "dashboard.sheet",
                "suggest_charts_for_sheet",
                [[this.state.id], this.dimensions, this.measures],
            );
        } catch (e) {
            this.notification.add("Could not load chart suggestions.", { type: "warning" });
        }
        suggestions = suggestions || [];
        const html = suggestions.length
            ? "Based on your fields, the most relevant charts:"
            : "I couldn't find useful chart pairings — add a few more dimension/measure fields and try again.";
        this.env.bus.trigger("CY_AI:PUSH_MESSAGE", { html, suggestions });
    },

    /**
     * Apply a suggestion as a fresh, self-contained chart.
     *
     * The sheet only runs a query when `isGoodQuery` (measure.length &&
     * join.length) is true, so we keep the MEASURE EMPTY while we reset and
     * rebuild — every intermediate state short-circuits (no DB hit, no toast) —
     * and set the measure LAST. Result: exactly one query, on the final
     * consistent state. Reset drops join tables left over from prior Applies
     * (option 1) so accumulated INNER JOINs can't filter the result to nothing.
     */
    async applyAiSuggestion(suggestion) {
        // Remember what's on the sheet so the edit tool can refine it later.
        this._lastAppliedSuggestion = suggestion;
        const companyId = this.company.currentCompany?.id;
        const dim = suggestion.dimension;
        const measure = suggestion.measure;

        // Build the measure entry now, but DO NOT apply it until the very end.
        const measEntry = await buildAxisEntry({
            column: measure.column,
            value: measure.label,
            type: "measure",
            field_type: measure.field_type,
            is_json: measure.is_json,
        }, { companyId, orm: this.orm });

        // 1. Empty the measure -> isGoodQuery is false -> no query runs below.
        this.query_data.measure = [];
        this.env.bus.trigger("CY:SYNC_CHILDREN", { targetType: "measure", children: [] });

        // 2. Reset to the main table (drop prior Applies' join tables + columns).
        this._resetToMainTable();

        // 3. Axis + dimension (relational adds its own join) + chart type.
        this.env.bus.trigger("CY:UPDATE_QUERY", { type: "dimension_axis", data: "x" });
        if (dim.field_type === "many2one" && dim.display_field) {
            await this.applyRelationalNameDimension(dim);
        } else {
            const dimEntry = await buildAxisEntry({
                column: dim.column,
                value: dim.label,
                type: "dimension",
                field_type: dim.field_type,
                is_json: dim.is_json,
            }, { companyId, orm: this.orm });
            this.env.bus.trigger("CY:UPDATE_QUERY", { type: "dimension", data: [dimEntry] });
        }
        const st = (this.state.sheetTypes || []).find(s => s.ttype === suggestion.chart_type);
        if (st) {
            this.onClickSheetType([st.id, st.ttype]);
        }

        // Sync the join array to the current tables SYNCHRONOUSLY. ModelViewer
        // refreshes query_data.join reactively (after render), which lags behind
        // the measure we set next — so without this, the one query that runs can
        // reference a just-added related table before its join is in the FROM.
        this.query_data.join = this.state.models.map((m) => m.linked_by?.join).filter(Boolean);
        this.query_data.joinData = this.state.models.map((m) => ({ ...m.linked_by, model_id: m.id }));

        // 4. Measure LAST -> isGoodQuery flips true -> ONE query, final state.
        this.env.bus.trigger("CY:UPDATE_QUERY", { type: "measure", data: [measEntry] });
    },

    /**
     * Reset the sheet to its main (user-selected) table: drop the join tables
     * added by previous Applies and clear the old columns. Linked tables have a
     * "JOIN …" join string; the main table's is just the table name.
     */
    _resetToMainTable() {
        const isLinked = (m) => /^\s*JOIN\b/i.test((m.linked_by && m.linked_by.join) || "");
        // Track removed links so Save unlinks them from the DB.
        for (const m of this.state.models) {
            if (isLinked(m) && m.linked_by?.id) {
                this.unlinkList.tables.push(m.linked_by.id);
            }
        }
        const mainModels = this.state.models.filter((m) => !isLinked(m));
        this.state.models = mainModels;
        // Clear columns that may reference the dropped tables.
        this.query_data.dimension = [];
        this.query_data.groupBy = [];
        this.query_data.orderBy = [];
        for (const t of ["dimension", "groupBy", "orderBy"]) {
            this.env.bus.trigger("CY:SYNC_CHILDREN", { targetType: t, children: [] });
        }
        // Rebuild join/joinData from the remaining (main) tables.
        this.query_data.join = mainModels.map((m) => m.linked_by?.join).filter(Boolean);
        this.query_data.joinData = mainModels.map((m) => ({ ...m.linked_by, model_id: m.id }));
    },

    /**
     * Apply a many2one suggestion by its display name through the sheet's own
     * relational path (_applyRelationalSelection) — the same code the manual
     * "traverse to Name" wizard runs, so the join, column and metadata match.
     */
    async applyRelationalNameDimension(dim) {
        const selection = {
            rootModel: { table: dim.rel_table, name: dim.rel_model_name, id: dim.rel_model_id },
            path: [],
            field: {
                table: dim.rel_table,
                name: dim.display_field,
                type: dim.display_field_type,
                label: dim.display_field_label,
                is_json: dim.display_field_is_json,
            },
        };
        const baseField = { column: dim.column, label: dim.base_label };
        await this._applyRelationalSelection(baseField, selection, "dimension", "x");
    },
});
