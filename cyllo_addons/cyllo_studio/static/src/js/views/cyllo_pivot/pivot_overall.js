/** @odoo-module **/

/**
 * PivotOverall
 *
 * Component that manages pivot view configurations within Cyllo Studio.
 * It allows users to add, remove, and update measures, row groupings,
 * and column groupings dynamically while keeping synchronization with
 * Odoo’s pivot model metadata.
 *
 * Features:
 * 1. **Initialization & State**:
 *    - Tracks pivot state (row/col groups, measures, record changes, etc.).
 *    - Loads and validates active fields on mount.
 *    - Synchronizes state with `envModel.model.metaData` on prop updates.
 *
 * 2. **Grouping Management**:
 *    - Dynamically add/remove row and column groupings.
 *    - Tracks original (`loadedRowGroupBy`, `loadedActiveMeasures`) vs. current state.
 *    - Handles insertion of blank placeholders when record changes occur.
 *
 * 3. **Pivot Updates**:
 *    - Communicates with backend (`cyllo_studio/pivot/edit_element`).
 *    - Stores changes for Undo/Redo functionality in `sessionStorage`.
 *    - Notifies users of successful changes and reloads Studio.
 *
 * 4. **Group Removal**:
 *    - Removes row/column groupings and syncs with backend
 *      (`cyllo_studio/pivot/remove_element`).
 *    - Manages undo/redo history and refreshes Studio mode.
 *
 * Purpose:
 * Provides a bridge between user pivot view customizations in Studio
 * and Odoo’s pivot model, ensuring changes are persisted, reversible,
 * and user-friendly.
 */
import {
    Component,
    useState,
    onMounted,
    onWillUpdateProps,
    useExternalListener
} from "@odoo/owl";
import {
    useService
} from "@web/core/utils/hooks";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    _t
} from "@web/core/l10n/translation";
import {
    validateField
} from "@cyllo_studio/js/actions/utils";
import {
    sortBy
} from "@web/core/utils/arrays";

// Maps the groupType passed to selectGroupField ('col' | 'row' | 'measure')
// to the corresponding key on state.addNew / state[...] arrays.
const GROUP_TYPE_KEYS = {
    col: "colGroupBys",
    row: "rowGroupBys",
    measure: "activeMeasures",
};

export class PivotOverall extends Component {
    static template = "cyllo_studio.PivotOverall";
    setup() {
        this.notification = useService("effect");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.state = useState({
            // One flag per section so adding a row in one section doesn't
            // hide the "+" button in the other two.
            addNew: {
                colGroupBys: true,
                rowGroupBys: true,
                activeMeasures: true,
            },
            columnGroup: this.props.mode.colGroupBys ? this.props.mode.colGroupBys[this.props.mode.colGroupBys.length - 1] : " ",
            rowGroup: this.props.mode.rowGroupBys ? this.props.mode.rowGroupBys[this.props.mode.rowGroupBys.length - 1] : " ",
            measure: this.props.mode.activeMeasures[0],
            colGroupBys: this.props.mode.colGroupBys,
            rowGroupBys: this.props.mode.rowGroupBys,
            activeMeasures: this.props.mode.activeMeasures,
            recordChange: false,
        })
        onMounted(() => {
            const fields = [];
            if (this.props.activeFields) {
                for (const [fieldName, field] of Object.entries(
                    this.props.activeFields
                )) {
                    if (validateField(fieldName, field)) {
                        fields.push(Object.assign({
                            name: fieldName
                        }, field));
                    }
                }
                this.fields = sortBy(fields, "string");
            }
        })
        onWillUpdateProps((nextProps) => {
            this.state.colGroupBys = nextProps.envModel.model.metaData?.colGroupBys;
            this.state.rowGroupBys = this.getRowGroupBys(nextProps);
            this.state.loadedRowGroupBy = nextProps.envModel.model.metaData.loadedRowGroupBy;
            this.state.activeMeasures = this.getMeasure(nextProps);
            this.state.loadedActiveMeasures = nextProps.envModel.model.metaData.loadedActiveMeasures;
            // Any section's blank/unselected row that hasn't been saved gets
            // dropped by the resync above (it only ever existed locally).
            // Reset every section's "+" button here, not just the one that
            // was just saved, so a still-pending blank row in a DIFFERENT
            // section doesn't leave its "+" stuck hidden.
            this.state.addNew = {
                colGroupBys: true,
                rowGroupBys: true,
                activeMeasures: true,
            };
        });


    }
     /**
     * Extracts row groupings from pivot metadata.
     * Adds a blank placeholder if a record change is flagged.
     *
     * @param {Object} props - Component props (includes envModel).
     * @param {boolean} [add=false] - Whether to append a blank placeholder.
     * @returns {Array} - Array of row groupings.
     */
    getRowGroupBys(props, add = false) {
        const rowGroup = [...props.envModel.model.metaData.rowGroupBys]
        rowGroup.splice(0, [...props.envModel.model.metaData.loadedRowGroupBy].length)
        return !this.state.recordChange ? rowGroup : [...rowGroup, '']
    }

