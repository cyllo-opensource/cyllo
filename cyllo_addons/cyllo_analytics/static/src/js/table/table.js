/** @odoo-module **/

import {TableMaker} from './table_maker'
import {convertToTitleCase} from "@cyllo_analytics/js/chart_maker"
import {useService} from "@web/core/utils/hooks";

const {Component, useState, useEffect, xml, useRef, onWillUpdateProps, onMounted, onWillUnmount} = owl

/**
 * Table class for managing tabular data in a component.
 * @class
 * @extends {Component}
 */
export class Table extends Component {
    /**
     * Initializes the state and sets up the initial data for the Table class.
     * @function
     */
    setup() {
        useEffect(() => {
            this.setStyle()
        }, () => [this.props.style?.height, this.props.style?.width])
        onWillUpdateProps((newProps) => this.updateTable(newProps))
        useEffect(() => {
            const headerHeight = 100;
            const rowHeight = 47;
            const availableHeight = this.state.tableHeight - headerHeight;
            this.state.min = Math.floor(availableHeight / rowHeight);
            if (this.state.data.length) this.setArr()
        }, () => [this.state.tableHeight])
        this.state = useState({
            tableHeight: 0,
            arr: [],
            data: [],
            heading: [],
            name: this.props.data?.name || this.props.item?.name,
            count: 0,
            min: 0,
            offset: 0,
            sort: {},
            style: '',
            cardStyle: "",
            className: '',
            hasData: true,
            hiddenColumns: {},
            showColPanel: false,
            activeSort: null,
        })
        this.orm = useService('orm')
        this.rootRef = useRef('eChart-ref')
        this.cardRef = useRef('table-card')
        this.colPanelRef = useRef('col-panel-anchor')
        this._onDocClick = (ev) => {
            if (!this.state.showColPanel) return;
            const panel = this.colPanelRef.el;
            if (panel && !panel.contains(ev.target)) {
                this.state.showColPanel = false;
            }
        };
        this._tableResizeObserver = null;
        onMounted(() => {
            document.addEventListener('click', this._onDocClick, true)
            if (this.cardRef.el) {
                this._tableResizeObserver = new ResizeObserver(() => {
                    if (!this.cardRef.el) return;
                    const h = this.cardRef.el.clientHeight
                    if (h > 0 && h !== this.state.tableHeight) {
                        this.state.tableHeight = h
                    }
                })
                this._tableResizeObserver.observe(this.cardRef.el)
            }
        })
        onWillUnmount(() => {
            document.removeEventListener('click', this._onDocClick, true)
            if (this._tableResizeObserver) this._tableResizeObserver.disconnect()
        })
        useEffect(() => {
            this.theme = this.props.theme
            this.updateTable(this.props)
        }, () => [])
        this.convertToTitleCase = convertToTitleCase
    }

    updateTable(newProps) {
        var props = newProps.data?.data
        if (props) {
            this.setTableData(newProps.data)
        } else if (props === undefined) {
            props = newProps.item
            if (props) {
                this.fetchData(props)
            }
        }
    }

    /**
     * Sets the style property of the Table class based on the provided props.style object.
     * @function
     */
    setStyle() {
        var style = Object.keys(this.props.style).map(key => {
            const val = String(this.props.style[key]).replace(/;*$/, '');
            return `${key}:${val};`;
        }).join('');
        var cardStyle = Object.keys(this.props.style).filter(key => ['height', 'width'].includes(key)).map(key => {
            const val = String(this.props.style[key]).replace(/;*$/, '');
            return `${key}:${val};`;
        }).join('');
        this.state.style = style
        this.state.cardStyle = cardStyle
    }

    /**
     * Sets the data, heading, sort, count, min, offset, style, and className properties of the Table class based on the provided props.
     * Calls the setArr method to update the arr property.
     * @param {Object} props - An object containing the data, dimension, measures, and name properties.
     * @function
     */
    setTableData(props) {
        this.state.className = this.props.toggleClass
        var table = new TableMaker(props.data, props.dimension, props.measures, props.name)
        var tableData = table.getTableData()
        if (!tableData.data.length) {
            var newTheme = this.theme != this.props.theme
            if (newTheme) {
                this.theme = this.props.theme
            }
            if (this.state.hasData || newTheme) {
                this.state.hasData = false
                var theme = this.props.theme ? this.props.theme : false
                this.eChart = echarts.init(this.rootRef.el, theme)
                this.eChart.setOption({...tableData, animation: false, animationDuration: 0})
            }
            return
        }
        this.state.hasData = true
        this.state.data = tableData.data
        this.state.heading = tableData.heading
        var sort = {}
        const hiddenColumns = {}
        tableData.heading.forEach((head) => {
            sort[head] = 'asc'
            hiddenColumns[head] = false
        })
        this.state.sort = sort
        this.state.hiddenColumns = hiddenColumns
        this.state.count = tableData.count
        this.setArr()
    }

