/** @odoo-module **/
import { registry } from "@web/core/registry"
import { onMounted, onWillUnmount, useState, Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import owlForecastAnimation from "../lottie/owl_forecast.js";


export class SalesPredictionDashboard extends Component {
    setup() {
        const defaultState = {
            // Start in a neutral loading state; checkSavedForecast() then either
            // opens the results view (saved forecast found) or falls back to the
            // guidelines screen. This avoids the guidelines page flashing before
            // a saved forecast is restored on every menu open.
            status: 'loading',
            startDate: '',
            endDate: '',
            startDateInvalid: false,   // red highlight when Start Date missing/invalid
            endDateInvalid: false,     // red highlight when End Date missing/invalid
            downloading: false,        // XLSX download in progress (shows a spinner)
            aggregate: 'M',
            mode: 'algorithm',
            keywords: '',            // AI mode: comma-separated news search keywords
            panelKeywords: '',       // keywords edited inside the on-chart news panel
            showNewsPanel: false,    // on-chart news/keyword side panel visibility
            recomputing: false,      // recompute-in-progress flag
            activeTab: 'chart',
            activeSubTab: 'main',   // 'main' | 'product' | 'customer'
            hasForecast: false,
            customFields: {
                customer_info: true,
                sale_order_amount: true,
                order_date: true,
                campaign_id: false,
                opportunity_id: false,
                leads_opportunities: false,
                holidays: false,
                website_visitors: false,
                product_features: false,
                seasonality: false,
                active_customer: false
            },
            irFieldsList: [],
            searchIrField: '',
            selectedIrFields: {},
            tableDataPreview: [],
            tableColumns: [],
            columnLabels: {},   // English column key -> translated display label
            predefinedLabels: {},   // predefined-field key -> translated label (from backend)
            totalRows: 0,
            availableFields: [],
            // Sub-table state (populated when aggregate != 'D')
            saleOrdersTableData: [],
            saleOrdersTableColumns: [],
            orderLinesTableData: [],
            orderLinesTableColumns: [],
            hasSubTables: false,
        };

        this.state = useState(defaultState);
        this.dataset = [];

        this.orm = useService('orm');

        // Readiness flags for the loading screen: the guidelines screen is only
        // revealed once both the data checks and the Lottie (owl) are loaded.
        this._dataReady = false;
        this._lottieDone = false;
        this._guidelinesFallbackTimer = null;
        this._owlLottieRetries = 0;
        this.owlLottieRef = useRef('owlLottie');
        this.procLottieRef = useRef('procLottie');

        onMounted(async () => {
            // Render the owl animation locally (bundled lottie player + local
            // JSON) — the old lottie.host iframe embed returned an empty page.
            this._initOwlAnimation();
            await this.loadIrFields();
            await this.checkSavedForecast();
            // No saved forecast restored -> show the guidelines landing screen,
            // but only after the owl animation finished loading as well.
            if (this.state.status === 'loading') {
                this._dataReady = true;
                // Fallback: don't keep the spinner forever if the Lottie
                // can't load (e.g. offline); reveal the screen anyway.
                this._guidelinesFallbackTimer = setTimeout(() => {
                    this._lottieDone = true;
                    this.maybeShowGuidelines();
                }, 5000);
                this.maybeShowGuidelines();
            }
        });

    onWillUnmount(() => {
        // Stop the animation and release its SVG when the dashboard closes.
        if (this._owlAnim) {
            this._owlAnim.destroy();
            this._owlAnim = null;
        }
        if (this._procAnim) {
            this._procAnim.destroy();
            this._procAnim = null;
        }
        clearTimeout(this._guidelinesFallbackTimer);
    });

    }

    // Reveal the guidelines screen only when both readiness flags are set.
    maybeShowGuidelines() {
        if (this.state.status !== 'loading' || !this._dataReady || !this._lottieDone) {
            return;
        }
        clearTimeout(this._guidelinesFallbackTimer);
        this._showGuidelines();
    }

    // Show the guidelines screen. Every time it is (re)entered, OWL renders a
    // NEW animation container, so the owl animation must be (re)started after
    // the render — otherwise it only ever mounts when the component happens to
    // mount on this screen (e.g. not when coming back via "New forecast").
    _showGuidelines() {
        this.state.status = 'guidelines';
        setTimeout(() => this._initOwlAnimation(), 0);
    }

    // Owl animation: rendered by the bundled lottie-web player. The
    // animation data is imported directly (no HTTP request — the old
    // lottie.host /embed/ endpoint returned an empty page, which is why
    // the iframe stayed blank).
    //
    // The player is normally part of the asset bundle, but if the bundle is
    // stale (module not upgraded since it was added) we fetch it directly
    // from the module's static files, so the owl always shows up.
    _loadLottiePlayer() {
        if (window.lottie) return Promise.resolve();
        if (!this._lottiePlayerPromise) {
            this._lottiePlayerPromise = new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/cyllo_sale_analytics/static/lib/lottie/lottie_light.min.js';
                script.onload = resolve;
                script.onerror = () => reject(new Error('lottie player script could not be loaded'));
                document.head.appendChild(script);
            });
        }
        return this._lottiePlayerPromise;
    }

    async _initOwlAnimation() {
        // Each entry into the guidelines screen renders a new container:
        // release the previous animation first.
        if (this._owlAnim) {
            this._owlAnim.destroy();
            this._owlAnim = null;
        }
        this._owlLottieRetries = 0;
        const el = this.owlLottieRef.el;
        if (!el) {
            // The guidelines screen (and its ref) may not be rendered yet.
            if (this._owlLottieRetries++ < 50) {
                setTimeout(() => this._initOwlAnimation(), 100);
            } else {
                console.warn("[sales_forecasting] owl animation container never appeared — is the guidelines screen mounted?");
            }
            return;
        }
        try {
            await this._loadLottiePlayer();
        } catch (e) {
            console.warn("[sales_forecasting] owl animation skipped:", e.message);
            return;
        }
        if (!this.owlLottieRef.el) return; // screen changed meanwhile
        this._owlAnim = window.lottie.loadAnimation({
            container: this.owlLottieRef.el,
            renderer: 'svg',
            loop: true,
            autoplay: true,
            animationData: JSON.parse(JSON.stringify(owlForecastAnimation)),
        });
        this._owlAnim.addEventListener('DOMLoaded', () => {
            this._lottieDone = true;
            this.maybeShowGuidelines();
        });
    }

    // Same local owl animation, shown on the "Processing Data" screen.
    // The screen is rendered by the same status flip that calls this, so the
    // ref can be one tick behind (or still point at the previous render) —
    // keep retrying until a LIVE container holds the animation.
    async _startProcessingAnimation() {
        try {
            await this._loadLottiePlayer();
        } catch (e) {
            console.warn("[sales_forecasting] processing animation skipped:", e.message);
            return;
        }
        this._procLottieRetries = 0;
        const start = () => {
            const el = this.procLottieRef.el;
            if (!el || !el.isConnected) {
                // Ref not mounted yet, or left over from the previous screen.
                if (this._procLottieRetries++ < 100) {
                    setTimeout(start, 100);
                } else {
                    console.warn("[sales_forecasting] processing animation container missing.");
                }
                return;
            }
            if (this._procAnim) {
                this._procAnim.destroy();
                this._procAnim = null;
            }
            el.innerHTML = "";
            this._procAnim = window.lottie.loadAnimation({
                container: el,
                renderer: 'svg',
                loop: true,
                autoplay: true,
                animationData: JSON.parse(JSON.stringify(owlForecastAnimation)),
            });
            // If the screen re-rendered while the player was booting, the SVG
            // lands in a detached node — move on to the live one.
            this._procAnim.addEventListener('DOMLoaded', () => {
                const node = this.procLottieRef.el;
                if ((!node || !node.isConnected || !node.querySelector('svg'))
                    && this._procLottieRetries++ < 100) {
                    setTimeout(start, 100);
                }
            });
        };
        setTimeout(start, 30);
    }

    // KPI stats for the "Generated training dataset" screen.
    get datasetStats() {
        const cols = this.state.tableColumns || [];
        const rows = Array.isArray(this.dataset) ? this.dataset : [];

        // Total amount: sum the first amount-like column of the full dataset.
        const amountKey = cols.find(c => /amount/i.test(c));
        let total = 0;
        if (amountKey) {
            total = rows.reduce((s, r) => s + (parseFloat(r[amountKey]) || 0), 0);
        }

        // Average trend/seasonality score, when such a column exists.
        const trendKey = cols.find(c => /score/i.test(c))
            || cols.find(c => /trend/i.test(c))
            || cols.find(c => /seasonality/i.test(c));
        let trend = null;
        if (trendKey && rows.length) {
            const vals = rows.map(r => parseFloat(r[trendKey])).filter(v => !isNaN(v));
            if (vals.length) {
                trend = vals.reduce((a, b) => a + b, 0) / vals.length;
            }
        }

        const aggLabels = { D: 'Days', W: 'Weeks', M: 'Months', Y: 'Years' };
        const aggPill = { D: 'Daily summaries', W: 'Weekly summaries', M: 'Monthly summaries', Y: 'Yearly summaries' };
        return {
            records: this.state.totalRows,
            aggregate: aggLabels[this.state.aggregate] || '',
            aggregateLabel: aggPill[this.state.aggregate] || 'Aggregated summaries',
            saleOrders: this.state.saleOrdersTableData.length,
            orderLines: this.state.orderLinesTableData.length,
            totalAmount: '$ ' + total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
            trendScore: trend === null ? '—' : trend.toFixed(2),
        };
    }

    async loadIrFields() {
        try {
            // Translated predefined-field labels (reliable Python translation path).
            this.state.predefinedLabels = await this.orm.call('sale.order', 'get_predefined_field_labels', []);

            const predefinedFields = [
                'amount_total', 'date_order', 'partner_id', 'opportunity_id',
                'campaign_id', 'website_id', 'id', 'name'
            ];

            const fields = await this.orm.searchRead(
                "ir.model.fields",
                [
                    ["model", "=", "sale.order"],
                    ["ttype", "in", ["char", "integer", "float", "monetary", "date", "datetime", "boolean", "selection"]]
                ],
                ["name", "field_description", "ttype"]
            );

            this.state.availableFields = fields.map(f => f.name);

            // Labels come translated from the server (reliable Python translation
            // path) instead of JS _t(), which depends on the web-translation bundle.
            const virtualFields = await this.orm.call('sale.order', 'get_virtual_forecast_fields', []);

            const typeLabels = {
                char: 'Char', integer: 'Integer', float: 'Float', monetary: 'Monetary',
                date: 'Date', datetime: 'Datetime', boolean: 'Boolean', selection: 'Selection',
            };
            for (const f of fields) {
                f.type_label = typeLabels[f.ttype] || f.ttype;
            }
            for (const f of virtualFields) {
                f.type_label = 'Derived';
            }

            const filteredFields = fields.filter(f => !predefinedFields.includes(f.name));
            filteredFields.push(...virtualFields);
            filteredFields.sort((a, b) =>
                a.field_description > b.field_description ? 1 : (b.field_description > a.field_description ? -1 : 0)
            );
            this.state.irFieldsList = filteredFields;

            for (let f of filteredFields) {
                this.state.selectedIrFields[f.name] = false;
            }
        } catch (e) {
            console.error(e);
        }
    }

    get filteredIrFields() {
        const search = this.state.searchIrField.toLowerCase();
        if (!search) return this.state.irFieldsList;
        return this.state.irFieldsList.filter(f =>
            f.field_description.toLowerCase().includes(search) ||
            f.name.toLowerCase().includes(search)
        );
    }

    // ── Dataset preview tables: cell rendering helpers ──
    // (kept for the status-pill / right-align / currency rendering)
    filterRows(rows) {
        return rows || [];
    }

    get filteredTableRows() {
        return this.filterRows(this.state.tableDataPreview);
    }

    get filteredSaleOrderRows() {
        return this.filterRows(this.state.saleOrdersTableData);
    }

    get filteredOrderLineRows() {
        return this.filterRows(this.state.orderLinesTableData);
    }

    isStatusCol(label) {
        return /^status/i.test(label || '');
    }

    isRightCol(label) {
        return /amount|lines\b|count|score|number|no\.? of|total|qty|quantity|holiday/i.test(label || '');
    }

    formatCell(value, label) {
        if (value === null || value === undefined || value === '') return value;
        if (typeof value === 'number') {
            if (/amount/i.test(label || '')) {
                return '$ ' + value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }
            return value.toLocaleString();
        }
        return value;
    }

    startWizard() { this.state.status = 'wizard'; }
    cancelWizard() { this._showGuidelines(); }
    setMode(mode) { this.state.mode = mode; }

    // Quick pick chips: fill the date range with a recent historical period.
    applyQuickPick(kind) {
        const end = new Date();
        const start = new Date();
        if (kind === '30d') {
            start.setDate(end.getDate() - 30);
        } else if (kind === 'quarter') {
            start.setMonth(end.getMonth() - 3);
        } else if (kind === '6m') {
            start.setMonth(end.getMonth() - 6);
        } else if (kind === '12m') {
            start.setFullYear(end.getFullYear() - 1);
        }
        const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        this.state.startDate = fmt(start);
        this.state.endDate = fmt(end);
        this.state.startDateInvalid = false;
        this.state.endDateInvalid = false;
    }

    // Live summary for the right-hand sidebar card.
    get wizardSummary() {
        const start = this.state.startDate ? new Date(this.state.startDate) : null;
        const end = this.state.endDate ? new Date(this.state.endDate) : null;
        let days = 0;
        if (start && end && !isNaN(start.getTime()) && !isNaN(end.getTime())) {
            days = Math.max(0, Math.round((end - start) / 86400000) + 1);
        }
        const aggLabels = { D: 'Daily', W: 'Weekly', M: 'Monthly', Y: 'Yearly' };
        const customCount = Object.values(this.state.customFields).filter(Boolean).length;
        const extraCount = Object.values(this.state.selectedIrFields).filter(Boolean).length;
        const fmtDate = (d) => d ? d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
        return {
            days,
            start: this.state.startDate ? fmtDate(start) : '—',
            end: this.state.endDate ? fmtDate(end) : '—',
            aggregate: aggLabels[this.state.aggregate] || this.state.aggregate,
            model: this.state.mode === 'ai' ? 'AI Mode' : 'Algorithm Mode',
            fields: customCount + extraCount,
            ready: days > 0 && (customCount + extraCount) > 0,
            hasStart: !!this.state.startDate,
            hasEnd: !!this.state.endDate,
        };
    }

    toggleCustomField(field) {
        this.state.customFields[field] = !this.state.customFields[field];
    }

    toggleIrField(fieldName) {
        this.state.selectedIrFields[fieldName] = !this.state.selectedIrFields[fieldName];
    }

    selectAllCustomFields() {
        for (let key in this.state.customFields) this.state.customFields[key] = true;
    }

    clearAllCustomFields() {
        for (let key in this.state.customFields) this.state.customFields[key] = false;
    }

    toggleTab(tabName) {
        this.state.activeTab = tabName;
        // Reset sub-tab whenever entering Table View
        if (tabName === 'table') {
            this.state.activeSubTab = 'main';
        }
        if (tabName === 'chart' && (this.state.mode === 'ai' || this.state.mode === 'algorithm') && this.state.hasForecast && this.forecastData && this.historicalData) {
            setTimeout(() => this.renderForecastChart(this.historicalData, this.forecastData, this.forecastReasons || {}, this.sentimentalScores || {}), 100);
        }
    }

    async checkSavedForecast() {
        try {
            const saved = await this.orm.call('sale.order', 'get_last_forecast', []);
            if (saved && saved.results && saved.params) {
                const params = JSON.parse(saved.params);
                const response = JSON.parse(saved.results);

                // Restore wizard parameters
                this.state.startDate = params.start_date || '';
                this.state.endDate = params.end_date || '';
                this.state.aggregate = ['M', 'Y'].includes(params.aggregate) ? params.aggregate : 'M';
                this.state.mode = params.mode || 'algorithm';
                this.state.keywords = params.keywords || '';
                
                if (params.custom_fields) {
                    for (let key in this.state.customFields) {
                        this.state.customFields[key] = false;
                    }
                    for (let key of params.custom_fields) {
                        if (key in this.state.customFields) {
                            this.state.customFields[key] = true;
                        }
                    }
                }
                if (params.extra_fields) {
                    for (let key in this.state.selectedIrFields) {
                        this.state.selectedIrFields[key] = false;
                    }
                    for (let key of params.extra_fields) {
                        if (key in this.state.selectedIrFields) {
                            this.state.selectedIrFields[key] = true;
                        }
                    }
                }

                // Restore results
                let actualDataset = response.dataset || [];
                let forecastData = response.forecast || null;
                let historicalData = response.historical || null;
                let saleOrdersTable = response.sale_orders_table || [];
                let orderLinesTable = response.orderlines_table || [];

                if (actualDataset && actualDataset.length > 0) {
                    this.dataset = actualDataset;
                    this.state.totalRows = actualDataset.length;
                    this.state.tableDataPreview = actualDataset.slice(0, 100);
                    this.state.tableColumns = Object.keys(actualDataset[0]);
                    this.state.columnLabels = response.column_labels || {};
                    this.state.status = 'table';
                    this.state.hasForecast = forecastData && Object.keys(forecastData).length > 0 && historicalData && Object.keys(historicalData).length > 0;
                    this.state.activeTab = 'chart';
                    this.state.activeSubTab = 'main';

                    this.state.saleOrdersTableData = saleOrdersTable.slice(0, 200);
                    this.state.saleOrdersTableColumns = saleOrdersTable.length > 0 ? Object.keys(saleOrdersTable[0]) : [];
                    this.state.orderLinesTableData = orderLinesTable.slice(0, 200);
                    this.state.orderLinesTableColumns = orderLinesTable.length > 0 ? Object.keys(orderLinesTable[0]) : [];
                    this.state.hasSubTables = (saleOrdersTable.length > 0 || orderLinesTable.length > 0);

                    if (this.state.hasForecast && forecastData && historicalData) {
                        this.forecastData = forecastData;
                        this.historicalData = historicalData;
                        this.forecastReasons = response.forecast_reasons || {};
                        this.sentimentalScores = response.sentimental_scores || {};
                        if (this.state.activeTab === 'chart') {
                            setTimeout(() => this.renderForecastChart(this.historicalData, this.forecastData, this.forecastReasons, this.sentimentalScores), 100);
                        }
                    } else {
                        this.forecastData = null;
                        this.historicalData = null;
                        this.forecastReasons = {};
                        this.sentimentalScores = {};
                    }
                }
            }
        } catch (e) {
            console.error("Error checking saved forecast:", e);
        }
    }


    toggleSubTab(subTabName) {
        this.state.activeSubTab = subTabName;
    }

    // ── On-chart news/keyword panel ──
    toggleNewsPanel() {
        if (!this.state.showNewsPanel) {
            // Seed the panel with the keywords used for the current forecast.
            this.state.panelKeywords = this.state.keywords || '';
        }
        this.state.showNewsPanel = !this.state.showNewsPanel;
    }

    closeNewsPanel() {
        this.state.showNewsPanel = false;
    }

    async recomputePrediction() {
        if (this.state.recomputing) return;
        this.state.recomputing = true;
        // Show the same processing ("owl") screen that follows Generate Query.
        this.state.showNewsPanel = false;
        this.state.status = 'processing';
        this._startProcessingAnimation();
        try {
            const response = await this.orm.call('sale.order', 'recompute_forecast', [{
                keywords: this.state.panelKeywords || ''
            }]);
            if (response && response.error) {
                alert(response.error);
                return;
            }
            this.state.keywords = this.state.panelKeywords || '';
            // Update only when keywords changed; unchanged -> keep the existing result.
            if (!(response && response.unchanged)) {
                this.forecastData = (response && response.forecast) || this.forecastData;
                this.historicalData = (response && response.historical && Object.keys(response.historical).length)
                    ? response.historical : this.historicalData;
                this.forecastReasons = (response && response.forecast_reasons) || {};
                this.sentimentalScores = (response && response.sentimental_scores) || {};
                this.state.hasForecast = !!(this.forecastData && Object.keys(this.forecastData).length
                    && this.historicalData && Object.keys(this.historicalData).length);
            }
            if (response && response.ai_status && response.ai_status !== 'ok') {
                alert(response.ai_status);
            }
        } catch (e) {
            console.error(e);
            alert("Could not recompute the prediction. Please try again.");
        } finally {
            this.state.recomputing = false;
            this.state.status = 'table';
            this.state.activeTab = 'chart';
            if (this.state.hasForecast) {
                setTimeout(() => this.renderForecastChart(this.historicalData, this.forecastData,
                    this.forecastReasons, this.sentimentalScores), 100);
            }
        }
    }

    // Translated display label for a dataset column key (falls back to the key).
    colLabel(col) {
        return (this.state.columnLabels && this.state.columnLabels[col]) || col;
    }

    // Download every generated table as one XLSX (one sheet per table).
    // Fetched as a blob so we can show a loading state until it is fully ready.
    async downloadAllXlsx() {
        if (this.state.downloading) {
            return;
        }
        this.state.downloading = true;
        try {
            const response = await fetch('/cyllo_sale_analytics/forecast_xlsx');
            if (!response.ok) {
                throw new Error("Download failed (" + response.status + ")");
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "Sales_Forecast_Tables.xlsx");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
            alert("Could not download the report. Please try again.");
        } finally {
            this.state.downloading = false;
        }
    }

    async submitWizard() {
        // Missing dates: highlight the empty field(s) in red and block save,
        // instead of showing a browser alert.
        this.state.startDateInvalid = !this.state.startDate;
        this.state.endDateInvalid = !this.state.endDate;
        if (this.state.startDateInvalid || this.state.endDateInvalid) {
            return;
        }
        // End before start: flag the End Date field and block save.
        if (new Date(this.state.startDate) > new Date(this.state.endDate)) {
            this.state.endDateInvalid = true;
            return;
        }
        this.state.startDateInvalid = false;
        this.state.endDateInvalid = false;

        const extraFields = Object.keys(this.state.selectedIrFields).filter(k => this.state.selectedIrFields[k]);
        const chosenCustomFields = Object.keys(this.state.customFields).filter(k => this.state.customFields[k]);

        if (extraFields.length === 0 && chosenCustomFields.length === 0) {
            alert("Warning: No fields selected! Please select at least one field.");
            return;
        }

        // AI mode requires a configured OpenAI key. Check it up-front and OUTSIDE
        // the try/catch below so a missing key surfaces as Odoo's styled
        // ValidationError dialog (not a browser alert) before processing starts.
        if (this.state.mode === 'ai') {
            await this.orm.call('sale.order', 'check_ai_credentials', []);
        }

        this.state.status = 'processing';
        this._startProcessingAnimation();

        const params = {
            start_date: this.state.startDate,
            end_date: this.state.endDate,
            mode: this.state.mode,
            aggregate: this.state.aggregate,
            custom_fields: chosenCustomFields,
            extra_fields: extraFields,
            keywords: this.state.mode === 'ai' ? this.state.keywords : ''
        };

        try {
            const response = await this.orm.call('sale.order', 'generate_training_dataset', [params]);

            if (response && response.error !== undefined) {
                this.state.status = 'wizard';
                alert("Server Error during extraction: " + (response.error || "Unknown Error"));
                return;
            }

            // ── Unified response handling ──
            // Backend always returns a dict: { dataset, product_table, customer_table, [forecast, historical] }
            let actualDataset = Array.isArray(response) ? response : (response && response.dataset) || [];
            let forecastData = (response && response.forecast) || null;
            let historicalData = (response && response.historical) || null;
            let saleOrdersTable = (response && response.sale_orders_table) || [];
            let orderLinesTable = (response && response.orderlines_table) || [];

            if (actualDataset && actualDataset.length > 0) {
                this.dataset = actualDataset;
                this.state.totalRows = actualDataset.length;
                this.state.tableDataPreview = actualDataset.slice(0, 100);
                this.state.tableColumns = Object.keys(actualDataset[0]);
                this.state.columnLabels = response.column_labels || {};
                this.state.status = 'table';
                this.state.hasForecast = forecastData && Object.keys(forecastData).length > 0 && historicalData && Object.keys(historicalData).length > 0;
                this.state.activeTab = 'chart';
                this.state.activeSubTab = 'main';

                // Sub-table state
                this.state.saleOrdersTableData = saleOrdersTable.slice(0, 200);
                this.state.saleOrdersTableColumns = saleOrdersTable.length > 0 ? Object.keys(saleOrdersTable[0]) : [];
                this.state.orderLinesTableData = orderLinesTable.slice(0, 200);
                this.state.orderLinesTableColumns = orderLinesTable.length > 0 ? Object.keys(orderLinesTable[0]) : [];
                this.state.hasSubTables = (saleOrdersTable.length > 0 || orderLinesTable.length > 0);


                if (this.state.hasForecast && forecastData && historicalData) {
                    this.forecastData = forecastData;
                    this.historicalData = historicalData;
                    this.forecastReasons = (response && response.forecast_reasons) || {};
                    this.sentimentalScores = (response && response.sentimental_scores) || {};
                    if (this.state.activeTab === 'chart') {
                        setTimeout(() => this.renderForecastChart(this.historicalData, this.forecastData, this.forecastReasons, this.sentimentalScores), 100);
                    }
                } else {
                    this.forecastData = null;
                    this.historicalData = null;
                    this.forecastReasons = {};
                    this.sentimentalScores = {};
                }

                // If AI mode was requested but the AI could not run, the forecast is
                // just the algorithm baseline — tell the user why (otherwise it looks
                // identical to Algorithm mode for no apparent reason).
                if (this.state.mode === 'ai' && response && response.ai_status && response.ai_status !== 'ok') {
                    alert(response.ai_status);
                }
            } else {
                this.state.status = 'wizard';
                alert("No data found for the selected criteria.");
            }
        } catch (e) {
            console.error(e);
            this.state.status = 'wizard';
            alert("Error generating dataset. Please check selections.");
        }
    }

    renderForecastChart(historicalData, forecastData, forecastReasons, sentimentalScores) {
        const chartElement = document.getElementById('sale_forecast_wizard_chart');
        if (!chartElement) return;

        const myChart = echarts.init(chartElement);
        const reasons = forecastReasons || {};

        const histKeys = Object.keys(historicalData).slice(-10);
        const forecastKeys = Object.keys(forecastData);
        const allDates = [...histKeys, ...forecastKeys];

        const fmt = v => {
            if (v === null || v === undefined) return '-';
            return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 });
        };

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                confine: true,
                extraCssText: 'max-width:300px; white-space:normal; word-break:break-word; line-height:1.5;',
                formatter: params => {
                    const date = params[0]?.axisValue;
                    let html = `<div class="cy-sf-tt-title">${date}</div>`;
                    params.forEach(p => {
                        if (p.value === null || p.value === undefined) return;
                        const color = p.seriesName === 'Historical' ? '#9ea700' : '#ff3333';
                        html += `<div class="cy-sf-tt-row">`;
                        html += `<span class="cy-sf-tt-dot" style="background:${color};"></span>`;
                        html += `<span class="cy-sf-tt-label"><strong>${p.seriesName}:</strong> ${fmt(p.value)}</span></div>`;
                    });
                    // Contextual reasons (only for predicted bars)
                    const periodReasons = reasons[date];
                    const periodScore = sentimentalScores ? sentimentalScores[date] : null;
                    if (periodReasons && periodReasons.length) {
                        html += `<div class="cy-sf-tt-reasons">`;
                        html += `<div class="cy-sf-tt-reasons-title">Why this forecast?</div>`;
                        if (periodScore !== null && periodScore !== undefined) {
                            const scoreColor = periodScore > 0 ? '#4CAF50' : (periodScore < 0 ? '#F44336' : '#9E9E9E');
                            html += `<div class="cy-sf-tt-score-wrap"><span class="cy-sf-tt-score" style="background-color:${scoreColor};">Sentiment Score: ${periodScore}</span></div>`;
                        }
                        periodReasons.forEach(r => {
                            html += `<div class="cy-sf-tt-reason">${r}</div>`;
                        });
                        html += `</div>`;
                    }
                    return html;
                }
            },
            legend: { data: ['Historical', 'Predicted'], top: 'top' },
            grid: { left: '3%', right: '4%', bottom: '8%', containLabel: true },
            xAxis: { type: 'category', data: allDates },
            yAxis: { type: 'value', axisLabel: { formatter: v => fmt(v), rotate: 30 } },
            series: [
                {
                    name: 'Historical',
                    type: 'bar',
                    itemStyle: { color: '#9ea700' },
                    data: allDates.map(d => histKeys.includes(d) ? historicalData[d] : null)
                },
                {
                    name: 'Predicted',
                    type: 'bar',
                    itemStyle: { color: '#ff3333' },
                    data: allDates.map(d => forecastKeys.includes(d) ? forecastData[d] : null)
                }
            ]
        };

        myChart.setOption(option);
    }

}

SalesPredictionDashboard.template = "SalesPredictionDashboard";
registry.category("actions").add("sales_prediction", SalesPredictionDashboard);