    /**
     * Extracts active measures from pivot metadata.
     * Adds a blank placeholder if a record change is flagged.
     *
     * @param {Object} props - Component props (includes envModel).
     * @param {boolean} [add=false] - Whether to append a blank placeholder.
     * @returns {Array} - Array of measures.
     */
    getMeasure(props, add = false) {
        const rowGroup = [...props.envModel.model.metaData.activeMeasures]
        rowGroup.splice(0, [...props.envModel.model.metaData.loadedActiveMeasures].length)
        return !this.state.recordChange ? rowGroup : [...rowGroup, '']
    }

     /**
     * Appends a new empty entry to a grouping type (row/col/measures).
     * Only hides the "+" button for THIS section.
     *
     * @param {string} type - The state key to update (colGroupBys | rowGroupBys | activeMeasures).
     */
    handleInputGrouping(type) {
        this.state.addNew[type] = false;
        this.state[type].push("");
    }

    /**
     * Updates pivot configuration by sending changes to backend.
     * Persists changes in Undo/Redo stack and reloads Studio.
     *
     * @param {string} name - Field or option name being updated.
     * @param {string} item_type - Type of item (group/measure/attribute).
     * @param {string} [interval=""] - Interval for date/datetime fields.
     */
    async updatePivot(name, item_type, interval = "") {
        const view_type = this.props.viewType
        this.env.services.ui.block();
        const position = ["disable_linking", "sticky", "display_quantity"].includes(name) ?
            "attributes" :
            "inside";
        try {
            const response = await this.rpc("cyllo_studio/pivot/edit_element", {
                kwargs: {
                    model: this.props.model,
                    viewId: this.props.viewId,
                    name: name,
                    position: position,
                    item_type: item_type,
                    interval: interval,
                    view_type: view_type,
                },
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.env.services.ui.unblock();
        }
        try {
            this.notification.add({
                title: _t("Success"),
                message: "Changes Added.",
                description: "Exit Studio Mode To View Changes",
                type: "notification_panel",
                notificationType: "success",
                time: 1000,
            });
        } finally {
            await this.action.doAction("studio_reload");
        }
        // Only re-show the "+" button for the section that was being edited.
        const addNewKey = GROUP_TYPE_KEYS[item_type];
        if (addNewKey) {
            this.state.addNew[addNewKey] = true;
        }
        this.state.recordChange = false
    }

    /**
     * Returns flat options for CylloStudioDropdown.
     * Date/datetime fields are expanded into per-interval entries (Year, Quarter…).
     */
    get groupByFields() {
        const fields = this.fields || [];
        if (fields.length === 0) {
            return [{ value: "", label: "No fields available" }];
        }
        const DATE_INTERVALS = ["year", "quarter", "month", "week", "day"];
        const options = [];
        for (const field of fields) {
            if (["date", "datetime"].includes(field.type)) {
                for (const interval of DATE_INTERVALS) {
                    options.push({
                        value: `${field.name}:${interval}`,
                        label: `${field.string || field.name} · ${interval.charAt(0).toUpperCase() + interval.slice(1)}`,
                    });
                }
            } else {
                options.push({
                    value: field.name,
                    label: field.string || field.name,
                });
            }
        }
        return options;
    }

    /**
     * Returns flat options for CylloStudioDropdown limited to numeric fields.
     */
    get measureFields() {
        const measures = this.props.envModel.model.metaData.measures || {};
        const options = [];
        for (const [key, measure] of Object.entries(measures)) {
            options.push({
                value: key,
                label: measure.string,
            });
        }
        return options.length > 0 ? options : [{ value: "", label: "No measures available" }];
    }

    /**
     * Called by CylloStudioDropdown when a group-by field is selected.
     * Parses "fieldName:interval" format for date fields.
     *
     * @param {string} rawValue - Selected value from the dropdown.
     * @param {string} groupType - "col" | "row" | "measure".
     */
    selectGroupField(rawValue, groupType) {
        if (!rawValue) return;
        const [name, interval = ""] = rawValue.includes(":") ? rawValue.split(":") : [rawValue, ""];
        this.updatePivot(name, groupType, interval);
    }

    /**
     * Removes a row/col grouping or measure from pivot configuration.
     * Syncs changes with backend and updates Undo/Redo stack.
     *
     * @param {string} type - Metadata key type (e.g., rowGroupBys, colGroupBys).
     * @param {number} index - Index of the item to remove.
     * @param {string} name - State key holding the grouping.
     * @param {Array} rowGroupBys - Current row groupings (for context).
     */
    async handleRemoveGroup(type, index, name, rowGroupBys) {
        const path = this.props.envModel.model?.metaData[type][index];
        if (!path) {
            this.state[name].pop()
            this.state.addNew[name] = true;
            this.state.recordChange = false
            return;
        }
        this.env.services.ui.block();
        try {
            this.state[name].splice(index, 1);
            const response = await this.rpc("cyllo_studio/pivot/remove_element", {
                model: this.props.model,
                view_type: this.props.viewType,
                view_id: this.props.viewId,
                path,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.state.addNew[name] = true
            this.state.recordChange = false
            this.env.services.ui.unblock();

        }
        try {
            this.notification.add({
                title: _t("Success"),
                message: "Changes Added.",
                description: "Exit Studio Mode To View Changes",
                type: "notification_panel",
                notificationType: "success",
                time: 1000,
            });
        } finally {
            this.action.doAction('studio_reload');
        }
    }
}
PivotOverall.components = {
    CylloStudioDropdown,
};