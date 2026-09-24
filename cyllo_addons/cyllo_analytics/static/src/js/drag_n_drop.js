/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, useRef, onWillUpdateProps } = owl

/**
 * Build a chart-axis entry (query/alias/column) for a DIRECT field, exactly as
 * a drag-drop into an axis zone produces it. Shared by DropZone.onItemDrop and
 * by programmatic callers (e.g. AI chart-apply) so the two stay identical —
 * including the JSON (translatable) and monetary (base-currency) handling.
 *
 * @param {Object} field - { column, value, type, field_type, is_json }
 * @param {Object} ctx   - { companyId, orm }
 * @returns {Promise<Object>} the entry to push into query_data[type]
 */
export async function buildAxisEntry(field, { companyId, orm }) {
    const { column, value, type, field_type } = field;
    const is_json = field.is_json === true || field.is_json === 'true';
    const alias = column.replace('.', '_');
    let query;
    let monetaryInBase = false;

    if (is_json) {
        query = `${column} ->> 'en_US' AS ${alias}`;
    } else if (field_type === 'monetary') {
        const modelName = column.split('.')[0];
        let has_currency = false;
        const technicalName = await orm.searchRead(
            'ir.model', [['table_name', '=', modelName]], ['model']);
        const fieldsInfo = await orm.call(technicalName?.[0]?.model, 'fields_get', ['currency_id']);
        if (fieldsInfo && fieldsInfo.currency_id && fieldsInfo.currency_id.store) {
            has_currency = true;
        }
        const source_currency = has_currency
            ? `${modelName}.currency_id`
            : `(SELECT currency_id FROM res_company WHERE id = ${companyId})`;
        const currency_rate = `COALESCE((
                SELECT rate FROM res_currency_rate
                WHERE currency_id = ${source_currency}
                AND company_id = ${companyId}
                ORDER BY name DESC
                LIMIT 1
            ), 1) * COALESCE((
                SELECT rate
                FROM res_currency_rate
                WHERE currency_id = {selectedCurrency}
                AND company_id = ${companyId}
                ORDER BY name DESC
                LIMIT 1
            ), 1)`;
        monetaryInBase = `ROUND(${column} / ${currency_rate}, 2)`;
        query = `${monetaryInBase} AS ${alias}`;
    } else {
        query = `${column} AS ${alias}`;
    }

    return {
        type,
        value,
        alias,
        query,
        column,
        name: column.split('.')[1],
        raw_column: column,  // clean column preserved for AGG rebuilding
        monetaryInBase,
        field_type,
        sort_desc: false,
    };
}

export class DragItem extends Component {
    /** Class for draggable item */
    setup() {
        this.state = useState({
            isDragging: false
        })
        this.types = {
            "dimension": "measure",
            "measure": "dimension",
        }
        this.options = []
        this.mode = false
        this.setOptions()
        onWillUpdateProps((nextProps) => {
            this.setOptionsFromProps(nextProps)
        })
    }

    /**
     * Set options based on the item's type and field_type.
     * @param {Object} p - Props to evaluate (defaults to current props).
     */
    setOptions(p) {
        this.setOptionsFromProps(p || this.props)
    }

    setOptionsFromProps(p) {
        if (p.type == "measure") {
            this.options = ["NONE", "MIN", "MAX", "AVG", "SUM", "COUNT"]
            this.mode = "AGG"
        } else if (p.type == "dimension" &&
            ["date", "datetime"].includes(p.field_type)) {
            this.options = ["Day", "Month", "Year"]
            this.mode = "DATE_GROUP"
        } else {
            this.options = []
            this.mode = false
        }
    }

    /**
     * Set the dragging state.
     * @param {Event} e - The drag event.
     * @param {boolean} val - The new dragging state.
     */
    setDragging(e, val) {
        this.state.isDragging = val
        var { type, is_json, field_type, relation } = this.props
        if (val) {
            e.dataTransfer.setData("type", type)
            e.dataTransfer.setData("is_json", is_json)
            e.dataTransfer.setData("field_type", field_type)
            e.dataTransfer.setData("relation", relation)
            if (this.props.placedInZone) {
                e.dataTransfer.setData("placed_item", JSON.stringify({
                    type: this.props.type,
                    value: this.props.value,
                    alias: this.props.alias,
                    query: this.props.query,
                    column: this.props.column,
                    name: this.props.name,
                    raw_column: this.props.raw_column,
                    monetaryInBase: this.props.monetaryInBase,
                    field_type: this.props.field_type,
                    isPreset: this.props.isPreset,
                    rawFormula: this.props.rawFormula,
                    calculation_type: this.props.calculation_type,
                    aggregate_func: this.props.aggregate_func,
                    AGG: this.props.AGG,
                    DATE_GROUP: this.props.DATE_GROUP,
                    original_value: this.props.original_value,
                    sort_desc: this.props.sort_desc,
                    _sourceCategory: this.props.sourceCategory,
                    _sourceAxis: this.props.sourceAxis || '',
                    _sourceType: this.props.sourceType,
                }));
            }
        }
        var highlight = val ? 'highlight' : ''
        var avoidTypes = val ? [this.types[type]] : []
        if (val && type === 'measure') {
            avoidTypes = [...avoidTypes, 'groupBy'];
        }
        this.env.bus.trigger("CY:DROPZONE_HIGHLIGHT", { highlight, avoidTypes })
    }
}