    /**
     * Updates the `arr` property of the `Table` class based on the current offset and count values.
     * It calculates the start and end indices and extracts a subset of elements from the `data` array.
     * @function
     */
    setArr() {
        var min = this.state.min - 1
        var next_min = this.state.count - (this.state.offset + 1)
        next_min = next_min > min ? min : next_min
        var start = this.state.offset
        var end = this.state.offset + next_min
        this.state.arr = this.createArray(start, end)
    }

    /**
     * Creates a new array by extracting a subset of elements from the `data` array based on the given start and end indices.
     * @param {number} start - The index of the first element to include in the new array.
     * @param {number} end - The index of the last element to include in the new array.
     * @returns {Array} - A new array containing the elements from the `data` array within the specified range.
     * @function
     */
    createArray(start, end) {
        const result = [];
        for (let i = start; i <= end; i++) {
            result.push(this.state.data[i]);
        }
        return result;
    }

    /**
     * Checks if there are more elements to display in the table.
     * @returns {boolean} - True if there are more elements, false otherwise.
     * @member {boolean}
     * @readonly
     */
    get hasNext() {
        return !(this.state.offset + this.state.min >= this.state.count)
    }

    /**
     * Checks if there are previous elements to display in the table.
     * @returns {boolean} - True if there are previous elements, false otherwise.
     * @member {boolean}
     * @readonly
     */
    get hasPrev() {
        return this.state.offset !== 0
    }

    /**
     * Updates the offset based on the minimum number of elements and the direction specified by the `num` parameter.
     * @param {number} num - The direction to update the offset (-1 for previous, 1 for next).
     * @function
     */
    onClick(num) {
        this.state.offset += this.state.min * num
        this.setArr()
    }

    /**
     * Sorts the table based on the specified header.
     * @param {string} header - The header to sort the table by.
     * @function
     */
    sortBy(header) {
        var mode = this.state.sort[header] === 'asc' ? 'desc' : 'asc'
        this.state.sort[header] = mode
        this.state.activeSort = header
        Object.keys(this.state.sort).forEach((item) => {
            if (item != header) {
                this.state.sort[item] = 'asc'
            }
        })
        this.state.data = this.state.data.sort((a, b) => {
            if (typeof a[header] === 'number' && typeof b[header] === 'number') {
                return mode === 'asc' ? a[header] - b[header] : b[header] - a[header]
            } else if (typeof a[header] === 'string' && typeof b[header] === 'string') {
                return mode === 'asc' ? a[header].localeCompare(b[header]) : b[header].localeCompare(a[header])
            }
        })
        this.setArr()
    }

    /**
     * Fetches data for the table based on the provided item.
     * @param {Object} item - The item containing information for fetching data.
     * @function
     */
    fetchData(item) {

        var sql = item.query.replace(/\n/g, ' ');
        this.orm.call("dashboard.config", "sql_execute", [sql]).then(async (res) => {
            this.state.rec_id = res.id
            let props = {
                data: res,
                name: item.name,
                measures: eval(item.measure),
                dimension: [item.dimension],
                dimension_axis: item.dimension_axis,
                type: item.type,
                id: item.id,
            }
            this.setTableData(props)
        })
    }

    convertToPixels(value, unit) {
        switch (unit) {
            case "px":
                return parseFloat(value);
            case "vh":
                return ((parseFloat(value) / 100) * window.innerHeight) + 190;
            default:
                return parseFloat(value);
        }
    };

    extractNumericValue(value) {
        const match = value.match(/([\d.]+)\s*(px|vh|%)?/);
        if (match) {
            const numericValue = parseFloat(match[1]);
            const unit = match[2] || "px"; // Default to pixels if no unit is specified
            return this.convertToPixels(numericValue, unit);
        }
        return NaN; // or handle the case where no numeric value is found
    };

    getImageUrl(val) {
        if (!val) return '';
        const parts = val.split(':');
        if (parts.length === 4) {
            return `/web/image?model=${parts[1]}&field=${parts[2]}&id=${parts[3]}`;
        }
        return '';
    }

    onClickTable(ev) {
        var hasData = true
        if (this.props.data) {
            hasData = Boolean(this.props.data.data?.length)
        }
        this.props.onClickTable && this.props.onClickTable(ev, hasData, false)
    }

    get visibleHeadings() {
        return this.state.heading.filter(h => !this.state.hiddenColumns[h])
    }

    toggleColumn(col) {
        this.state.hiddenColumns[col] = !this.state.hiddenColumns[col]
    }

    toggleColPanel(ev) {
        ev.stopPropagation()
        this.state.showColPanel = !this.state.showColPanel
    }

