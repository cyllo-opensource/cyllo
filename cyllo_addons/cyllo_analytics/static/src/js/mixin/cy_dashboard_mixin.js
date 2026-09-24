/** @odoo-module **/
const {useState, onWillStart, useEffect, useRef} = owl;
import {useService, useBus} from "@web/core/utils/hooks";
import {ThemeMaker} from "@cyllo_analytics/js/theme_maker";
import {useSaveContext} from "@cyllo_analytics/js/useSaveContext";
import {session} from "@web/session";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";

const TIMEFRAMES = {
    'This Week': 'week',
    'This Quarter': 'quarter',
    'Last Quarter': 'quarter_l',
    'This Month': 'month',
    'Last Month': 'month_l',
    'This Year': 'year',
    'Last Year': 'year_l',
    'Custom': 'custom'
}
export const SUB_KPI_SIZES = {
    "kpi": {height: 1, width: 3},
    "financial_kpi": {height: 2, width: 3}
}

export function CyAnalyticMixin(CyComponent) {
    return class extends CyComponent {
        setup() {
            super.setup();
            this.env.bus.addEventListener("PN:RLD", () => setTimeout(() => {
                window.location.reload()
            }, 50))
            this.edit = false;
            this.dateFormats = {
                display: 'YYYY/MM/DD',
                actual: 'YYYY-MM-DD',
            }

            this.filters = useState({})
            const {id, removeManually, getKeyValue, saveToSession} = useSaveContext()
            this.saveContext = {removeManually, getKeyValue, saveToSession}
            this.removeManually = removeManually
            this.userService = useService("user")
            this.hasAccess = session.is_admin;
            this.id = id
            this.orm = useService("orm")
            this.actionService = useService("action")
            this.notification = useService('notification');

            this.busService = this.env.services.bus_service
            this.channel = "CY:ANALYTICS"
            this.busService.addChannel(this.channel)
            this.busService.addEventListener("notification", this.onMessage.bind(this))
            this.themes = []
            this.themeState = useState({
                theme: false,
                theme_id: false,
                items: [],
                currentTheme: false,
            });
            this.bannerState = useState({
                banner: []
            })
            this.filterData = useState({
                selected: this.defaultFilterTag
            })
            this.ChartData = useState({
                data: [],
                itemData: [],
                items: [],
                loading: true,
            })
            this.timFrameState = useState({
                selected: this.defaultFilterTag,
                date_0: "",
                date_1: "",
                company: [],
                user: []
            })
            this.dashboard = useRef('dashboard')
            this.state = useState({
                width: 0,
                originalWidth: 0,
                globalFilters: [],
                sources: [],
                optionClass: 'collapse-filter',
                options: [],
                currentItem: false,
                sortedItems: [],
                showInfo: false,
                darkMode: false,
                renderKey: 0,
                gridReady: false,
                gridRevealed: false,
                kpiPending: 0,
                isPrinting: false,
            })
            useBus(this.env.bus, 'KPI_LOADED', () => {
                if (this.state.kpiPending > 0) this.state.kpiPending--;
            })
            onWillStart(this.onWillStart)
            useEffect(() => {
                this.state.sortedItems = this.sortedItems
                const filter = this.timFrameState.selected.split('_')
                const flag = !Boolean(filter.length > 1)
                this.dateOrder(flag, filter[0], true)
                this.applyAllFilters()
            }, () => [this.ChartData.items])
            this._darkModeSyncing = false
            useBus(this.env.bus, "DARK_MODE_UPDATED", (event) => {
                this._darkModeSyncing = true
                this.state.darkMode = event.detail
            })
            let toggleDarkMode = false
            useEffect(() => {
                if (toggleDarkMode) {
                    if (this._darkModeSyncing) {
                        this._darkModeSyncing = false
                        this.env.bus.trigger("RERENDER_ALL_GRAPHS")
                    } else {
                        this.toggleDarkMode()
                    }
                }
                toggleDarkMode = true
            }, () => [this.state.darkMode]);
        }

        get TimeFrame() {
            return TIMEFRAMES
        }

        async toggleDarkMode() {
            this.env.bus.trigger("TOGGLE_DARK_MODE")
            this.env.bus.trigger("RERENDER_ALL_GRAPHS")
        }

        async onWillStart() {
            this.state.darkMode = await this.orm.call('res.users', 'get_active', [])
            const hasAdminGroup = await this.userService.hasGroup('cyllo_analytics.group_cyllo_analytics_admin')
            this.hasAccess = session.is_admin || hasAdminGroup;
            var data = await this.orm.call("dashboard.config", "get_sheets", [this.id])
            this.items = data[0]
            this.state.kpiPending = data[0].filter(i => i.type === 'kpi').length
            this.state.showInfo = !Boolean(this.items.length);
            this.ChartData.items = data[0]
            this.id = data[1]
            this.name = data[3]
            this.state.name = data[3]
            this.themeState.theme = data[2]
            this.bannerState.banner = data[4]
            if (this.themeState.theme) {
                this.themeState.theme_id = data[2].id
                this.themeMaker = new ThemeMaker(this.themeState.theme)
                this.themeState.currentTheme = this.themeMaker.getTheme()
            }
            this.fetchThemes()
        }

        onMessage({detail: notifications}) {
            notifications = notifications.filter(item => item.payload && item.payload.channel === "CY:ANALYTICS")
            notifications.forEach(msg => {
                const payload = msg.payload;
                var item = this.items.find(i => i.id === payload.id)
                if (item) {
                    item.data = payload.result
                    this.env.bus.trigger("REFRESH_GRAPH") // Trigger re-render with new local data
                }
            })
        }

        dateOrder(flag, value, defaultVal) {
            var momentValue = flag ? moment() : moment().subtract(1, value);
            var startDate = momentValue.startOf(value).toDate();
            var endDate = momentValue.endOf(value).toDate();
            this.timFrameState.date_0 = moment(startDate).format(this.dateFormats.actual)
            this.timFrameState.date_1 = moment(endDate).format(this.dateFormats.actual)
            this.filters['start-date'] = moment(startDate).format(this.dateFormats.actual)
            this.filters['end-date'] = moment(endDate).format(this.dateFormats.actual)
            if (defaultVal) {
                this.filterData.date_0 = moment(startDate).format(this.dateFormats.display)
                this.filterData.date_1 = moment(endDate).format(this.dateFormats.display)
            }
        }

        resetPosition() {
            this.positions = {
                x: 0,
                y: 0,
                w: 0,
                h: 0,
                ft: true,
                maxH: [],
                maxHVal: {0: [0]},
                colFill: new Array(12).fill(0),
                cache: {}
            }
            this.firstLine = true
        }

        storeDefaultFilter() {
            var defaultFilterObject = {
                ...this.timFrameState
            }
            this.saveContext.saveToSession("defaultFilter", defaultFilterObject, true)
        }

        get defaultFilterOpts() {
            return this.saveContext.getKeyValue("defaultFilter")
        }

        get defaultFilterTag() {
            var selectedTag = 'month_l'
            if (this.defaultFilterOpts?.selected) {
                selectedTag = this.defaultFilterOpts.selected == "custom" ? selectedTag : this.defaultFilterOpts.selected
            }
            return selectedTag
        }

        /**
         * Fetch available themes.
         */
        async fetchThemes() {
            this.themes = await this.orm.call("dashboard.theme", 'search_read', [], {
                fields: ["name"]
            })
        }

        /**
         * Fetch data for charts.
         */
        async fetchData() {
            var itemLength = this.items.length
            this.ChartData.loading = Boolean(itemLength)
            this.items.forEach((item, i) => {
                var sql = item.query.replace(/\n/g, ' ');
                this.orm.call("dashboard.config", "sql_execute", [sql]).then((res) => {
                    const measuresList = eval(item.measure);
                    const measureAliases = measuresList.map(m => typeof m === 'object' ? m.alias : m);
                    const measureNames = (Array.isArray(measuresList) ? measuresList : []).reduce((acc, m) => {
                        if (typeof m === 'object' && (m.isPreset || m.value)) {
                            acc[m.alias] = m.value;
                        }
                        return acc;
                    }, {});

                    let props = {
                        data: res,
                        name: item.name,
                        measures: measureAliases,
                        measureNames: measureNames,
                        dimension: item.dimension,
                        dimension_axis: item.dimension_axis,
                        type: item.type,
                        id: item.id,
                        color_mappings: item.color_mappings || []
                    }
                    this.ChartData.data.push(props)
                    itemLength--;
                    this.ChartData.loading = !(itemLength == 0)
                })
            })
        }

        getKpi(item) {
            return {
                description: item.kpi_description,
                redirect: item.kpi_redirect,
                target: item.kpi_target,
                measureView: item.kpi_view,
                icon: item.kpi_icon,
                model: item.table_ids[0].model
            }
        }

        get sortedItems() {
            const copiedItems = this.items.slice();
            const value = copiedItems.sort((a, b) => {
                const aValue = a.dashboard_sheet_option_ids.length ? a.dashboard_sheet_option_ids[0].attributes : {};
                const bValue = b.dashboard_sheet_option_ids.length ? b.dashboard_sheet_option_ids[0].attributes : {};
                // Compare y values first
                if (aValue.y !== undefined && bValue.y !== undefined) {
                    if (aValue.y < bValue.y) return -1;
                    if (aValue.y > bValue.y) return 1;
                } else {
                    // Handle case where y is undefined
                    if (aValue.y === undefined && bValue.y !== undefined) return 1;
                    if (aValue.y !== undefined && bValue.y === undefined) return -1;
                }
                // If y values are equal or both are undefined, compare x values
                if (aValue.x !== undefined && bValue.x !== undefined) {
                    if (aValue.x < bValue.x) return -1;
                    if (aValue.x > bValue.x) return 1;
                } else {
                    // Handle case where x is undefined
                    if (aValue.x === undefined && bValue.x !== undefined) return 1;
                    if (aValue.x !== undefined && bValue.x === undefined) return -1;
                }
                // If both y and x values are equal or both are undefined, consider objects equal
                return 0;
            });
            return value
        }

        applyAllFilters() {
            this.state.sortedItems.forEach(item => {
                this.applyItemFilter(item)
            })
            if (this.presentation) {
                this.fetchData()
            }
            this.env.bus.trigger("REFRESH_GRAPH", { type: "refresh_graph" });
        }

        applyItemFilter(item) {
            if (!item.original_query) {
                item.original_query = item.query;
            }
            if (!item.original_query) {
                // Query not yet computed – skip filter application for this item.
                return;
            }
            var domains = item.filter_ids
                .filter(item => item.is_active)
                .map(item => item.domain)
            var where = domains.join(' AND ')

            // Pre-compute which tables are actually referenced in the FROM / JOIN
            // section of this query so we can safely skip global filters whose
            // field table is absent (e.g. a custom query on purchase_order_line
            // with a date filter mapped to purchase_order.create_date).
            const _tablesInQuery = (() => {
                const upperQ = item.original_query.toUpperCase();
                const fromIdx = upperQ.indexOf('FROM');
                if (fromIdx === -1) return new Set();
                const fromSection = upperQ.slice(fromIdx);
                const tableRe = /(?:FROM|JOIN)\s+"?([a-zA-Z_][a-zA-Z0-9_]*)"?/gi;
                const tables = new Set();
                let m;
                while ((m = tableRe.exec(fromSection)) !== null) {
                    tables.add(m[1].toUpperCase());
                }
                return tables;
            })();

            item.sheet_filter_ids.forEach(filter => {
                var {operator, code} = filter.global_filter_id
                var value = this.filters[code]
                if (value?.length) {
                    // Skip filters that reference a table not present in the query.
                    if (filter.field) {
                        const parts = filter.field.split('.');
                        if (parts.length > 1) {
                            const filterTable = parts[0].toUpperCase();
                            if (!_tablesInQuery.has(filterTable)) {
                                return; // table not found anywhere in query – skip
                            }
                        }
                    }
                    value = typeof value == 'string' ? `'${value}'` :
                        typeof value == 'object' ? `(${value.join(', ')})` : value
                    var domain = `${filter.field} ${operator} ${value}`
                    domain = where ? `(${where}) AND ${domain}` : domain
                    where = domain
                }
            })
            var new_query = this.applyFilters(item.original_query, where)
            item.query = new_query
        }


        applyFilters(query, newCondition) {
            if (!newCondition) return query;
            const fromIdx = query.toUpperCase().lastIndexOf("FROM");
            if (fromIdx === -1) return query;
            const beforeFrom = query.slice(0, fromIdx);
            const afterFrom = query.slice(fromIdx);
            const currentWhere = afterFrom.match(
                /WHERE\s+(.+?)(?=GROUP\s+BY|ORDER\s+BY|LIMIT|$)/is
            );
            if (currentWhere) {
                let matchFull = currentWhere[0];
                let conditions = currentWhere[1];
                let combinedCondition = `(${conditions.trim()}) AND (${newCondition})`;

                let matchStartIndex = currentWhere.index;
                let beforeMatch = afterFrom.substring(0, matchStartIndex);
                let afterMatch = afterFrom.substring(matchStartIndex + matchFull.length);

                let newAfterFrom = `${beforeMatch}WHERE ${combinedCondition}${afterMatch}`;
                return beforeFrom + newAfterFrom;
            } else {
                const groupByRegex = /\bGROUP\s+BY\b/i;
                const orderByRegex = /\bORDER\s+BY\b/i;
                const limitRegex = /\bLIMIT\b/i;
                const insertPosition =
                    groupByRegex.test(afterFrom) ? groupByRegex.exec(afterFrom).index :
                        orderByRegex.test(afterFrom) ? orderByRegex.exec(afterFrom).index :
                            limitRegex.test(afterFrom) ? limitRegex.exec(afterFrom).index :
                                afterFrom.length;
                const beforeInsert = afterFrom.substring(0, insertPosition);
                const afterInsert = afterFrom.substring(insertPosition);
                return `${beforeFrom}${beforeInsert} WHERE ${newCondition} ${afterInsert}`;
            }
        }

        getChartSizes(type, rearrangeId = 1, subKpi = false) {
            if (type === "kpi") {
                if (subKpi) {
                    return SUB_KPI_SIZES[subKpi]
                } else return {height: 1, width: 3}
            } else {
                // tables use identical sizing to charts
                const modVal = rearrangeId % 2;
                if (modVal === 0) {
                    return {height: 4, width: 6};
                } else {
                    return {height: 3, width: 4};
                }
            }
        }
        static props = {...standardActionServiceProps}
    }
}