// Define the template and components for the DragItem component
DragItem.template = "DragItem"
DragItem.components = { Dropdown, DropdownItem }

export class DropZone extends Component {
    /** Class for drop zone */

    get translatedString() {
        return this.props.string ? _t(this.props.string) : '';
    }

    setup() {
        this.orm = useService("orm");
        this.company = useService("company");
        this.notification = useService("notification");
        this.types = {
            "dimension": "measure",
            "measure": "dimension",
        }
        this.state = useState({
            type: this.props.type,
            limit: this.props.limit,
            children: this.props.children,
            highlight: ''
        })
        this.ref = useRef('drop')
        useBus(this.env.bus, "CY:DROPZONE_CHANGE_TYPE", (ev) => {
            var { category, type } = ev.detail
            this.changeType(category, type)
        });
        useBus(this.env.bus, "CY:DROPZONE_IS_EMPTY", (ev) => {
            var { category, type } = ev.detail
            if (!this.state.children.length && this.props.category == category && this.state.type == type) {
                this.state.type = 'both';
                this.env.bus.trigger("CY:DROPZONE_IS_EMPTY_CONFIRM", { category, type: this.types[type] })
            }
        });
        useBus(this.env.bus, "CY:DROPZONE_IS_EMPTY_CONFIRM", (ev) => {
            var { category, type } = ev.detail
            if (this.props.category == category && this.state.type == type) {
                this.state.type = 'both';
            }
        })
        useBus(this.env.bus, "CY:DROPZONE_HIGHLIGHT", (ev) => {
            var { highlight, avoidTypes } = ev.detail
            if (avoidTypes && avoidTypes.includes(this.state.type)) return
            // Do not highlight a zone that is already at its limit
            if (highlight && this.state.children.length >= this.state.limit) return
            this.state.highlight = highlight
        })
        useBus(this.env.bus, "CY:SYNC_CHILDREN", (ev) => {
            const { targetType, children, axis } = ev.detail;
            if (axis && this.props.axis && this.props.axis !== axis) {
                return;
            }
            if (this.state.type === targetType || (this.state.type === 'both' && ['dimension', 'measure'].includes(targetType))) {
                this.state.children = children;
            }
        });
        useBus(this.env.bus, "CY:REMOVE_PLACED_CHIP", (ev) => {
            const { alias, sourceCategory, sourceAxis } = ev.detail;
            if (this.props.category === sourceCategory && (this.props.axis || '') === sourceAxis) {
                const idx = this.state.children.findIndex(c => c.alias === alias);
                if (idx !== -1) {
                    const removed = this.state.children.splice(idx, 1)[0];
                    const type = removed.type || this.state.type;
                    this.env.bus.trigger("CY:UPDATE_QUERY", { type, data: this.state.children });
                    if (!this.state.children.length) {
                        this.env.bus.trigger("CY:DROPZONE_IS_EMPTY", {
                            category: this.props.category,
                            type: this.types[type] || type,
                        });
                    }
                }
            }
        });
        onWillUpdateProps(nextProps => {
            this.state.type = nextProps.type
            this.state.limit = nextProps.limit
            this.state.children = nextProps.children
        })
    }

    /**
     * Handle the drag-over event.
     * @param {Event} e - The drag-over event.
     */
    onDragOver(e) {
        e.preventDefault();
        // Do not highlight the zone if it is already at its limit
        if (this.state.children.length >= this.state.limit) {
            return;
        }
        this.ref.el.classList.add('can-drop');
    }

    onDragLeave(e) {
        if (!this.ref.el.contains(e.relatedTarget)) {
            this.ref.el.classList.remove('can-drop');
        }
    }

