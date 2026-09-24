/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted, useRef } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";
import { GraphTile } from "@cyllo_analytics/js/presentation/components/graph_tile";
import { _t } from "@web/core/l10n/translation";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { download } from "@web/core/network/download";
import { FilterDropdown } from "@cyllo_analytics/js/filterDropdown"
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ConnectionAbortedError } from "@web/core/network/rpc_service";

const PERIODS = {
    quarter: 'Quarter',
    year: 'Year',
    month: 'Month',
    six_months: 'Half Year',
    current_date: 'current_date',
    financial_year: 'financial_year',
}

export class ChurnPredictionDashboard extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService('orm')
        this.notification = useService("notification");
        this.root = useRef("root")
        this.savedContext = useSaveContext()
        this.period = useRef("period")
        this.periodType = useRef("period_type")
        this.input = useRef("input")
        this.actionService = useService("action")

        // Monotonic token used to cancel/supersede an in-flight training run.
        // cancelTraining() bumps it so a still-pending result is ignored.
        this._loadToken = 0;
        // Snapshot of the selection (period/quarters/config) that produced the
        // currently-displayed result. Used to revert the UI when a run is cancelled.
        this._committedSelection = null;

        let defaultConfig = {
            algorithm: 'xgboost',
            cutoff: 80,
            fields: [
                {name: 'sale_count', weight: 40, fixed: true},
                {name: 'sale_total', weight: 40, fixed: true},
                {name: 'recency', weight: 20, fixed: true}
            ]
        };

        this.state = useState({
            churnData: [],
            labels: {},                  // translated churn labels (from backend)
            numberOfPeriods: 4,
            period: 'Quarter',
            periodType: 'current_date',
            generate: false,
            churnChart: false,
            offset: 0,
            arr: [],
            data: [],
            heading: [],
            count: 0,
            min: 0,
            searchText: false,
            predictData: true,
            selectedCustomerId: null,
            // `restoring` shows a plain "loading saved results" page while we try
            // to restore a previously stored result on open (no training). Only
            // if nothing is stored do we fall through to training, which flips
            // `loading` on and shows the cancellable training overlay.
            restoring: true,
            loading: false,              // true while the (heavy) churn TRAINING runs
            cancelled: false,            // training was cancelled and no result is shown
            availableFields: [],
            config: JSON.parse(JSON.stringify(defaultConfig)), // current dynamic config
        });

        this.defaultConfig = defaultConfig; // Master default

        // onWillStart only restores the lightweight saved filters/config (no server
        // calls) so the page shell paints immediately instead of blocking on the
        // heavy churn computation.
        onWillStart(async () => {
            // Translated churn labels (reliable Python path, fetched directly).
            this.state.labels = await this.orm.call('res.partner', 'get_churn_labels', []);
            var period, periodType, numberOfPeriods, config
            if (!this.savedContext?.state) {
                ({ period, periodType, numberOfPeriods, config } = this.state)
            } else {
                ({ period, periodType, numberOfPeriods, config } = this.savedContext.state)
            }
            this.state.period = period
            this.state.periodType = periodType;
            this.state.numberOfPeriods = numberOfPeriods;
            if (config) {
                this.state.config = config;
                this.state.config.fields = this.state.config.fields.map(f => {
                    if (f.name === 'sale_count' || f.name === 'sale_total' || f.name === 'recency') {
                        f.fixed = true;
                    }
                    return f;
                });
            }
        })

        // Heavy work runs AFTER the first paint: the shell + a loading spinner show
        // instantly, then the churn data streams in.
        onMounted(async () => {
            await this.restoreOrTrain();
        })
    }

    // Open behaviour, mirroring Sales Forecasting: first try to restore a
    // previously stored result (a plain loading page, no training). Only when
    // nothing is stored do we run the training, which shows the cancellable
    // "Computing churn prediction…" overlay. This stops a re-open of the menu
    // from re-training when a result already exists.
    async restoreOrTrain() {
        this.state.restoring = true;
        try {
            // availableFields backs the config editor; load it once up-front so
            // it's ready whether we end up restoring or training.
            if (!this.state.availableFields || !this.state.availableFields.length) {
                this.state.availableFields = await this.orm.searchRead('ir.model.fields', [
                    ['model', '=', 'sale.order'],
                    ['ttype', 'in', ['integer', 'float', 'monetary']],
                    ['store', '=', true]
                ], ['name', 'field_description', 'ttype']);
            }
            const stored = await this.orm.call('res.partner', 'get_stored_churn', [
                this.state.period, this.state.periodType,
                this.state.numberOfPeriods, this.state.config,
            ]);
            if (stored) {
                this.applyChurnData(stored);
                return;
            }
        } catch (e) {
            console.error(e);
        } finally {
            this.state.restoring = false;
        }
        // Nothing stored yet -> run the training (shows the training overlay).
        await this.loadChurn(false);
    }

    // Load available fields (lazily, once) and the churn data, toggling the
    // loading state so the UI shows a spinner instead of freezing.
    async loadChurn(force) {
        const token = ++this._loadToken;
        this.state.loading = true;
        this.state.cancelled = false;
        try {
            if (!this.state.availableFields || !this.state.availableFields.length) {
                this.state.availableFields = await this.orm.searchRead('ir.model.fields', [
                    ['model', '=', 'sale.order'],
                    ['ttype', 'in', ['integer', 'float', 'monetary']],
                    ['store', '=', true]
                ], ['name', 'field_description', 'ttype']);
            }
            await this.renderChurnData(force, token);
        } catch (e) {
            // A user-initiated Cancel aborts the request on purpose — that is not
            // an error, so don't log it or let it bubble to Odoo's error handler.
            if (!(e instanceof ConnectionAbortedError)) {
                console.error(e);
            }
        } finally {
            // Only clear loading if this run is still the current one — a
            // cancel or a newer run must not hide the active overlay/spinner.
            if (token === this._loadToken) {
                this.state.loading = false;
            }
        }
    }

    // Stop the current training, ignore its (still-pending) result, and return
    // to the normal UI. Also reverts the selection (period/quarters/config) back
    // to the last successfully-applied values so the cancelled, not-yet-applied
    // changes don't linger in the inputs.
    cancelTraining() {
        this._loadToken++;
        this.state.loading = false;
        // Actually abort the in-flight training request instead of only ignoring
        // its result. Previously the heavy request kept running after Cancel; on a
        // slow/neutralised DB it would later time out and Odoo's connection-lost
        // handling reloaded the action — the "page exits a few seconds after
        // Cancel" symptom. abort(false) stops the request and unblocks the UI
        // without surfacing an error.
        if (this._pendingChurnRequest && this._pendingChurnRequest.abort) {
            this._pendingChurnRequest.abort(false);
        }
        this._pendingChurnRequest = null;
        // If there is no result to fall back to (e.g. cancelled the very first
        // run), show a clean "cancelled" panel instead of an empty results page.
        this.state.cancelled = !this.state.generate;
        if (this._committedSelection) {
            this.state.period = this._committedSelection.period;
            this.state.periodType = this._committedSelection.periodType;
            this.state.numberOfPeriods = this._committedSelection.numberOfPeriods;
            this.state.config = JSON.parse(JSON.stringify(this._committedSelection.config));
            // The quarters field is bound with t-att-value (not t-model), so its
            // DOM value won't refresh from state alone — set it explicitly.
            if (this.input && this.input.el) {
                this.input.el.value = this.state.numberOfPeriods;
            }
            // Keep the persisted filter/config in sync with the reverted state.
            this.savedContext?.saveManually(this.state, "state");
        }
    }

    updateConfigField(index, key, value) {
        if (key === 'weight') {
            value = parseInt(value) || 0;
        }
        this.state.config.fields[index][key] = value;
    }

    addConfigField() {
        const firstAvailable = (this.state.availableFields || [])[0];
        this.state.config.fields.push({
            name: firstAvailable ? firstAvailable.name : '',
            weight: 0,
        });
    }

    removeConfigField(index) {
        this.state.config.fields.splice(index, 1);
    }

    onDiscardConfig(ev) {
        if (ev) { ev.preventDefault(); ev.stopPropagation(); }
        // Reset to exactly xgboost, 80%, and 50/50 fields
        this.state.config = JSON.parse(JSON.stringify(this.defaultConfig));
        this.renderChurnData();
        this.savedContext.saveManually(this.state, "state");
        this.notification.add(_t("Configuration discarded. Reset to defaults."), { type: "info" });
        const btn = document.getElementById('configDropdownButton');
        if (btn) {
            btn.click(); // Close the dropdown on discard
        }
    }

    onSaveConfig(ev) {
        if (ev) { ev.preventDefault(); ev.stopPropagation(); }
        // Every row must name a field, otherwise the query has nothing to sum
        if (this.state.config.fields.some((f) => !f.name)) {
            this.notification.add(_t("Please choose a field for every line."), { type: "danger" });
            return;
        }
        // Validate total weight sums to 100
        let total = this.state.config.fields.reduce((acc, f) => acc + f.weight, 0);
        if (total !== 100) {
            this.notification.add(_t("Total weightage must equal exactly 100%."), { type: "danger" });
            return;
        }
        this.renderChurnData();
        this.savedContext.saveManually(this.state, "state");
        this.notification.add(_t("Configuration saved successfully! ML Engine updated."), { type: "success" });
        const btn = document.getElementById('configDropdownButton');
        if (btn) {
            btn.click(); // Close the dropdown since no error
        }
    }

    async onChangePeriod() {
        if (this.input.el.value < 4) {
            this.input.el.value = 4
            this.state.numberOfPeriods = 4
            this.notification.add(_t("Number of periods must be at least 4"), {
                type: "warning",
            });
            this.loadChurn(true)
        } else {
            this.state.period = PERIODS[this.period.el.value];
            this.state.periodType = PERIODS[this.periodType.el.value];
            this.state.numberOfPeriods = this.input.el.value
            this.loadChurn(true)
            this.savedContext.saveManually(this.state, "state")
        }
    }

    // Translated churn label (from backend-provided labels; falls back to key).
    churnLabel(key) {
        const labels = this.state.labels;
        return (labels && labels[key]) || key;
    }

    async renderChurnData(force, token) {
        // If no token was passed (config save/discard callers), take a fresh one
        // so a cancel/supersede still invalidates this result.
        const t = (token !== undefined) ? token : (++this._loadToken);
        // Keep a handle on the in-flight request so cancelTraining() can truly
        // abort it (not just ignore the result). orm.call returns the abortable
        // rpc promise directly.
        this._pendingChurnRequest = this.orm.call('res.partner', 'get_date_range', [this.state.period, this.state.periodType, this.state.numberOfPeriods, this.state.config, !!force]);
        let churnData;
        try {
            churnData = await this._pendingChurnRequest;
        } finally {
            this._pendingChurnRequest = null;
        }
        // Training was cancelled or superseded while this request was in flight.
        if (t !== this._loadToken) {
            return;
        }
        this.applyChurnData(churnData);
    }

    // Render a churn result (from a fresh training run OR a restored stored
    // result) into the dashboard state. Kept separate from the fetch so the
    // restore-on-open path can reuse the exact same rendering.
    applyChurnData(churnData) {
        // A result is being shown -> clear any prior "cancelled" panel.
        this.state.cancelled = false;
        // Record the selection that produced this result so a later cancel can
        // revert quarters / period / algorithm / fields back to these values.
        this._committedSelection = {
            period: this.state.period,
            periodType: this.state.periodType,
            numberOfPeriods: this.state.numberOfPeriods,
            config: JSON.parse(JSON.stringify(this.state.config)),
        };
        this.state.churnData = churnData;
        this.state.predictData = this.state.churnData.predict;
        if (this.state.predictData) {
            this.state.min = this.state.churnData.cust_wise_details.length > 6 ? 6 : this.state.churnData.cust_wise_details.length;
            this.state.count = this.state.churnData.cust_wise_details.length
            let props = {
                data: [{ value: this.state.churnData.churn_perc, name: this.churnLabel('at_risk'), itemStyle: { color: '#ff3333' } },
                { value: this.state.churnData.waiting_perc || 0, name: this.churnLabel('waiting'), itemStyle: { color: '#f9aa4f' } },
                { value: this.state.churnData.not_churn_perc, name: this.churnLabel('loyal'), itemStyle: { color: '#9ea700' } }],
                measures: ['value', 'itemStyle'],
                dimension: 'name',
                dimension_axis: 'y',
                type: 'pie',
                id: 'churn_main_chart',
                hidePieSliceLabels: true,
                pieLegendBottom: true,
            }
            this.state.churnChart = props
            this.state.generate = true
            this.onClickCustomer(this.state.churnData.cust_wise_details[0]);
            this.setArr()
        }
    }

    /** Marks the row as selected. The per-customer pie it used to feed was
     *  removed, so no chart props are built here any more. */
    onClickCustomer(cust) {
        this.state.selectedCustomerId = cust.custId
    }

    async exportPDF() {
        var head = this.root.el?.querySelector('.churn_prediction-graph_img')
        if (head) {
            var canvas = await html2canvas(head)
            head = canvas.toDataURL('image/png');
        }
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: 'cyllo_sale_analytics.report_churn_prediction',
            report_file: "cyllo_sale_analytics.report_churn_prediction",
            data: {
                head,
                'churnData': this.state.churnData,
                'period': this.state.period,
                'numberOfPeriods': this.state.numberOfPeriods
            }
        });
    }
    async exportXLSX() {
        try {
            await download({
                url: '/smartd_xlsx_reports',
                data: {
                    'model': 'res.partner',
                    'data': JSON.stringify(this.state),
                    'output_format': 'xlsx',
                    'report_name': 'Churn Prediction',
                },
            });
        } catch (error) {
            this.notification.add(
                _t("Could not download the report. Please try again."),
                { type: "danger" });
        }
    }

    onInputCustomer(ev) {
        this.state.searchText = ev.toLowerCase();
        this.state.offset = 0;
        this.setArr()
    }

    // ---------------------------------------------------------------------
    // Churn table helpers
    // ---------------------------------------------------------------------

    /** Customers the model could not classify either way yet. */
    get waitingCount() {
        const rows = this.state.churnData?.cust_wise_details || [];
        return rows.filter((c) => c.Churn === 'Waiting').length;
    }

    /** Confirmed sale orders behind the analysed customers. */
    get totalOrders() {
        const rows = this.state.churnData?.cust_wise_details || [];
        return rows.reduce((sum, c) => sum + (parseFloat(c.total_sales) || 0), 0);
    }

    /** Churn probability of a customer, 0-100, as shown by the risk bar. */
    riskPercent(cust) {
        return Math.round(parseFloat(cust?.prob_yes) || 0);
    }


    get showingLabel() {
        const total = this.state.count || 0;
        if (!total) return _t("No entries");
        const from = this.state.offset + 1;
        const to = Math.min(this.state.offset + this.state.min, total);
        return _t("Showing %s to %s of %s entries", from, to, total);
    }

    /**
     * Drag-to-pan for the churn table: the horizontal scrollbar is hidden, so
     * the middle columns are moved by grabbing the table instead. Ignores
     * drags that start on a link/button so row actions keep working.
     */
    onTablePointerDown(ev) {
        const scroller = ev.currentTarget;
        if (ev.button !== 0 || ev.target.closest("a, button, input")) return;
        const startX = ev.clientX;
        const startLeft = scroller.scrollLeft;
        let dragged = false;

        const move = (e) => {
            const dx = e.clientX - startX;
            if (Math.abs(dx) > 3) dragged = true;
            scroller.scrollLeft = startLeft - dx;
        };
        const up = () => {
            window.removeEventListener("pointermove", move);
            window.removeEventListener("pointerup", up);
            scroller.classList.remove("cy-churn_table--dragging");
            // swallow the click that ends a real drag, so it does not also
            // select the row underneath
            if (dragged) {
                scroller.addEventListener("click", (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                }, { capture: true, once: true });
            }
        };
        scroller.classList.add("cy-churn_table--dragging");
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
    }

    // ---------------------------------------------------------------------
    // KPI card captions. The card artwork is fixed decorative SVG in the
    // template; only the caption below it reflects real data.
    // ---------------------------------------------------------------------
    _series(key) {
        const trends = this.state.churnData?.kpi_trends;
        const values = trends ? trends[key] : null;
        return Array.isArray(values) && values.length > 1 ? values : null;
    }



    /** Caption under each KPI, derived from the same series. */
    kpiStatus(key) {
        const values = this._series(key);
        const data = this.state.churnData || {};
        if (key === "analyzed") {
            // total_cust counts partners flagged as customers while active_cust
            // counts those with orders, so the ratio can exceed 1 -- clamp it.
            const total = data.total_cust || 0;
            const raw = total ? Math.round((data.active_cust / total) * 100) : 0;
            return { text: _t("%s% Completed", Math.min(raw, 100)), tone: "ok" };
        }
        if (key === "at_risk") {
            const perc = parseFloat(data.churn_perc) || 0;
            if (perc <= 0) return { text: _t("Excellent"), tone: "ok" };
            if (perc < 20) return { text: _t("Healthy"), tone: "ok" };
            return { text: _t("Needs attention"), tone: "warn" };
        }
        if (!values) return { text: _t("No change"), tone: "ok" };
        const last = values[values.length - 1], prev = values[values.length - 2];
        const diff = last - prev;
        if (!diff) return { text: _t("No change"), tone: "ok" };
        const pct = prev ? Math.abs((diff / prev) * 100).toFixed(2) : 100;
        return {
            text: diff > 0 ? _t("%s% up on last period", pct)
                           : _t("%s% down on last period", pct),
            tone: diff > 0 ? "ok" : "warn",
            arrow: diff > 0 ? "ri-arrow-up-line" : "ri-arrow-down-line",
        };
    }

    get chartStyle() {
        return {
            height: `320px`,
            width: `400px`,
        }
    }
    onClickCustomerDetails(cust) {
        return this.actionService.doAction({
            target: "current",
            tag: "cyllo_sale_analytics.customer_details",
            type: "ir.actions.client",
            context: {
                cust: cust,
                dateRange: this.state.churnData.date_range,
                dateRangeIso: this.state.churnData.date_range_iso,
                period: this.state.period
            }
        })
    }
    get hasNext() {
        return this.state.offset + this.state.min < this.state.count;
    }
    get hasPrev() {
        return this.state.offset > 0;
    }
    onClick(num) {
        this.state.offset += this.state.min * num
        this.setArr()
    }
    setArr() {
        const pageSize = 6;  // You can set this to any number
        const start = this.state.offset;
        const end = start + pageSize;

        this.state.min = pageSize;  // Update the state's page size
        this.state.arr = this.createArray(start, end);
    }

    createArray(start, end) {
        const result = [];
        if (this.state.searchText) {
            const filteredData = this.state.churnData.cust_wise_details.filter(item => {
                return item.custName && item.custName.toLowerCase().includes(this.state.searchText);
            });
            if (filteredData) {
                this.state.count = filteredData.length
                for (let i = start; i < end && i < filteredData.length; i++) {
                    result.push(filteredData[i]);
                }
            }
        }
        else {
            const allData = this.state.churnData.cust_wise_details;
            this.state.count = allData.length;
            for (let i = start; i < end && i < allData.length; i++) {
                result.push(this.state.churnData.cust_wise_details[i]);
            }
        }
        return result;
    }
    onClickFrequency(cust) {
        const dateRangeIso = this.state.churnData.date_range_iso;
        const lastIndex = dateRangeIso.length - 1;
        // Match the churn "Total Sale Orders" count, which only considers
        // confirmed/done orders (state in sale/done) — not quotations or
        // cancelled orders. Without this the drill-down over-counts.
        const domain = [['date_order', '>=', dateRangeIso[0][0]], ['date_order', '<=', dateRangeIso[lastIndex][1]], ['partner_id', '=', cust.custId], ['state', 'in', ['sale', 'done']]];
        this.actionService.doAction({
            name: "Sale orders of " + cust.custName + " from " + this.state.churnData.date_range[0][0] + " to "
                + this.state.churnData.date_range[this.state.churnData.date_range.length - 1][1],
            res_model: "sale.order",
            views: [[false, "tree"], [false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "tree",
            domain: domain,
            target: "current",
        });
    }
    formatNumber(value) {
        if (!value) return ''
        if (value >= 1e18) {
            return (value / 1e18).toFixed(2) + 'Qi';
        } else if (value >= 1e15) {
            return (value / 1e15).toFixed(2) + 'Q';
        } else if (value >= 1e12) {
            return (value / 1e12).toFixed(2) + 'T';
        } else if (value >= 1e9) {
            return (value / 1e9).toFixed(2) + 'B';
        } else if (value >= 1e6) {
            return (value / 1e6).toFixed(2) + 'M';
        } else if (value >= 1e3) {
            return (value / 1e3).toFixed(2) + 'K';
        } else {
            return value.toString();
        }
    }
}

ChurnPredictionDashboard.template = "ChurnPredictionDashboard";
ChurnPredictionDashboard.components = { GraphTile, FilterDropdown, Dropdown, DropdownItem }
registry.category("actions").add("churn_prediction", ChurnPredictionDashboard);