    static props = {
        item: {type: Object, optional: true},
        data: {type: Object, optional: true},
        slots: {type: Object, optional: true},
        style: {type: Object, optional: true},
        theme: {type: String, optional: true},
        toggleClass: {type: String, optional: true},
        onClickTable: {type: Function, optional: true},
    }
    static defaultProps = {
        style: {
            height: "100%;",
            width: "950px;"
        },
        theme: false,
        toggleClass: "",
        onClickTable: () => {
        },
    }
}

Table.template = xml`
<t t-name="Table">
    <div t-ref="table-card" t-attf-id="elem_{{props.data?.id}}" class="card cp mr-1 mt-0 align-items-stretch cy_tile cy_sheet_scrollable_table cy_sheet_table" t-att-class="state.className" t-att-style="state.style" t-on-click="onClickTable">
        <div class="cy-churn_tabl-header__section d-flex justify-content-between align-items-center sheet-header">
            <div class="cy-churn_tile-text cy-table-header sheet-title"><t t-esc="convertToTitleCase(state.name)"></t></div>
            <div class="d-flex align-items-center gap-2 cy-table-nav-button-container">
                <t t-if="state.hasData">
                    <div class="d-flex">
                        <button class=" cy-churn-nav_btn" t-if="hasPrev" t-on-click.stop.prevent="() => this.onClick(-1)"><i class="ri-arrow-left-line"></i></button>
                        <button class=" cy-churn-nav_btn" t-if="hasNext" t-on-click.stop.prevent="() => this.onClick(1)"><i class="ri-arrow-right-line cy-icon"></i></button>
                    </div>
                </t>
                <div class="table_footer">
                    <t t-slot="footer"></t>
                </div>
            </div>
        </div>
        <div t-ref="eChart-ref" t-attf-style="display: {{ state.hasData ? 'none': 'block' }}; {{state.cardStyle}} height: calc(100% - clamp(35px, 15%, 60px));"></div>
        <t t-if="state.hasData">
            <!-- Column panel lives OUTSIDE the overflow:auto container so it isn't clipped -->
            <t t-if="state.showColPanel">
                <div class="cy-col-panel" t-ref="col-panel-anchor" t-on-click.stop="() => {}">
                    <div class="cy-col-panel-header">Columns</div>
                    <t t-foreach="state.heading" t-as="col" t-key="col">
                        <div class="cy-col-panel-item" t-on-click.stop="() => this.toggleColumn(col)">
                            <i t-att-class="state.hiddenColumns[col] ? 'ri-checkbox-blank-line cy-col-unchecked' : 'ri-checkbox-circle-fill cy-col-checked'"></i>
                            <span t-esc="convertToTitleCase(col)"></span>
                        </div>
                    </t>
                </div>
            </t>
            <div class="cy-churn_table--container cy_sheets_table" style="height: 100%; overflow: auto;">
            <table class="cy-listView-table cy-churn_predict--table">
                <thead class="cy-listview-head cy-churn-prdt_thead">
                    <tr>
                        <th t-foreach="visibleHeadings" t-as="heading" t-key="heading_index"
                        t-att-title="convertToTitleCase(heading)"
                        class="o_list_record_selector o_list_controller align-middle pe-1 cursor-pointer cy-th-sortable"
                        t-on-click.stop.prevent="() => this.sortBy(heading)">
                            <div class="cy-th-inner">
                                <span class="d-block min-w-0 text-truncate flex-grow-1" t-esc="convertToTitleCase(heading)"></span>
                                <i t-att-class="'cy-sort-icon ' + (state.activeSort === heading ? (state.sort[heading] === 'asc' ? 'ri-arrow-up-s-line cy-sort-active' : 'ri-arrow-down-s-line cy-sort-active') : 'ri-arrow-up-down-line cy-sort-idle')"></i>
                            </div>
                        </th>
                        <th class="cy-col-th-toggle">
                            <button class="cy-col-toggle-btn" title="Columns" t-on-click.stop="toggleColPanel">
                                <i class="ri-equalizer-line"></i>
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody>
                <tr class="o_data_row" t-foreach="state.arr" t-as="arr" t-key="arr_index">
                    <td class="o_data_cell cursor-pointer o_field_cell o_list_char"
                    t-foreach="visibleHeadings" t-as="heading" t-key="heading_index">
                        <t t-if="arr[heading] and typeof arr[heading] === 'string' and arr[heading].startsWith('CY_IMAGE:')">
                            <img t-att-src="this.getImageUrl(arr[heading])" style="max-height: 32px; max-width: 32px; border-radius: 4px; object-fit: contain;"/>
                        </t>
                        <t t-else="">
                            <span t-esc="arr[heading]"></span>
                        </t>
                    </td>
                    <td class="cy-col-th-toggle"></td>
                    </tr>
                </tbody>
            </table>
            </div>
        </t>
    </div>
</t>`