    /**
     * Handle item drop event.
     * @param {Event} e - The drop event.
     */
    async onItemDrop(e) {
        e.preventDefault();
        this.ref.el.classList.remove('can-drop');

        // Handle cross-zone chip move
        const placedItemStr = e.dataTransfer.getData("placed_item");
        if (placedItemStr) {
            const placed = JSON.parse(placedItemStr);
            const { _sourceCategory, _sourceAxis, _sourceType } = placed;

            // Same zone: no-op
            if (_sourceCategory === this.props.category && _sourceAxis === (this.props.axis || '')) {
                return;
            }
            // Zone full: no-op
            if (this.state.children.length >= this.state.limit) {
                return;
            }

            if (this.state.type === 'groupBy' && (placed.type === 'measure' || _sourceType === 'measure')) {
                this.notification.add("Measures and presets cannot be used for grouping.", { type: "warning" });
                return;
            }

            // Prevent duplicate: same column already in this zone
            const dupKey = placed.column || placed.alias;
            if (dupKey && this.state.children.some(c => (c.column || c.alias) === dupKey)) {
                this.notification.add("This field is already added to this zone.", { type: "warning" });
                return;
            }

            const childItem = {
                type: placed.type || _sourceType,
                value: placed.value,
                alias: placed.alias,
                query: placed.query,
                column: placed.column,
                name: placed.name,
                raw_column: placed.raw_column,
                monetaryInBase: placed.monetaryInBase,
                field_type: placed.field_type,
                isPreset: placed.isPreset,
                rawFormula: placed.rawFormula,
                calculation_type: placed.calculation_type,
                aggregate_func: placed.aggregate_func,
                AGG: placed.AGG,
                DATE_GROUP: placed.DATE_GROUP,
                original_value: placed.original_value,
                sort_desc: placed.sort_desc,
            };
            this.state.children.push(childItem);
            const targetType = this.state.type === 'both' ? (placed.type || _sourceType) : this.state.type;
            this.env.bus.trigger("CY:UPDATE_QUERY", { type: targetType, data: this.state.children });
            return;
        }

        const companyId = this.company.currentCompany?.id
        var type = e.dataTransfer.getData("type")
        var is_json = e.dataTransfer.getData("is_json")
        var field_type = e.dataTransfer.getData("field_type");
        var relation = e.dataTransfer.getData("relation");

        // Handle relational field drop (Many2one)
        if (field_type === 'many2one' && relation) {
            const item = document.querySelector('.dragging');
            // 1. Update the Zone's type and limit first
            var is_core = Object.keys(this.types).includes(this.state.type) || this.state.type == "both";
            if (this.state.type == "both" && this.props.axis) {
                const axis = {
                    "dimension": this.props.axis,
                    "measure": this.props.axis == 'x' ? 'y' : 'x',
                };
                const data = axis[type];
                this.env.bus.trigger("CY:UPDATE_QUERY", { type: 'dimension_axis', data });
            }

            if (is_core) {
                const category = this.props.category;
                this.changeType(category, type);
                this.env.bus.trigger("CY:DROPZONE_CHANGE_TYPE", { category, type: this.types[type] });
            }

            // 2. Validate against types and strict limits BEFORE proceeding
            if ((type == this.state.type || !is_core) && this.state.children.length < this.state.limit) {
                const targetType = this.state.type === 'both' ? type : this.state.type;
            this.env.bus.trigger("CY:RELATIONAL_FIELD_DROPPED", {
                type: targetType,
                axis: this.props.axis || false,
                field: {
                    column: item.dataset.column,
                    label: item.textContent,
                    relation: relation,
                    field_type: field_type,
                }
            });
            }
            this.ref.el.classList.remove('can-drop');
            return;
        }

        // 1. Handle axis/dimension logic (keep same)
        if (is_json && type) {
            if (this.state.type == "both" && this.props.axis) {
                var axis = {
                    "dimension": this.props.axis,
                    "measure": this.props.axis == 'x' ? 'y' : 'x',
                }
                var data = axis[type]
                this.env.bus.trigger("CY:UPDATE_QUERY", { type: 'dimension_axis', data })
            }

            // 2. Change type logic (keep same)
            var is_core = Object.keys(this.types).includes(this.state.type) || this.state.type == "both"
            if (is_core) {
                var category = this.props.category
                this.changeType(category, type)
                this.env.bus.trigger("CY:DROPZONE_CHANGE_TYPE", { category, type: this.types[type] })
            }

            // 3. Build final SQL
            const item = document.querySelector('.dragging');

            if (this.state.type === 'orderBy' && field_type === 'binary') {
                this.notification.add("Binary fields cannot be used for ordering.", { type: "warning" });
                this.ref.el.classList.remove('can-drop');
                return;
            }

            if (this.state.type === 'groupBy' && type === 'measure') {
                this.notification.add("Measures and presets cannot be used for grouping.", { type: "warning" });
                this.ref.el.classList.remove('can-drop');
                return;
            }

            if ((type == this.state.type || !is_core) && this.state.children.length < this.state.limit) {
                var column = item.dataset.column
                const is_preset = (item.dataset.is_preset && item.dataset.is_preset !== 'false') || (item.dataset.isPreset && item.dataset.isPreset !== 'false');

                // Prevent duplicate: same column already in this zone
                if (column && this.state.children.some(c => (c.column || c.raw_column) === column)) {
                    this.notification.add("This field is already added to this zone.", { type: "warning" });
                    this.ref.el.classList.remove('can-drop');
                    return;
                }

                if (is_preset) {
                    this.env.bus.trigger("CY:REBUILD_PRESET", {
                        targetType: this.state.type === 'both' ? type : this.state.type,
                        presetData: {
                            value: item.textContent,
                            alias: item.dataset.alias,
                            column: column,
                            rawFormula: item.dataset.raw_formula || item.dataset.rawFormula,
                            variables: item.dataset.variables,
                            variable_configs: item.dataset.variable_configs || item.dataset.variableConfigs,
                            calculation_type: item.dataset.calculation_type || item.dataset.calculationType,
                            aggregate_func: item.dataset.aggregate_func || item.dataset.aggregateFunc,
                            preset_context: item.dataset.preset_context || item.dataset.presetContext,
                            preset_id: item.dataset.preset_id || item.dataset.presetId,
                            monetaryInBase: item.dataset.monetary_in_base || item.dataset.monetaryInBase,

                        }
                    });
                    this.ref.el.classList.remove('can-drop');
                    return;
                }

                const entry = await buildAxisEntry({
                    column,
                    value: item.textContent,
                    type: item.dataset.type,
                    field_type,
                    is_json,
                }, { companyId, orm: this.orm });
                this.state.children.push(entry);
                var data = this.state.children
                var new_type = this.state.type == "both" ? type : this.state.type
                this.env.bus.trigger("CY:UPDATE_QUERY", { type: new_type, data })
            }
            this.ref.el.classList.remove('can-drop');
        }
    }

    /**
     * Change the category and type.
     * @param {string} category - The category to change to.
     * @param {string} type - The type to change to.
     */
    changeType(category, type) {
        if (this.state.type == "both" && category == this.props.category) {
            this.state.type = type
            if (type == "dimension") {
                this.state.limit = 1
            }
            if (type == "measure") {
                this.state.limit = 5
            }
        }
    }

    /**
     * Handle item removal.
     * @param {number} index - The index of the item to remove.
     * @param {string} type - The item type.
     */
    onItemRemove(index, type) {
        let elem = this.state.children[index]
        this.state.children.splice(index, 1)
        this.env.bus.trigger("CY:UPDATE_QUERY", { type, data: this.state.children })
        if (elem?.id) {
            this.env.bus.trigger("CY:UPDATE_UNLINKS", { type: 'axis', id: elem.id })
        }
        if (!this.state.children.length) {
            var category = this.props.category
            this.env.bus.trigger("CY:DROPZONE_IS_EMPTY", { category, type: this.types[type] })
        }
    }

    /**
     * Toggle the sort direction for an Order By item.
     * @param {number} index - The index of the item.
     */
    onToggleSort(index) {
        let elem = this.state.children[index];
        elem.sort_desc = !elem.sort_desc;
        this.env.bus.trigger("CY:UPDATE_QUERY", { type: this.state.type, data: this.state.children });
    }

    /**
     * Open the preset configuration dialog for editing.
     * @param {number} index - The index of the preset item in the drop zone.
     */
    editPreset(index) {
        this.env.bus.trigger("CY:EDIT_PRESET_FORMULA", {
            index,
            type: this.state.type,
        });
    }

    /**
     * Set functions for items.
     * @param {string} val - The new value.
     * @param {string} mode - The mode to set (e.g., "SUM").
     * @param {number} index - The index of the item.
     */
    setFunctions(val, mode, index) {
        const child = this.state.children[index];
        if (child.isPreset || child.rawFormula) {
            child.aggregate_func = val;
            child[mode] = val;
            
            // Capture the original label if not already captured to prevent stacking
            if (!child.original_label) {
                child.original_label = child.value ? child.value.replace(/^[A-Z]+\((.*)\)$/i, '$1') : child.alias;
            }
            const baseLabel = child.original_label;
            
            if (val === 'NONE') {
                child.value = baseLabel;
            } else {
                child.value = `${val}(${baseLabel})`;
            }
            
            this.state.children[index] = child;
            const targetType = this.state.type === "both" ? "axis" : this.state.type;
            this.env.bus.trigger("CY:UPDATE_QUERY", { type: targetType, data: this.state.children })
            return;
        }


        const cur = this.state.children[index];
        const extractField = cur.column.match(/([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)/);
        const rawCol = cur.raw_column || (extractField ? extractField[0] : cur.column.replace(/^\w+\(([\s\S]+)\)$/, '$1').trim());
        const monetaryInBase = cur.monetaryInBase;
        const baseExpr = monetaryInBase ? monetaryInBase.trim() : rawCol.trim();
        const baseLabel = cur.original_value || cur.original_label || (cur.value ? cur.value.replace(/^[A-Z]+\((.*)\)$/i, '$1') : rawCol.replace(/\./g, ' > '));
        if (val === 'NONE') {
            const alias = rawCol.replace(/\./g, '_').replace(/[^a-zA-Z0-9_]/g, '').substring(0, 50);
            this.state.children[index] = {
                ...cur,
                raw_column: rawCol,
                [mode]: false,
                aggregate_func: false,
                query: `${baseExpr} AS ${alias}`,
                alias: alias,
                column: rawCol,
                value: baseLabel,
                type: this.state.type,
            };
            const targetType = this.state.type === "both" ? "axis" : this.state.type;
            this.env.bus.trigger("CY:UPDATE_QUERY", { type: targetType, data: this.state.children });
            return;
        }
        const new_column = `${val}(${baseExpr})`;
        const alias = `${rawCol.replace(/\./g, '_').replace(/[^a-zA-Z0-9_]/g, '').substring(0, 50)}_${val.toLowerCase().trim()}`;
        this.state.children[index] = {
            ...cur,
            raw_column: rawCol,      // Persist the clean column for future re-selections
            [mode]: val,
            aggregate_func: val,
            query: `${new_column} AS ${alias}`,
            alias,
            column: rawCol,          // Keep column clean so GROUP BY logic uses the right field
            value: `${val}(${baseLabel})`,
            type: this.state.type,
        };
        const targetType = this.state.type === "both" ? "axis" : this.state.type;
        this.env.bus.trigger("CY:UPDATE_QUERY", { type: targetType, data: this.state.children })
    }

    /**
     * Set date group-by function for date/datetime dimension items.
     * Uses TO_CHAR for human-readable display (e.g. "January (2026)").
     * Also adds a visual tag in the Group By zone.
     * @param {string} val - The grouping level: "Day", "Month", or "Year".
     * @param {string} mode - Always "DATE_GROUP".
     * @param {number} index - The index of the item.
     */
    setDateGroupBy(val, mode, index) {
        const child = this.state.children[index]
        const column = child.column
        const baseAlias = column.replace('.', '_')
        const rawLabel = (child.original_value || child.value)
            .replace(/^(Day|Month|Year)\s+of\s+/i, '').trim()

        // Human-readable TO_CHAR format map
        const sqlExprMap = {
            "Day": `TO_CHAR(${column}, 'Mon DD, YYYY')`,
            "Month": `TO_CHAR(${column}, 'FMMonth (YYYY)')`,
            "Year": `TO_CHAR(${column}, 'YYYY')`,
        }
        const sqlExpr = sqlExprMap[val] || sqlExprMap["Month"]
        const alias = `${baseAlias}_${val.toLowerCase()}`

        this.state.children[index] = {
            query: `${sqlExpr} AS ${alias}`,
            alias,
            column,
            id: child.id,
            value: rawLabel,
            original_value: rawLabel,
            type: this.state.type,
            field_type: child.field_type,
            DATE_GROUP: val,
        }
        this.env.bus.trigger("CY:UPDATE_QUERY", { type: this.state.type, data: this.state.children })

        // Add a visual tag in the Group By zone, keyed by source_column for dedup/replace
        this.env.bus.trigger("CY:ADD_DATE_GROUPBY", {
            groupByItem: {
                type: "group",
                value: `${val} \u2014 ${rawLabel}`,
                alias,
                query: `${sqlExpr} AS ${alias}`,
                column: sqlExpr,
                source_column: column,
                date_group: val,
            }
        })
    }
}

// Define the template and components for the DropZone component
DropZone.template = "DropZone"

DropZone.defaultProps = {
    show: true,
    info: {
        condition: false,
        message: "",
        className: ""
    }
}
DropZone.components = { DragItem }
