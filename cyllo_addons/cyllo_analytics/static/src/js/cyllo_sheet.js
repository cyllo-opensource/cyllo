/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { ModelViewer } from "./model_viewer";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { DragItem, DropZone } from "./drag_n_drop"
import { GraphTile } from "@cyllo_analytics/js/presentation/components/graph_tile";
import { SQLEditor } from "./editor/SQLEditor";
import { browser } from "@web/core/browser/browser";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";
import { SQLQueryParser } from "./query/query_manager"
import { FieldAutoComplete } from "@cyllo_analytics/js/sheet_filter/field_auto_complete"
import { FieldAutoCompleteGlobal } from "@cyllo_analytics/js/sheet_filter/field_auto_complete_global"
import { KpiSheet } from "@cyllo_analytics/js/KpiSheet";
import { Table } from "@cyllo_analytics/js/table/table";
import { Number } from "@cyllo_analytics/js/fields/number";
import { DeleteDialog } from "./delete_dialog_box";
import { Dialog } from "@web/core/dialog/dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";
import { SheetFilterDomain } from "./sheet_filter/sheetFilterDomain";
import { PresetApplyDialog } from "@cyllo_analytics/js/presets/preset_apply_dialog";
import { FieldTraversalDialog } from "./FieldTraversalDialog";
import { generateSqlAlias } from "@cyllo_analytics/js/utils";
const { Component, useState, onWillStart, useEffect, onWillDestroy, onMounted, useRef } = owl


export class SheetDeleteDialog extends DeleteDialog {
    async _confirm() {
        if (typeof this.props.callBackAction === 'function') {
            this.props.callBackAction()
            this.props.close()
        } else {
            await this.orm.unlink(this.props.model, [this.props.id]);
            this.props.removeManually && this.props.removeManually()
            this.props.close()
            this.props.onConfirm()
        }

    }

    static defaultProps = {
        ...DeleteDialog.defaultProps,
        callBackAction: false
    }
}

class FieldList extends Component {
    setup() {

        this.state = useState({
            data: this.props.data,
            search: '',
        })
        useEffect(() => {
            this.state.data = this.props.data
            this.state.search = ""
        }, () => [this.props.data])
        useEffect(() => {
            if (this.state.search) {
                this.state.data = this.props.data.filter(item => {
                    const search = this.state.search.toLowerCase()
                    return item.label.toLowerCase().includes(search) || item.name.toLowerCase().includes(search)
                })
            } else {
                this.state.data = this.props.data
            }
        }, () => [this.state.search])
    }
}

FieldList.template = "FieldList"
FieldList.components = { DragItem }

export class ChartNoteDialog extends Component {
    setup() {
        this.state = useState({
            note: this.props.existingNote || ''
        });
    }

    _onSave() {
        this.props.onSave({
            note: this.state.note
        });
        this.props.close();
    }
}
ChartNoteDialog.template = "ChartNoteDialog";
ChartNoteDialog.components = { Dialog };

export class ColorMappingDialog extends Component {
    setup() {
        this.state = useState({
            measure_alias: this.props.mapping.measure_alias || '',
            min_value: this.props.mapping.min_value ?? 0,
            max_value: this.props.mapping.max_value || '',
            color: this.props.mapping.color || '#344BD2',
            indicator: this.props.mapping.indicator || '',
        });
    }

    update(field, value) {
        this.state[field] = value;
        this.props.onUpdate(field, value);
    }
}
ColorMappingDialog.template = "ColorMappingDialog";
ColorMappingDialog.components = { Dialog };

export class CylloSheet extends Component {
    /** Class for creating a CylloSheet component. */
    setup() {
        const { id, saveManually, removeManually } = useSaveContext()
        this.id = id
        this.hasMonetary = false //multi
        this.isNewSheet = false;
        onWillDestroy(removeManually)
        this.sheet = useRef('sheet')
        this.saveManually = saveManually
        this.removeManually = removeManually
        this.model = 'dashboard.sheet'
        this.orm = useService("orm")
        this.company = useService("company")
        this.dialog = useService("dialog")
        this.notification = useService("notification")
        this.avoid_fields = []
        this.action = useService("action")
        this.ChartData = useState({ data: { data: [], type: 'bar', measures: [], dimension: [] }, generate: true })
        this.measures_field_types = ["float", "monetary", "integer"]
        this.avoid_field_types = ["many2many", "one2many"]
        this.unlinkList = {
            axis: [],
            tables: [],
            where: [],
            configs: [],
        }
        this.previewLimit = {
            is_enable: false,
            limit: 0
        }
        this.filterOptions = {}
        this.state = useState({
            name: '',
            models: [],
            fields: [],
            limit: 0,
            query: '',
            need_save: false,
            false_linking: false,
            sheetTypes: [],
            chart: [],
            selectedType: [1, 'line'],
            configs: [],
            globalFilters: [],
            activeFilterGroup: null,
            filterModalPos: { top: 100, left: 300 },
            image: "",
            option: {},
            kpiValue: {},
            saveClicked: false,
            loading: true,
            savingMode: false,
            id: id,
            currency: false,
            isCustomSQL: false,
            allDbPresets: [],
            themeColors: [],
            darkMode: false,
            toggleQuery: false,
            // Signature of the last saved/loaded config; compared against the live
            // configSignature to decide whether Save/Discard should be shown.
            savedSignature: null,
        })

        this.query_data = useState({
            dimension: [],
            measure: [],
            join: [],
            joinData: [],
            where: [],
            groupBy: [],
            orderBy: [],
            color_mappings: [],
            annotations: [],
            dimension_axis: 'x',
        })
        this.navState = useState({
            allRecords: [],
            recordValue: 1
        })
        this._configLoaded = false
        useBus(this.env.bus, "CY:UPDATE_UNLINKS", (ev) => {
            var { type, id } = ev.detail
            this.unlinkList[type].push(id)
        })
        useBus(this.env.bus, "CY:UPDATE_QUERY", (ev) => {
            this.state.false_linking = false
            var { type, data } = ev.detail

            if (['measure', 'dimension', 'axis', 'dimension_axis', 'where', 'groupBy', 'orderBy'].includes(type)) {
                this.state.isCustomSQL = false;
            }

            if (type === 'groupBy') {
                // Detect which date groupBy items were just removed
                const oldGroupBy = this.query_data.groupBy || []
                const removedDateItems = oldGroupBy.filter(
                    g => g.source_column && !data.some(n => n.source_column === g.source_column)
                )
                this.query_data[type] = data
                // Revert removed date dimensions back to their plain column query
                if (removedDateItems.length > 0) {
                    this.query_data.dimension = this.query_data.dimension.map(dim => {
                        const removed = removedDateItems.find(r => r.source_column === dim.column)
                        if (removed) {
                            const baseAlias = dim.column.replace('.', '_')
                            const cleanLabel = (dim.original_value || dim.value)
                                .replace(/^(Day|Month|Year)\s+of\s+/i, '').trim()
                            return {
                                ...dim,
                                alias: baseAlias,
                                query: `${dim.column} AS ${baseAlias}`,
                                value: cleanLabel,
                                original_value: cleanLabel,
                                DATE_GROUP: null,
                            }
                        }
                        return dim
                    })
                    // onWillUpdateProps always-sync will pick this up; CY:SYNC_CHILDREN as backup
                    this.env.bus.trigger("CY:SYNC_CHILDREN", {
                        targetType: 'dimension',
                        children: this.query_data.dimension,
                    })
                }

                // Update measure chip labels to reflect the effective aggregate
                // Presets are skipped — their aggregation is embedded in the formula already.
                const isNowGrouping = data.length > 0;
                const defaultAgg = 'SUM';
                this.query_data.measure = this.query_data.measure.map(m => {
                    // Skip presets and measures with explicit aggregate set by user
                    if (m.isPreset || m.rawFormula) return m;
                    if (m.aggregate_func && m.aggregate_func !== 'NONE') return m;
                    const baseLabel = m.original_label || m.value || m.alias || '';
                    if (isNowGrouping) {
                        return {
                            ...m,
                            original_label: m.original_label || baseLabel,
                            value: `${defaultAgg}(${m.original_label || baseLabel})`,
                        };
                    } else {
                        return {
                            ...m,
                            value: m.original_label || baseLabel,
                        };
                    }
                });
                // Sync updated measure labels back to the drop zone
                this.env.bus.trigger("CY:SYNC_CHILDREN", {
                    targetType: 'measure',
                    children: this.query_data.measure,
                });
            } else {
                this.query_data[type] = data
                if (["measure", "dimension"].includes(type)) {
                    this.query_data.measure = this.query_data.measure.filter(item => item.type == "measure")
                    this.query_data.dimension = this.query_data.dimension.filter(item => item.type == "dimension")

                    if (type === 'measure') {
                        const activeMeasures = new Set(this.query_data.measure.map(m => m.alias));
                        this.query_data.color_mappings.forEach(mapping => {
                            if (!activeMeasures.has(mapping.measure_alias)) {
                                mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                            }
                        });
                        if (this.ChartData.data && this.ChartData.data.color_mappings) {
                            this.ChartData.data.color_mappings = this.query_data.color_mappings;
                        }
                        if (this.query_data.annotations) {
                            this.query_data.annotations.forEach(mapping => {
                                if (!activeMeasures.has(mapping.measure_alias)) {
                                    mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                                }
                            });
                            if (this.ChartData.data && this.ChartData.data.annotations) {
                                this.ChartData.data.annotations = this.query_data.annotations;
                            }
                        }

                        // If any measure now has an explicit aggregate (triggering grouping),
                        // update the UI labels of all other measures without an explicit aggregate
                        // to show the default SUM() — matching what _applyMeasureAggregates does in SQL.
                        // Presets are skipped — their aggregation is embedded in the formula already.
                        const hasExplicitAgg = this.query_data.measure.some(
                            m => m.aggregate_func && m.aggregate_func !== 'NONE'
                        );
                        const isGroupingActive = hasExplicitAgg || this.query_data.groupBy.length > 0;
                        if (isGroupingActive) {
                            const defaultAgg = 'SUM';
                            let labelsChanged = false;
                            this.query_data.measure = this.query_data.measure.map(m => {
                                if (m.isPreset || m.rawFormula) return m;
                                if (m.aggregate_func && m.aggregate_func !== 'NONE') return m;
                                const baseLabel = m.original_label || m.value || m.alias || '';
                                const expectedLabel = `${defaultAgg}(${m.original_label || baseLabel})`;
                                if (m.value !== expectedLabel) {
                                    labelsChanged = true;
                                    return {
                                        ...m,
                                        original_label: m.original_label || baseLabel,
                                        value: expectedLabel,
                                    };
                                }
                                return m;
                            });
                            if (labelsChanged) {
                                this.env.bus.trigger("CY:SYNC_CHILDREN", {
                                    targetType: 'measure',
                                    children: this.query_data.measure,
                                });
                            }
                        } else {
                            // No grouping — revert any auto-labelled measures back to plain labels
                            let labelsChanged = false;
                            this.query_data.measure = this.query_data.measure.map(m => {
                                if (m.isPreset || m.rawFormula) return m;
                                if (m.aggregate_func && m.aggregate_func !== 'NONE') return m;
                                const base = m.original_label;
                                if (base && m.value !== base) {
                                    labelsChanged = true;
                                    return { ...m, value: base };
                                }
                                return m;
                            });
                            if (labelsChanged) {
                                this.env.bus.trigger("CY:SYNC_CHILDREN", {
                                    targetType: 'measure',
                                    children: this.query_data.measure,
                                });
                            }
                        }
                    }

                    // When dimension is removed, clean up any date groupBy tags for it
                    if (type === 'dimension') {
                        const activeColumns = new Set(this.query_data.dimension.map(d => d.column))
                        this.query_data.groupBy = this.query_data.groupBy.filter(
                            item => {
                                if (item.source_column && !activeColumns.has(item.source_column)) {
                                    if (item.id) {
                                        this.unlinkList.axis.push(item.id)
                                    }
                                    return false
                                }
                                return true
                            }
                        )
                    }
                }
            }
            this.genQuery()
        })
        // Add / replace a date group-by tag in the Group By zone
        useBus(this.env.bus, "CY:ADD_DATE_GROUPBY", (ev) => {
            const { groupByItem } = ev.detail
            let existingId = null
            // Remove any existing date_group entry for the same source column
            this.query_data.groupBy = this.query_data.groupBy.filter(
                item => {
                    const hasSameSource = item.source_column === groupByItem.source_column;
                    // Fallback for duplicates or older records missing source_column
                    const hasSameColumnSubstring = !item.source_column && item.column && typeof item.column === 'string' && item.column.includes(groupByItem.source_column) && /^TO_CHAR/i.test(item.column);

                    if (hasSameSource || hasSameColumnSubstring) {
                        if (item.id) {
                            if (!existingId) {
                                existingId = item.id; // Reuse the first matched ID to avoid creating a new DB record
                            } else {
                                this.unlinkList.axis.push(item.id); // If there are multiple, unlink the rest to clean up the DB
                            }
                        }
                        return false;
                    }
                    return true;
                }
            )
            if (existingId) {
                groupByItem.id = existingId;
            }
            this.query_data.groupBy.push(groupByItem)
            this.genQuery()
        })
        useBus(this.env.bus, "CY:REBUILD_PRESET", this._onRebuildPreset.bind(this));
        useBus(this.env.bus, "CY:RELATIONAL_FIELD_DROPPED", this.onRelationalFieldDropped.bind(this));

        useEffect(() => {
            (async () => {
                this.state.savingMode = false
                this.state.loading = true
                try {
                    if (!this._configLoaded) {
                        await this._loadConfig()
                        this._configLoaded = true
                    }
                    await this._refreshSheet()
                } finally {
                    requestAnimationFrame(() => {
                        if (this.state) {
                            this.state.loading = false
                        }
                    })
                }
            })()
        }, () => [this.id])

        this.onAddPreset = () => {
            this.dialog.add(PresetApplyDialog, {
                fields: this.state.fields || [],
                models: this.state.models || [],
                sheet_id: this.id,
                initialMode: 'create',
                onApply: (measureObj) => {
                    this.env.bus.trigger("CY:APPLY_PRESET", { measureObj });
                },
            });
        };

        useEffect(() => {
            this.calculateLimit()
            this.genQuery()
        },
            () => [...Object.keys(this.query_data), this.state.limit])
        useEffect(() => {
            this.calculateLimit()
            this.state.need_save = true
        },
            () => [this.state.selectedType[0]])
        useEffect(() => {
            this.generateChart()
        }, () => [this.state.previewQuery])
        useEffect((event) => {
            this.setTableSave()
        }, () => [this.state.models, this.state.limit])
        useEffect(() => {
            this.orm.call("calculation.preset", "get_all_presets", [this.id || false]).then(presets => {
                this.state.allDbPresets = presets || [];
            });
        }, () => [this.state.models.length])

        useBus(this.env.bus, "CY:PRESET_SAVED", () => {
            this.orm.call("calculation.preset", "get_all_presets", [this.id || false]).then(presets => {
                this.state.allDbPresets = presets || [];
            });
        });
        // ── Preset apply handler ────────────────────────────────────────────
        useBus(this.env.bus, "CY:APPLY_PRESET", (ev) => {
            const { measureObj, type = 'measure' } = ev.detail;
            const alias = measureObj.alias;
            const oldAlias = measureObj.oldAlias;

            // Remove existing preset item if editing or if alias conflicts
            this.query_data[type] = this.query_data[type].filter(
                m => m.alias !== alias && (oldAlias ? m.alias !== oldAlias : true)
            );
            this.query_data[type].push(measureObj);

            if (type === 'measure') {
                let mappingUpdated = false;
                const activeMeasures = new Set(this.query_data.measure.map(m => m.alias));

                // 1. Explicit rename (if alias changed)
                if (oldAlias && oldAlias !== alias) {
                    this.query_data.color_mappings.forEach(mapping => {
                        if (mapping.measure_alias === oldAlias) {
                            mapping.measure_alias = alias;
                            mappingUpdated = true;
                        }
                    });
                }
                
                // 2. Fallback for orphaned mappings (e.g. creating new preset after deleting old measure)
                this.query_data.color_mappings.forEach(mapping => {
                    if (!activeMeasures.has(mapping.measure_alias)) {
                        mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                        mappingUpdated = true;
                    }
                });

                if (mappingUpdated && this.ChartData.data && this.ChartData.data.color_mappings) {
                    this.ChartData.data.color_mappings = this.query_data.color_mappings;
                }

                // Do the same for annotations
                if (this.query_data.annotations) {
                    let annotationUpdated = false;
                    
                    if (oldAlias && oldAlias !== alias) {
                        this.query_data.annotations.forEach(mapping => {
                            if (mapping.measure_alias === oldAlias) {
                                mapping.measure_alias = alias;
                                annotationUpdated = true;
                            }
                        });
                    }
                    
                    this.query_data.annotations.forEach(mapping => {
                        if (!activeMeasures.has(mapping.measure_alias)) {
                            mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                            annotationUpdated = true;
                        }
                    });

                    if (annotationUpdated && this.ChartData.data && this.ChartData.data.annotations) {
                        this.ChartData.data.annotations = this.query_data.annotations;
                    }
                }
            }

            // Update the available fields list so it stays in sync
            const fieldIndex = this.state.fields.findIndex(
                f => f.name === alias || (oldAlias && f.name === oldAlias)
            );
            const fieldData = {
                label: measureObj.value,
                name: measureObj.alias,
                column: measureObj.column,
                type: type,
                isPreset: true,
                rawFormula: measureObj.rawFormula,
                variables: measureObj.variables,
                variable_configs: measureObj.variable_configs,
                calculation_type: measureObj.calculation_type,
                aggregate_func: measureObj.aggregate_func,
                monetaryInBase: measureObj.monetaryInBase,
                preset_id: measureObj.preset_id,
                model: { name: 'Calculated' }
            };

            if (fieldIndex !== -1) {
                this.state.fields[fieldIndex] = fieldData;
            } else {
                this.state.fields.push(fieldData);
            }

            this.env.bus.trigger("CY:SYNC_CHILDREN", { targetType: type, children: this.query_data[type] });
            this.genQuery();
            this.showMessage(`Formula for "${measureObj.value}" updated`, "success");
            this.orm.call("calculation.preset", "get_all_presets", [this.id || false]).then(presets => {
                this.state.allDbPresets = presets || [];
            });
        });

        useBus(this.env.bus, "CY:EDIT_PRESET_FORMULA", (ev) => {
            const { index, type } = ev.detail;
            const measureObj = this.query_data[type][index];
            this.dialog.add(PresetApplyDialog, {
                fields: this.state.fields || [],
                models: this.state.models || [],
                sheet_id: this.id,
                editMeasure: measureObj,
                onApply: (updatedMeasureObj) => {
                    this.env.bus.trigger("CY:APPLY_PRESET", {
                        measureObj: updatedMeasureObj,
                        type
                    });
                },
            });
        });

        onMounted(() => {
            const accordion = document.getElementById('fieldListAccordion');
            if (!accordion) return;
            const isExpandable = (item) => item && !item.classList.contains('cy-config-section');
            accordion.querySelectorAll('.accordion-collapse.show').forEach(el => {
                const item = el.closest('.accordion-item');
                if (isExpandable(item)) item.classList.add('cy-accordion-open');
            });
            accordion.addEventListener('show.bs.collapse', (e) => {
                const item = e.target.closest('.accordion-item');
                if (isExpandable(item)) item.classList.add('cy-accordion-open');
            });
            accordion.addEventListener('hide.bs.collapse', (e) => {
                e.target.closest('.accordion-item')?.classList.remove('cy-accordion-open');
            });

            const optAccordion = document.getElementById('optionsAccordion');
            if (optAccordion) {
                optAccordion.querySelectorAll('.accordion-collapse.show').forEach(el => {
                    el.closest('.accordion-item')?.classList.add('cy-accordion-open');
                });
                optAccordion.addEventListener('show.bs.collapse', (e) => {
                    e.target.closest('.accordion-item')?.classList.add('cy-accordion-open');
                });
                optAccordion.addEventListener('hide.bs.collapse', (e) => {
                    e.target.closest('.accordion-item')?.classList.remove('cy-accordion-open');
                });
            }
        });
    }

    // ── Preset reconstruction handler ──────────────────────────────────
    async _onRebuildPreset(ev) {
        const { targetType, presetData } = ev.detail;
        const {
            value, rawFormula, calculation_type, variables,
            variable_configs, preset_id, monetaryInBase, alias
        } = presetData;

        try {
            const varConfigList = typeof variable_configs === 'string'
                ? JSON.parse(variable_configs || '[]') : (variable_configs || []);

            // Fresh DB template drag: column is __preset__<id>, no configured variable_configs yet
            if (presetData.column && String(presetData.column).startsWith('__preset__')) {
                this.dialog.add(PresetApplyDialog, {
                    fields: this.state.fields || [],
                    models: this.state.models || [],
                    sheet_id: this.id,
                    editMeasure: {
                        preset_id: preset_id ? String(preset_id) : undefined,
                        rawFormula: rawFormula || '',
                        value: value || '',
                        calculation_type: calculation_type || 'aggregate',
                    },
                    onApply: (measureObj) => {
                        this.env.bus.trigger("CY:APPLY_PRESET", { measureObj, type: targetType });
                    },
                });
                return;
            }

            // 1. Ensure all required models are present in the sheet
            // Use original_column if available to get the clean 'table.field' string
            const requiredTables = [...new Set(varConfigList.map(vc => (vc.original_column || vc.column).split('.')[0]))];
            for (const table of requiredTables) {
                if (!this.state.models.some(m => m.table === table)) {
                    await this.setModelFromTable({ model: table });
                }
            }

            // 2. Re-translate formula via RPC to get fresh SQL
            const tablesStr = requiredTables.join(', ');
            const freshColumnExpr = await this.orm.call(
                "calculation.preset",
                "translate_to_sql_advanced",
                [rawFormula, varConfigList, tablesStr, calculation_type]
            );

            // 3. Reconstruct measure object
            const measureObj = {
                type: 'measure',
                isPreset: true,
                rawFormula,
                calculation_type,
                aggregate_func: presetData.aggregate_func || false,
                variables: typeof variables === 'string' ? variables : JSON.stringify(variables),
                variable_configs: typeof variable_configs === 'string' ? variable_configs : JSON.stringify(varConfigList),
                value,
                original_label: value,
                alias: alias || generateSqlAlias(value, true),
                column: freshColumnExpr,
                query: `${freshColumnExpr} AS ${alias || generateSqlAlias(value, true)}`,
                preset_id: preset_id ? parseInt(preset_id) : false,
                monetaryInBase: monetaryInBase && monetaryInBase !== 'false' ? freshColumnExpr : false,
            };

            // 4. Update query_data
            this.query_data[targetType] = this.query_data[targetType].filter(m => m.alias !== measureObj.alias);
            this.query_data[targetType].push(measureObj);

            if (targetType === 'measure') {
                const activeMeasures = new Set(this.query_data.measure.map(m => m.alias));
                this.query_data.color_mappings.forEach(mapping => {
                    if (!activeMeasures.has(mapping.measure_alias)) {
                        mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                    }
                });
                if (this.ChartData.data && this.ChartData.data.color_mappings) {
                    this.ChartData.data.color_mappings = this.query_data.color_mappings;
                }
                if (this.query_data.annotations) {
                    this.query_data.annotations.forEach(mapping => {
                        if (!activeMeasures.has(mapping.measure_alias)) {
                            mapping.measure_alias = this.query_data.measure.length ? this.query_data.measure[0].alias : '';
                        }
                    });
                    if (this.ChartData.data && this.ChartData.data.annotations) {
                        this.ChartData.data.annotations = this.query_data.annotations;
                    }
                }
            }

            // Update fields list in sidebar to keep it in sync with latest metadata
            const fieldIndex = this.state.fields.findIndex(f => f.name === measureObj.alias || f.column === measureObj.column);
            if (fieldIndex !== -1) {
                this.state.fields[fieldIndex] = {
                    ...this.state.fields[fieldIndex],
                    ...measureObj,
                    name: measureObj.alias,
                    label: measureObj.value,
                    type: targetType,
                };
            } else {
                this.state.fields.push({
                    ...measureObj,
                    name: measureObj.alias,
                    label: measureObj.value,
                    type: targetType,
                    model: { name: 'Calculated' }
                });
            }

            this.genQuery();
            this.env.bus.trigger("CY:SYNC_CHILDREN", { targetType, children: this.query_data[targetType] });
            this.showMessage(`Preset "${value}" re-initialized`, "success");
        } catch (e) {
            this.showMessage(`Failed to re-initialize preset: ${e.message || 'Check logs'}`, "danger");
            console.error(e);
        }
    }

    get yZoneInfo() {
        return {
            condition: this.state.selectedType[1] === "pictorialBar" && this.query_data.measure.length < 2,
            message: "Two Measures are required.",
            className: "dropzone-warning-panel"
        }
    }

    setTableSave() {
        this.state.need_save = (this.state.models.length > 0)
        if (this.state.models.length > 0) {
            this.globalFilters()
        }
    }


    async _loadConfig() {
        this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
        if (this.id) {
            const value = this.navState.allRecords.findIndex(item => item == this.id)
            this.navState.recordValue = value + 1
        }
        if (this.props.action.context?.dashboard_id) {
            const context = this.props.action.context
            this.state.configs.push({ id: context.dashboard_id, display_name: context.display_name })
        }
        const res = await this.orm.call(this.model, 'get_config_data', [])
        this.state.sheetTypes = res.sheet_types
        this.previewLimit = {
            is_enable: res.is_enable,
            limit: res.limit
        }
        this.state.currency = res.currency
        this.state.themeColors = res.theme_color_ids || []
        this.state.darkMode = await this.orm.call('res.users', 'get_active', [])
        const dbPresets = await this.orm.call("calculation.preset", "get_all_presets", [this.id || false]);
        this.state.allDbPresets = dbPresets || [];
    }

    /** Raw sheet (re)load steps — no loading management (callers own that). */
    async _refreshSheet() {
        await this.updateData();
        this.genQuery()
        await this.generateChart()
        await this.globalFilters()
    }

    async updateSheet() {
        // Cover the async data-load + chart render with the loading overlay so
        // the view never flashes a half-built ("dirty") state. Used by Discard.
        this.state.savingMode = false
        this.state.loading = true
        try {
            await this._refreshSheet()
        } finally {
            requestAnimationFrame(() => {
                if (this.state) {
                    this.state.loading = false
                }
            })
        }
    }


    _nextPaint() {
        return new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 60)));
    }

    addColorMapping() {
        this.query_data.color_mappings.push({
            measure_alias: this.query_data.measure.length ? this.query_data.measure[0].alias : '',
            min_value: 0,
            max_value: '',
            color: '#344BD2',
            indicator: '',
        });
        if (this.ChartData.data) {
            this.ChartData.data = { ...this.ChartData.data, color_mappings: this.query_data.color_mappings };
        }
        this.openMappingEdit(this.query_data.color_mappings.length - 1);
    }

    openMappingEdit(index) {
        this.dialog.add(ColorMappingDialog, {
            mapping: { ...this.query_data.color_mappings[index] },
            measures: this.query_data.measure,
            onUpdate: (field, value) => this.updateColorMapping(index, field, value),
        });
    }

    getMeasureLabel(alias) {
        const m = this.query_data.measure.find(m => m.alias === alias);
        return m ? m.value : alias;
    }

    removeColorMapping(index) {
        this.query_data.color_mappings.splice(index, 1);
        if (this.ChartData.data) {
            this.ChartData.data = { ...this.ChartData.data, color_mappings: this.query_data.color_mappings };
        }
    }

    updateColorMapping(index, field, value) {
        this.query_data.color_mappings[index][field] = value;
        if (this.ChartData.data) {
            this.ChartData.data = { ...this.ChartData.data, color_mappings: this.query_data.color_mappings };
        }
    }

    getColorMappingErrors() {
        const errors = [];
        // Only evaluate rule-based mappings for overlaps, ignore point annotations
        const ruleBasedMappings = this.query_data.color_mappings.filter(m => !m._point_label);
        const measures = [...new Set(ruleBasedMappings.map(m => m.measure_alias))];

        measures.forEach(alias => {
            const mappings = ruleBasedMappings.filter(m => m.measure_alias === alias);
            // Sort by min value
            mappings.sort((a, b) => parseFloat(a.min_value) || 0 - parseFloat(b.min_value) || 0);

            for (let i = 0; i < mappings.length - 1; i++) {
                const current = mappings[i];
                const next = mappings[i + 1];
                const currentMin = parseFloat(current.min_value || 0);
                const currentMax = (current.max_value === 'all above' || current.max_value === '') ? Infinity : parseFloat(current.max_value);
                const nextMin = parseFloat(next.min_value || 0);

                if (currentMax > nextMin) {
                    const measureName = this.query_data.measure.find(m => m.alias === alias)?.value || alias;
                    errors.push(`Overlap in ${measureName}: [${currentMin} - ${currentMax === Infinity ? 'all above' : currentMax}] overlaps with [Min: ${nextMin}]`);
                }
            }
        });
        return errors;
    }

    onChartPointClick(params, itemId) {
        if (!this.ChartData.generate) return;
        if (params === null || params === undefined) return;
        const measureIndex = params.seriesIndex !== undefined ? params.seriesIndex : 0;
        const measure = this.query_data.measure[measureIndex];
        if (!measure) return;

        const alias = measure.alias;
        const dimensionName = params.name !== undefined ? String(params.name) : String(params.dataIndex);

        let numericValue = params.value;
        if (Array.isArray(numericValue)) {
            numericValue = numericValue[1] !== undefined ? numericValue[1] : numericValue[0];
        } else if (typeof numericValue === 'object' && numericValue !== null) {
            numericValue = numericValue.value !== undefined ? numericValue.value : 0;
        }

        if (!this.query_data.annotations) {
            this.query_data.annotations = [];
        }
        const existing = this.query_data.annotations.find(m =>
            m.measure_alias === alias &&
            m.dimension_label === dimensionName
        );

        if (this.env && this.env.bus) {
            this.env.bus.trigger('CHART_SHOW_ANNOTATION', {
                itemId: itemId,
                measureName: params.seriesName || measure.value || alias,
                alias,
                dimensionName,
                numericValue,
                existingNote: existing ? existing.notes : '',
                onSave: (note) => {
                    if (existing) {
                        existing.notes = note;
                    } else {
                        this.query_data.annotations.push({
                            measure_alias: alias,
                            dimension_label: dimensionName,
                            notes: note
                        });
                    }
                    if (this.ChartData.data) {
                        this.ChartData.data = { ...this.ChartData.data, annotations: [...this.query_data.annotations] };
                    }
                    this.state.need_save = true;
                    this.generateChart();
                }
            });
        }
    }

    /**
     * Generate the SQL query based on query data.
     */
    calculateLimit() {
        if (['pie', 'doughnut', 'radar', 'funnel'].includes(this.state.selectedType[1])) {
            if (this.state.limit > 30 || !this.state.limit) {
                if (this.state.limit !== 30) {
                    this.state.previousLimit = this.state.limit;
                }
                this.state.limit = 30;
                let message = `Maximum count of data can be shown in a ${this.state.selectedType[1]} chart is 30`;
                this.showMessage(message, "warning");
            }
        } else {
            if (this.state.previousLimit !== undefined && this.state.limit === 30) {
                this.state.limit = this.state.previousLimit;
            }
            this.state.previousLimit = undefined;
        }
    }

    genQuery() {
        if (this.state.isCustomSQL || this.isParsing) {
            return;
        }
        this.calculateLimit();
        const query_data = this.query_data;
        this.hasMonetary = false;



        if (!query_data.measure.length) {
            if (!this.isParsing) {
                this.state.query = '';
                this.state.previewQuery = '';
                this.ChartData.data = { data: [], type: this.state.selectedType ? this.state.selectedType[1] : 'bar', measures: [], dimension: [] };
                this.ChartData.generate = true;
                return;
            }
        }

        let columns = this._prepareQueryColumns();
        const { totalGroupBy, aggregate, isGrouping } = this._getGroupByTerms(columns);

        if (isGrouping) {
            const hasNoneMeasure = columns.some(item => item.type === 'measure' && (item.aggregate_func === 'NONE' || item.AGG === 'NONE'));
            if (hasNoneMeasure) {
                if (!this.noneAggregateWarned) {
                    this.notification.add("Please apply an aggregate function to all measures when using dimensions.", { type: "warning" });
                    this.noneAggregateWarned = true;
                }
                this.state.query = '';
                this.state.previewQuery = '';
                this.ChartData.data = { data: [], type: this.state.selectedType ? this.state.selectedType[1] : 'bar', measures: [], dimension: [] };
                this.ChartData.generate = true;
                return;
            } else {
                this.noneAggregateWarned = false;
            }
        } else {
            this.noneAggregateWarned = false;
        }


        // Always call _applyMeasureAggregates if we have measures, even without grouping (e.g. KPIs)
        columns = this._applyMeasureAggregates(columns, totalGroupBy, aggregate, isGrouping);

        const join = query_data.join.join(' \n');
        const columnStr = columns.length ? columns.map(item => item.query).join(', ') : '';
        const groupBy = totalGroupBy.length ? '\n GROUP BY ' + totalGroupBy.join(', ') : '';
        const orderBy = query_data.orderBy.length ? '\n ORDER BY ' + query_data.orderBy.map(item => {
            const matchedCol = columns.find(c => c.alias === item.alias || c.raw_column === item.column || c.column === item.column);
            const orderExpr = matchedCol ? matchedCol.alias : item.column;
            return `${orderExpr} ${item.sort_desc ? 'DESC' : 'ASC'}`;
        }).join(', ') : '';
        const whereData = query_data.where.filter(item => item.active).map(item => `(${item.domain})`);
        const where = whereData.length ? '\n WHERE ' + whereData.join(' AND ') : '';

        let limit = this.state.limit ? ` LIMIT ${this.state.limit}` : '';

        // Base query MUST NOT include dynamic sheet filters so the dashboard can toggle them properly
        this.state.query = `SELECT ${columnStr} FROM ${join} ${groupBy} ${orderBy}${limit}`;

        if (this.previewLimit.is_enable) {
            this._applyPreviewLimit(limit, columnStr, join, where, groupBy, orderBy);
        } else {
            this.state.previewQuery = `SELECT ${columnStr} FROM ${join} ${where} ${groupBy} ${orderBy}${limit}`;
        }
    }

    _prepareQueryColumns() {
        const query_data = this.query_data;
        let columns = [...query_data.dimension, ...query_data.measure].map(item => {
            let col = { ...item };
            col.raw_column = col.raw_column || col.column;
            if (col.monetaryInBase) {
                this.hasMonetary = true;
                const replaceString = col.monetaryInBase.replaceAll('{selectedCurrency}', `${this.state.currency?.id}`);
                col.query = `${replaceString} AS ${col.alias}`;
            }
            if (col.field_type === 'image' || col.field_type === 'binary') {
                const tableName = col.model ? col.model.table : col.raw_column.split('.')[0];
                const modelName = col.model ? col.model.name : tableName.replace('_', '.');
                const fieldName = col.name || col.raw_column.split('.')[1];
                const cyImageExpr = `CONCAT('CY_IMAGE:', '${modelName}', ':', '${fieldName}', ':', COALESCE(${tableName}.id::text, ''))`;
                col.column = cyImageExpr;
                col.query = `${cyImageExpr} AS ${col.alias}`;
            }
            return col;
        });

        const activeGroupCols = new Set(
            query_data.groupBy.filter(g => g.source_column).map(g => g.source_column)
        );

        columns = columns.map(col => {
            if (col.type === 'dimension' && /^TO_CHAR\s*\(/i.test(col.query) && !activeGroupCols.has(col.column)) {
                return { ...col, query: `${col.column} AS ${col.alias}` };
            }
            return col;
        });
        return columns;
    }

    _getGroupByTerms(columns) {
        const query_data = this.query_data;
        const dateGroupedCols = new Set(
            query_data.groupBy.filter(g => g.source_column).map(g => g.source_column)
        );

        const groupColumn = columns
            .filter(item => item.type === 'dimension')
            .filter(item => !dateGroupedCols.has(item.column))
            .map(item => {
                // If it's a relational field, group by ID as well to ensure distinct records
                if (item.relational && item.relational.table) {
                    return [`${item.relational.table}.id`, item.column];
                }
                if (item.field_type === 'image' || item.field_type === 'binary') {
                    // Group by the table ID to avoid grouping by binary image data
                    const tableName = item.model ? item.model.table : (item.raw_column ? item.raw_column.split('.')[0] : 'id');
                    return `${tableName}.id`;
                }
                return item.column;
            })
            .flat();

        const groupByQuery = query_data.groupBy.length ? query_data.groupBy
            .filter(item => !/(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(item.column))
            .map(item => {
            if (item.field_type === 'image' || item.field_type === 'binary') {
                const tableName = item.model ? item.model.table : (item.raw_column || item.column).split('.')[0];
                return `${tableName}.id`;
            }
            return item.column;
        }) : [];
        // hasAggregates: true only when at least one measure column already carries an aggregate function
        const hasAggregates = columns.some(
            item => item.type === 'measure' && /(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(item.query)
        );
        // hasExplicitAggFunc: true when a user explicitly chose an AGG from the dropdown on any measure (except NONE)
        const hasExplicitAggFunc = columns.some(
            item => item.type === 'measure' && (item.aggregate_func || item.AGG) && !['NONE'].includes(item.aggregate_func || item.AGG)
        );

        const totalGroupBy = [...new Set([...groupByQuery, ...groupColumn])];
        // Only activate GROUP BY when there is an explicit group-by tag OR real aggregation is present
        const isGrouping = groupByQuery.length > 0 || hasAggregates || hasExplicitAggFunc;

        return {
            totalGroupBy: isGrouping ? totalGroupBy : [],
            aggregate: 'SUM', // Default aggregate (used as fallback when grouping is active)
            isGrouping,
        };
    }

    _applyMeasureAggregates(columns, totalGroupBy, aggregate, isGrouping) {
        return columns.map(item => {
            if (item.type === 'measure' && !/(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(item.query)) {
                const alias = item.alias;
                let rawExpr;
                // Use the user's explicit choice, or fall back to the default
                // aggregate when grouping is active.
                const itemAggregate = item.aggregate_func || item.AGG || null;

                // No aggregation selected AND no grouping active → raw column.
                if (!itemAggregate && !isGrouping) {
                    return item;
                }

                // Effective aggregate: user choice first, then default (SUM)
                const effectiveAgg = itemAggregate || aggregate;

                if (item.monetaryInBase) {
                    rawExpr = item.monetaryInBase.trim().replaceAll('{aggregate}', effectiveAgg);
                } else {
                    const rawCol = item.raw_column || item.column;
                    rawExpr = rawCol.replaceAll('{aggregate}', effectiveAgg);
                }

                // Universally replace {selectedCurrency} in the evaluated raw expression to avoid PostgreSQL errors.
                if (rawExpr.includes('{selectedCurrency}')) {
                    rawExpr = rawExpr.replaceAll('{selectedCurrency}', `${this.state.currency?.id}`);
                }

                if (item.calculation_type === 'aggregate') {
                    // Aggregated presets: the formula expression is already fully built
                    // (contains subqueries or AGG() calls from translate_to_sql_advanced).
                    return { ...item, query: `${rawExpr} AS ${alias}` };
                }

                if (item.calculation_type !== 'row' && /(\bSUM\b|\bAVG\b|\bCOUNT\b|\bMIN\b|\bMAX\b)/i.test(rawExpr)) {
                    return { ...item, query: `${rawExpr} AS ${alias}` };
                }

                if (effectiveAgg === 'NONE') {
                    return { ...item, query: `${rawExpr} AS ${alias}` };
                }

                return { ...item, query: `${effectiveAgg}(${rawExpr}) AS ${alias}` };
            }
            return item;
        });
    }

    _applyPreviewLimit(limit, columnStr, join, where, groupBy, orderBy) {
        let previewLimit = limit && this.state.limit < parseInt(this.previewLimit.limit)
            ? limit
            : ` LIMIT ${this.previewLimit.limit}`;

        if (this.state.limit > parseInt(this.previewLimit.limit) || !this.state.limit) {
            let message = `The data shown in the preview graph is not accurate.
                The data is limited to ${this.previewLimit.limit} rows or groups. If
                you want more data to be shown please change the limit in settings`;
            this.showMessage(message, "warning");
        }
        this.state.previewQuery = `SELECT ${columnStr} FROM ${join} ${where} ${groupBy} ${orderBy}${previewLimit}`;
    }
    /**
     * Check whether there is at least one column and one table
     */
    get isGoodQuery() {
        return this.query_data.measure.length && this.query_data.join.length;
    }

    /**
     * Execute the generated query to generate the graph
     */
    generateChart() {
        try {
            if (this.isGoodQuery || this.state.isCustomSQL) {
                this.orm.call("dashboard.config", "sql_execute", [
                    this.state.previewQuery
                ]).then((data) => {
                    if (!data || (Array.isArray(data) && data.length === 0) || (data && data.__query_error__)) {
                        const msg = data && data.message
                            ? `Query Error: ${data.message}`
                            : 'The query returned no data. Please check your configuration.';
                        this.showMessage(msg, 'danger');
                        this.ChartData.data = { data: [], type: this.state.selectedType ? this.state.selectedType[1] : 'bar', measures: [], dimension: [] };
                        this.ChartData.generate = true;
                        return;
                    }
                    let finalMeasures;
                    let finalDimensions;
                    if (this.state.isCustomSQL) {
                        // AUTO-DETECT from the actual data returned by Postgres
                        finalMeasures = [];
                        finalDimensions = [];
                        const firstRow = data[0];
                        if (firstRow) {
                            Object.entries(firstRow).forEach(([key, value]) => {
                                if (typeof value === 'number') {
                                    finalMeasures.push(key);
                                } else {
                                    finalDimensions.push(key);
                                }
                            });
                        }
                    } else {
                        // NORMAL mode: use the drag-and-drop configuration
                        finalMeasures = this.query_data.measure.map(item => item.alias);
                        finalDimensions = this.query_data.dimension.map(item => item.alias);
                    }

                    this.ChartData.data = {
                        data,
                        name: this.state.name || '',
                        measures: finalMeasures,
                        measureNames: this.query_data.measure.reduce((acc, m) => {
                            if (m.isPreset) {
                                acc[m.alias] = m.value;
                            }
                            return acc;
                        }, {}),
                        dimension: finalDimensions,
                        dimension_axis: this.query_data.dimension_axis,
                        type: this.state.selectedType[1],
                        color_mappings: this.query_data.color_mappings,
                        annotations: this.query_data.annotations,
                    };
                    this.ChartData.generate = true;
                });
            }
        } catch (error) {
            this.ChartData.data = { data: [], type: this.state.selectedType ? this.state.selectedType[1] : 'bar', measures: [], dimension: [] };
            this.ChartData.generate = true;
        }
    }

    /**
     * Set the models and fields for the sheet.
     * @param {Array} models - The list of models.
     */
    setModel(models) {
        this.state.models = models
        this.setFields()
        this.setTableSave()
    }

    /**
     * Set the currency for monetary measures in sheet.
     * @param {Array} currency - id and display_name of currency.
     */
    setCurrency(currency) {
        this.state.currency = currency
        this.genQuery()
    }

    checkHasLink(model) {
        var hasField = []
        var hasModel = []
        var fields = []
        fields = fields.concat(this.query_data.dimension)
        fields = fields.concat(this.query_data.measure)
        fields = fields.concat(this.query_data.groupBy)
        fields = fields.concat(this.query_data.orderBy)
        fields.forEach((field) => {
            if (field.query.includes(model.table))
                hasField.push(field)
        })
        var joinCheck = this.query_data.joinData.filter(join => join.model != model.model)
        joinCheck.forEach(join => {
            if (join.join.includes(model.table))
                hasModel.push(join)
        })
        return {
            fields: hasField,
            models: hasModel,
            link: !!(hasField.length || hasModel.length)
        }
    }

    /**
     * Set the available fields for the sheet.
     */
    setFields() {
        var fields = []
        for (var model of this.state.models) {
            Object.values(model.fields).forEach(field => {
                if (!this.avoid_fields.includes(field.name) && !this.avoid_field_types.includes(field.type)) {
                    const baseField = {
                        model: {
                            id: field.model.id,
                            name: field.model.name,
                            table: field.model.table,
                            relation: field.relation
                        },
                        name: field.name,
                        label: `${field.model.name} > ${field.string}`,
                        column: `${field.model.table}.${field.name}`,
                        field_type: field.type,
                        selection: field.selection || false,
                        is_json: field.type == 'char' && field.translate ? true : false
                    };

                    if (field.name === 'id') {
                        // Push as dimension
                        fields.push({ ...baseField, type: 'dimension' });
                        // Push as measure (ID is numeric so it naturally works with aggregations)
                        fields.push({ ...baseField, type: 'measure' });
                    } else {
                        fields.push({
                            ...baseField,
                            type: this.measures_field_types.includes(field.type) ? 'measure' : 'dimension'
                        });
                    }
                }
            })
        }
        this.state.fields = fields
    }

    /**
     * Get the list of measures.
     * @returns {Array} - The list of measures.
     */
    get measures() {
        return this.state.fields.filter(field => field.type == 'measure' && !field.isPreset)
    }

    /**
     * Get the list of presets.
     * @returns {Array} - The list of presets.
     */
    get presets() {
        return (this.state.allDbPresets || []).map(p => ({
            label: p.name,
            name: (p.name || '').toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '') || `preset_${p.id}`,
            column: `__preset__${p.id}`,
            field_type: 'float',
            model: { table: '__preset__', name: 'Preset', relation: '' },
            isPreset: true,
            rawFormula: p.formula || '',
            variables: p.variables || '[]',
            variable_configs: '[]',
            calculation_type: p.calculation_type || 'aggregate',
            aggregate_func: false,
            preset_id: p.id,
            monetaryInBase: false,
            is_json: false,
        }));
    }

    /**
     * Get a object with
     */
    get getAxisData() {
        const getLimit = (yAxisType) => {
            let xLimit, yLimit;
            switch (this.state.selectedType[1].toLowerCase()) {
                case "gauge":
                    xLimit = 0;
                    yLimit = 1;
                    break;
                case "kpi":
                    xLimit = 0;
                    yLimit = 1;
                    break;
                case "heatmap":
                    xLimit = 1;
                    yLimit = 2;
                    break;
                case "map":
                    xLimit = 1;
                    yLimit = 1;
                    break;
                case "pictorialbar":
                    xLimit = 1;
                    yLimit = 2;
                    break;
                case "funnel":
                    xLimit = 1;
                    yLimit = 1;
                    break;
                default:
                    xLimit = 1;
                    yLimit = 5;
            }
            if (yAxisType === "measure") {
                return { xLimit, yLimit };
            } else {
                return { xLimit: yLimit, yLimit: xLimit };
            }
        };

        if (this.state.selectedType[1].toLowerCase() === "kpi") {
            // Force clear the X axis if anything is there
            if (this.query_data.dimension?.length) {
                this.query_data.dimension = [];
            }

            // This object is the return value
            return {
                x: [],
                xType: "dimension",
                y: this.query_data.measure,
                yType: "measure",
                xLimit: 0,
                yLimit: 1,
            };
        }
        if (this.state.selectedType[1].toLowerCase() === "gauge") {
            // Force clear dimensions
            if (this.query_data.dimension?.length) {
                this.query_data.dimension = [];
            }

            return {
                x: [],
                xType: "dimension",
                y: this.query_data.measure,
                yType: "measure",
                xLimit: 0,
                yLimit: 1,
            };
        }

        // Normal flow for other chart types
        let type = "both";
        let yType = "both";

        if (this.query_data.dimension_axis === "x") {
            if (this.query_data.dimension.length || this.query_data.measure.length) {
                type = "dimension";
                yType = "measure";
            }
            const { xLimit, yLimit } = getLimit(yType);
            return {
                x: this.query_data.dimension,
                xType: type,
                y: this.query_data.measure,
                yType,
                xLimit,
                yLimit,
            };
        }

        if (this.query_data.dimension.length || this.query_data.measure.length) {
            type = "measure";
            yType = "dimension";
        }
        const { xLimit, yLimit } = getLimit(yType);
        return {
            x: this.query_data.measure,
            xType: type,
            y: this.query_data.dimension,
            yType,
            xLimit,
            yLimit,
        };
    }

    /**
     * Get the list of dimensions.
     * @returns {Array} - The list of dimensions.
     */
    get dimensions() {
        return this.state.fields.filter(field => field.type == 'dimension')
    }

    /**
     * Save the sheet configuration.
     */
    async onSave() {
        const mappingErrors = this.getColorMappingErrors();
        if (mappingErrors.length > 0) {
            this.notification.add(_t("Cannot save chart: Color mapping range overlaps detected. Please fix errors in the Color Mapping tab."), {
                type: "danger",
                title: _t("Validation Error")
            });
            return;
        }
        if (this.state.saveClicked) return
        if (!this.state.name) {
            this.showMessage('Please provide a name first', 'danger')
            return
        }
        this.state.saveClicked = true
        this.state.savingMode = true
        this.state.loading = true
        this.sheet?.el?.querySelector('.cy-sheet-loading-overlay')?.classList.remove('cy-overlay-hidden')
        try {

            await this._nextPaint()
            var joinData = [...this.query_data.joinData]
            joinData.forEach((item) => {
                delete item.model?.fields
            })
            if (this.state.selectedType[1] == 'kpi') {
                var kpiEl = this.sheet.el.querySelector(".kpi-sheet-parent")
                const canvas = kpiEl ? await html2canvas(kpiEl, { scale: 1, logging: false }) : false
                if (canvas) {
                    this.state.image = canvas.toDataURL('image/png');
                }
            } else if (this.state.selectedType[1] == 'table') {
                var el = this.sheet.el.querySelector(".cy_table_sheet")
                const canvas = el ? await html2canvas(el, { scale: 1, logging: false }) : false
                if (canvas) {
                    this.state.image = canvas.toDataURL('image/png');
                }
            }
            const isInteger = value => typeof value === 'number' && isFinite(value, "") && Math.floor(value) === value;

            let vals = {
                image: this.Image,
                id: this.id || false,
                limit: this.state.limit,
                joinData: joinData,
                group_by: this.query_data.groupBy,
                order_by: this.query_data.orderBy,
                dimension: this.query_data.dimension[0],
                measure: this.query_data.measure,
                where: this.query_data.where.map(filter => {
                    return {
                        ...filter,
                        id: isInteger(filter.id) ? filter.id : false
                    }
                }),
                type: this.state.selectedType,
                dimension_axis: this.query_data.dimension_axis,
                query: this.state.query,
                configs: this.state.configs,
                unlink_list: this.unlinkList,
                options: this.filterOptions,
                kpi: this.state.kpiValue,
                currency: this.state.currency?.id || false,
            }
            vals['name'] = this.state.name.substring(0, 32)
            vals['color_mappings'] = this.query_data.color_mappings
            vals['annotations'] = this.query_data.annotations
            const data = await this.orm.call(this.model, 'update_data', [vals])
            this.id = data.rec_id
            this.state.id = data.rec_id
            this.saveManually(this.id)
            this.showMessage("Saved", "success")
            this.state.need_save = false
            // Just-saved config becomes the clean baseline → hide Save/Discard.
            this._markSaved()
            const { show_position_warning } = data
            if (show_position_warning) {
                this.showMessage(`As the chart shifted from being a KPI to ${this.state.selectedType[1]}, it required removing the previous positions.`, "warning")
            }
            this.isNewSheet = data.is_new_sheet;
            data.sheet_filter.forEach(item => {
                this.query_data.where.find(where => where.name === item.name).id = item.id
            })
            this.navState.allRecords = await this.orm.search('dashboard.sheet', [])
            // Refresh axis state from DB so every item has the correct DB id.
            // Without this, groupBy/dimension/measure items stay id-less and
            // the backend creates duplicate records on the next save.
            await this.updateData()
            // Re-populate globalFilters after reload so filterOptions stays
            // accurate (important for the next Save click).
            await this.globalFilters()
            // Reset unlinkList after a successful save so already-unlinked
            // ids are not sent again on the next save.
            this.unlinkList = { axis: [], tables: [], where: [], configs: [] }
        }
        catch (error) {

            console.error("Sheet save failed:", error)
            this.showMessage(`There was an error while saving the record`, "warning")
        }
        finally {
            this.state.saveClicked = false
            // Give the reloaded chart a frame to paint before fading the overlay
            // out. Guarded against a component destroyed mid-save.
            requestAnimationFrame(() => {
                if (this.state) {
                    this.state.loading = false
                }
            })
        }
    }

    async globalFilters() {
        const ids = this.state.configs.map((config) => config.id);
        const globalFilters = await this.orm.searchRead('dashboard.global.filter', [['dashboard_config_id', 'in', ids]], [])
        const filteredDict = {};
        globalFilters.forEach((filter) => {
            const { dashboard_config_id, id, name, code, type, relation, operator } = filter;

            if (dashboard_config_id) {
                if (!filteredDict[dashboard_config_id[1]]) {
                    filteredDict[dashboard_config_id[1]] = [];
                }
                filteredDict[dashboard_config_id[1]].push({ name, id, code, type, relation, operator });
            }
        });
        this.state.globalFilters = filteredDict

        // Auto-populate default filters so that saving without opening the
        // modal still persists the defaults to the database.
        if (Array.isArray(this.filterOptions) || !this.filterOptions) {
            this.filterOptions = {};
        }
        for (const group of Object.values(this.state.globalFilters)) {
            for (const filter of group) {
                if (!this.filterOptions[filter.id]) {
                    const options = this.getGlobalFilters(filter.type, filter.relation);
                    this.getDefaultOption(options, filter);
                }
            }
        }
    }

    get Image() {
        return this.state.image
    }

    setImage(image) {
        this.state.image = image
    }

    async updateData() {
        if (!this.id) return
        const data = await this.orm.call(this.model, 'get_sheet_data', [this.state.id])
        if (data.has_error.error) {
            const model = data.has_error.value.length > 1 ? "models" : "model"
            this.notification.add(_t(`The sheet cannot display the graph because it is missing some information. It cannot access the ${model}: ${data.has_error.value.join(", ")}.`), { type: "warning" });
        }
        this.state.name = data.name

        this.state.currency = data.currency[0] || this.state.currency
        this.state.limit = data.limit
        this.state.selectedType = data.type
        this.state.configs = data.configs
        data.models.forEach(model => {
            for (var i in model.fields) {
                model.fields[i].model = model
            }
        })
        this.setModel(data.models)
        this.query_data.join = data.join
        this.query_data.joinData = data.joinData
        // Restore field_type and date grouping state so options and tags persist
        this.query_data.dimension = data.dimension.map(dim => {
            if (!dim.field_type && dim.column) {
                const [tableName, fieldName] = dim.column.split('.')
                for (const model of data.models) {
                    if (model.table === tableName && model.fields && model.fields[fieldName]) {
                        dim.field_type = model.fields[fieldName].type
                        break
                    }
                }
            }
            // If there's a matching date groupBy, restore the markers
            const dateGroup = data.groupBy.find(g => g.source_column === dim.column && g.date_group)
            if (dateGroup) {
                dim.DATE_GROUP = dateGroup.date_group
                dim.original_value = dim.value
            }
            // Map backend snake_case to frontend camelCase for presets
            dim.isPreset = dim.is_preset;
            dim.rawFormula = dim.raw_formula;
            return dim
        })
        this.query_data.measure = data.measure.map(msr => {
            // Map backend snake_case to frontend camelCase for presets
            msr.isPreset = msr.is_preset;
            msr.rawFormula = msr.raw_formula;
            return msr;
        });
        this.query_data.groupBy = data.groupBy
        this.query_data.orderBy = data.orderBy
        this.query_data.dimension_axis = data.dimension_axis
        this.query_data.where = data.where
        this.filterOptions = Array.isArray(data.options) ? {} : (data.options || {})
        this.state.kpiValue = data.kpi
        this.query_data.color_mappings = (data.color_mappings || []).map(m => ({
            ...m,
            notes: m.notes || ''
        }));
        this.query_data.annotations = data.annotations || []
        this.query_data.dimension_axis = data.dimension_axis
        // Reload DB presets using the confirmed sheet ID
        const dbPresets = await this.orm.call("calculation.preset", "get_all_presets", [this.state.id || false]);
        this.state.allDbPresets = dbPresets || [];
        // Loaded config is the clean baseline — hide Save/Discard until edited.
        this._markSaved();
    }

    _canonicalKpi(kpi) {
        if (!kpi || typeof kpi !== 'object') {
            return kpi;
        }
        return {
            target: kpi.target || false,
            measureView: kpi.measureView || 'View 1',
            description: kpi.description || false,
            redirect: kpi.redirect || false,
            name: kpi.name || this.state.name,
            icon: kpi.icon || 'ri-time-line',
        };
    }

    /**
     * Serialized snapshot of every savable config field (mirrors onSave's `vals`,
     * minus the rendered image / transient flags). Used to detect unsaved changes.
     * Wrapped in try/catch: on any serialization failure we return a unique string
     * so isDirty stays true (fail toward showing Save — never hide a real change).
     */
    get configSignature() {
        const s = this.state, qd = this.query_data;
        try {
            return JSON.stringify({
                name: s.name,
                limit: s.limit,
                type: s.selectedType,
                configs: s.configs,
                kpi: this._canonicalKpi(s.kpiValue),
                currency: s.currency?.id,
                dimension: qd.dimension,
                measure: qd.measure,
                groupBy: qd.groupBy,
                orderBy: qd.orderBy,
                dimension_axis: qd.dimension_axis,
                where: qd.where,
                color_mappings: qd.color_mappings,
                annotations: qd.annotations,
                // joinData items hold a back-reference to their model (circular) —
                // strip it before serializing.
                joinData: (qd.joinData || []).map(j => ({ ...j, model: undefined })),
            });
        } catch (e) {
            return `__err__${s.name}_${Date.now()}`;
        }
    }

    /** True when the live config differs from the last saved/loaded snapshot. */
    get isDirty() {
        return this.configSignature !== this.state.savedSignature;
    }

    /** Capture the current config as the "clean" baseline (after load / save). */
    _markSaved() {
        this.state.savedSignature = this.configSignature;
    }

    showMessage(message, type) {
        this.notification.add(message, { type })
    }

    onFilterClick() {
        const where = {
            name: "",
            domain: "",
            domain_py_expression: [],
            active: true,
        }
        this.dialog.add(SheetFilterDomain, {
            confirm: this.addWhere.bind(this),
            models: this.state.models,
            fields: this.state.fields,
            where,
            isEdit: false
        })
    }

    addWhere(domain) {
        if (domain.isEdit) {
            this.query_data.where = [
                ...this.query_data.where.filter(item => item.id !== domain.id),
                domain
            ]
        } else {
            this.query_data.where.push(domain)
        }
        this.genQuery()
    }

    updateWhere(where) {
        where.active = !where.active
        this.genQuery()
    }

    onClickSheetType(type) {
        // set the new type
        this.state.selectedType = type;

        // if KPI is selected -> clear X-axis related fields
        if (type && type[1] && String(type[1]).toLowerCase() === 'kpi') {
            // clear X axis related arrays so KPI has no X-axis
            this.query_data.dimension = [];
            this.query_data.groupBy = [];
            this.query_data.orderBy = [];
        }

        // regenerate chart preview
        this.genQuery();
        this.generateChart();
    }

    async onDashboardSelect(config) {
        const conf = await this._nameGet(config[0].id)
        this.state.configs.push(conf)
        this.setTableSave()
        this.globalFilters()
    }

    async _nameGet(recordId) {
        const result = await this.orm.read("dashboard.config", [recordId], ["display_name"]);
        return { id: result[0].id, display_name: result[0].display_name };
    }

    dashboardDomain() {
        var ids = this.state.configs.map(item => item.id)
        return [["id", "not in", ids]]
    }

    onRemoveDashboard(config) {
        this.state.configs = this.state.configs.filter(item => item.id !== config.id)
        this.unlinkList.configs.push(config.id)
    }

    get style() {
        return {
            height: `100%`,
            width: `100%`,
        }
    }

    onDelete() {
        this.dialog.add(SheetDeleteDialog, {
            id: this.id,
            removeManually: this.removeManually.bind(),
            model: this.model,
            body: `Are you sure you want to delete ${this.state.name}?`,
            onConfirm: () => {
                // Cover the sheet while it is torn down and the list reloads.
                this.state.savingMode = false
                this.state.loading = true
                this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "Successfully Deleted",
                        'type': 'success',
                        'sticky': false,
                    }
                })
                browser.history.go(-1)
            }
        })
    }

    onFilterGroupCardClick(ev) {
        const key = ev.currentTarget.dataset.gfkey
        const rect = ev.currentTarget.getBoundingClientRect()
        const modalWidth = 280
        const modalHeight = 300
        const left = rect.right + 8
        const top = Math.min(rect.top, window.innerHeight - modalHeight - 16)
        this.state.filterModalPos = { top, left }
        this.state.activeFilterGroup = key
    }

    openFilterGroupModal(key) {
        this.state.activeFilterGroup = key
    }

    closeFilterGroupModal() {
        this.state.activeFilterGroup = null
    }

    onOptionClick(option, filter) {
        if (!option) return;
        this.filterOptions[filter] = {
            'global_filter_id': filter,
            'field': option.model.table + '.' + option.name,
            'name': option.label
        };
    }

    getGlobalFilters(type, relation) {
        if (relation) {
            return this.state.fields.filter(item => item.field_type === type && item.model.relation === relation)
        }
        return this.state.fields.filter(item => item.field_type === type)
    }

    getDefaultOption(options, filter) {
        var selectedOption = this.getSelectedOption(filter)
        if (selectedOption !== undefined) {
            return options.find(item => item.label === selectedOption.name)
        }
        ;
        const { code } = filter
        const primaryModel = this.state.models.find(m => m.linked_by && !m.linked_by.string)
            || this.state.models[0];
        const primaryTable = primaryModel ? primaryModel.table : null;
        const findField = (fieldName) => {
            if (primaryTable) {
                const primary = options.find(
                    item => item.name === fieldName && item.model && item.model.table === primaryTable
                );
                if (primary) {
                    return primary;
                }
            }
            const fallback = options.find(item => item.name === fieldName);
            return fallback;
        };
        const getOptions = () => {
            switch (code) {
                case "start-date":
                case "end-date":
                    return options.find(item => item.name === 'create_date');
                case "company":
                    return options.find(item => item.name === 'company_id');
                case "user":
                    return options.find(item => item.name === 'user_id');
                default:
                    return false;
            }
        }
        var option = getOptions()
        this.onOptionClick(option, filter.id)
        return option
    }

    getSelectedOption(filter) {
        if (this.filterOptions.length == undefined) {
            var value = Object.values(this.filterOptions).find(item => item.global_filter_id === filter.id);
            return value
        }
        return false
    }

    onClickDuplicate() {
        this.orm.call(this.model, 'duplicate_sheet', [this.id]).then(async rec_id => {
            if (rec_id) {
                this.saveManually(rec_id);
                this.id = rec_id;
                this.state.id = rec_id;
                this.isNewSheet = false;
                await this.updateData();
            }
        })
    }

    setContentEmpty() {
        var axis = [...this.query_data.groupBy, ...this.query_data.orderBy, ...this.query_data.measure, ...this.query_data.dimension]
        axis.forEach(item => {
            if (item.id) {
                this.unlinkList.axis.push(item.id)
            }
        })
        this.state.models.forEach(item => {
            if (item.linked_by?.id) {
                this.unlinkList.tables.push(item.linked_by.id)
            }
        })
        this.query_data.where.forEach(item => {
            if (item.id) {
                this.unlinkList.where.push(item.id)
            }
        })
        this.state.models = []
        this.query_data.join = []
        this.query_data.joinData = []
        this.query_data.measure = []
        this.query_data.dimension = []
        this.query_data.where = []
        this.query_data.groupBy = []
        this.query_data.orderBy = []
        this.state.limit = false
    }

    onToggleQuery() {
        this.state.toggleQuery = !this.state.toggleQuery;
    }

    async onQueryChange(query) {
        try {
            this.isParsing = true;
            this.state.query = query;
            this.setContentEmpty()
            const parser = new SQLQueryParser(query);
            const parsedData = parser.parse();
            const tableAlias = {}
            if (!parsedData.joins) {
                this.isParsing = false;
                this.state.isCustomSQL = true;
                this.state.previewQuery = query;
                this.generateChart();
                return;
            }
            // Joins
            for (var join of parsedData.joins) {
                var alias = join.alias || join.join
                var n_join = join.join
                var split = this.splitJoinOnClause(n_join)
                n_join = n_join.replace(`AS ${alias}`, '')
                tableAlias[alias] = join.model
                if (split) {
                    split.forEach(item => {
                        var [table, field] = item
                        var table_name = tableAlias[table] || table
                        n_join = n_join.replace(`${table}.${field}`, `${table_name}.${field}`)
                    })
                }
                join.join = n_join
                await this.setModelFromTable(join)
            }

            let parsingIncomplete = false;

            // Measure and Dimension
            parsedData.columns.forEach(column => {
                var [mode, col] = this.splitStringWithParentheses(column.column)
                let splitColMatches = col.match(/([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)/);
                if (!splitColMatches) {
                    parsingIncomplete = true;
                    return;
                }
                var table = splitColMatches[1];
                var field = splitColMatches[2];
                var table_name = tableAlias[table] || table
                if (table_name) {
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    column.column = column.column.replace(val_to_change, val_new)
                    column.query = column.query.replace(val_to_change, val_new)
                    col = col.replace(val_to_change, val_new)
                }
                var fieldData = this.state.fields.filter(item => {
                    return item.model.table == table_name && item.name == field
                })
                if (fieldData.length) {
                    const targetType = mode ? 'measure' : fieldData[0].type;
                    this.updateColumns(fieldData, column, targetType, mode, col)
                } else {
                    parsingIncomplete = true;
                }
            })
            // Sheet Filters
            parsedData.where.forEach(where => {
                Object.entries(tableAlias).forEach((alias) => {
                    var val_to_change = ` ${alias[0]}.`
                    var val_new = ` ${alias[1]}.`
                    where.domain = where.domain.replaceAll(val_to_change, val_new)
                })
                this.query_data.where.push(where)
            })
            // Group by
            parsedData.groupBy.forEach(groupBy => {
                let splitColMatches = groupBy.column.match(/([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)/);
                if (splitColMatches) {
                    var table = splitColMatches[1];
                    var field = splitColMatches[2];
                    var table_name = tableAlias[table] || table
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    groupBy.column = groupBy.column.replace(val_to_change, val_new)
                    groupBy.query = groupBy.query.replace(val_to_change, val_new)
                    var fieldData = this.state.fields.filter(item => {
                        return item.model.table == table_name && item.name == field
                    })
                    if (fieldData.length) {
                        this.updateColumns(fieldData, groupBy, 'groupBy')
                    } else {
                        parsingIncomplete = true;
                    }
                } else {
                    parsingIncomplete = true;
                }
            })
            // Order by
            parsedData.orderBy.forEach(orderBy => {
                let splitColMatches = orderBy.column.match(/([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)/);
                if (splitColMatches) {
                    var table = splitColMatches[1];
                    var field = splitColMatches[2];
                    var table_name = tableAlias[table] || table
                    var val_to_change = `${table}.${field}`
                    var val_new = `${table_name}.${field}`
                    orderBy.column = orderBy.column.replace(val_to_change, val_new)
                    orderBy.query = orderBy.query.replace(val_to_change, val_new)
                    var fieldData = this.state.fields.filter(item => {
                        return item.model.table == table_name && item.name == field
                    })
                    if (fieldData.length) {
                        this.updateColumns(fieldData, orderBy, 'orderBy')
                    } else {
                        parsingIncomplete = true;
                    }
                } else {
                    parsingIncomplete = true;
                }
            })
            // Limit
            this.state.limit = parsedData.limit || false

            // Sync join data
            var joinsArray = this.state.models.map(model => model.linked_by?.join).filter(item => item);
            var joinDataArray = this.state.models.map(model => {
                if (!model.linked_by) return null;
                var joinObj = { ...model.linked_by };
                joinObj.model_id = model.id;
                return joinObj;
            }).filter(item => item);

            this.query_data.join = joinsArray;
            this.query_data.joinData = joinDataArray;

            this.state.isCustomSQL = parsingIncomplete;
            this.state.previewQuery = query;
            this.isParsing = false;
            this.setTableSave()
            if (this.state.isCustomSQL) {
                this.generateChart();
            } else {
                this.genQuery();
            }
        } catch {
            this.isParsing = false;
            this.state.isCustomSQL = true;
            this.state.query = query;
            this.state.previewQuery = query;
            this.generateChart();
        }
    }

    splitStringWithParentheses(input) {
        input = input.trim();
        const firstParen = input.indexOf('(');
        const lastParen = input.lastIndexOf(')');
        if (firstParen > 0 && lastParen === input.length - 1) {
            const firstPart = input.substring(0, firstParen).trim();
            if (/^[a-zA-Z0-9_]+$/.test(firstPart)) {
                const secondPart = input.substring(firstParen + 1, lastParen).trim();
                return [firstPart, secondPart];
            }
        }
        return [false, input];
    }

    splitJoinOnClause(joinClause) {
        const regex = /JOIN\s+([\w_]+)\s+\bAS\b\s+([\w_]+)?\s+ON\s+([^]+?)(?=(?:JOIN|$))/ig;
        const matches = [...joinClause.matchAll(regex)];
        if (matches.length > 0) {
            const [, table, alias, onCondition] = matches[0];
            const [leftTable, leftField, rightTable, rightField] = onCondition.split(/[.=]/).map((part) => part.trim());
            return [
                [leftTable || table, leftField],
                [rightTable || (alias || table), rightField],
            ];
        }
        return null;
    }

    updateColumns(field, column, type, mode, innerCol) {
        var cur_field = field[0]
        var rawCol = `${cur_field.model.table}.${cur_field.name}`;
        var val = {
            query: column.query,
            alias: column.alias,
            column: column.column,
            raw_column: rawCol,
            monetaryInBase: (innerCol && innerCol !== rawCol) ? innerCol : false,
            value: mode ? `${mode}(${cur_field.label})` : cur_field.label,
            original_value: cur_field.label,
            id: false,
            type,
            field_type: cur_field.field_type
        }
        if (mode) {
            val.AGG = mode
        }
        if (!this.query_data[type].filter(item => item.query == val.query).length) {
            this.query_data[type].push(val)
        }
    }

    async onRelationalFieldDropped(ev) {
        const { type, field, axis } = ev.detail;
        if (type === 'dimension' && axis) {
            this.env.bus.trigger("CY:UPDATE_QUERY", { type: 'dimension_axis', data: axis });
        }
        const model = await this.orm.searchRead('ir.model', [['model', '=', field.relation]], ['id', 'name', 'model']);
        if (!model.length) {
            return;
        }
        this.dialog.add(FieldTraversalDialog, {
            title: `Select field from ${field.label}`,
            model_id: model[0].id,
            base_label: field.label,
            targetType: type,
            onConfirm: (selection) => this._applyRelationalSelection(field, selection, type, axis),
        });
    }

    /**
     * Apply a relational field selection to an axis: add the join(s), build the
     * column, and push the axis entry. Extracted from the FieldTraversalDialog
     * onConfirm so both the manual wizard and programmatic callers (e.g. AI
     * chart-apply) go through the exact same, tested path.
     *
     * @param {Object} field     the base (many2one) field { column, label }
     * @param {Object} selection { field: selectedSubField, rootModel, path }
     * @param {String} type      axis type ('dimension' | 'measure' | ...)
     * @param {String|false} axis  'x' | 'y' | false
     */
    async _applyRelationalSelection(field, selection, type, axis) {
        const selectedField = selection.field;
        const rootModel = selection.rootModel;
        const path = selection.path || [];

        const mainFieldColumn = field.column;
        const [mainTable, mainFieldName] = mainFieldColumn.split('.');

        const joinSteps = [];
        if (rootModel && rootModel.table) {
            joinSteps.push({
                fromTable: mainTable,
                fieldName: mainFieldName,
                toTable: rootModel.table,
                toModelName: rootModel.name,
                toModelId: rootModel.id,
            });
        }
        path.forEach(step => {
            joinSteps.push({
                fromTable: step.fromTable,
                fieldName: step.fieldName,
                toTable: step.toTable,
                toModelName: step.toModelName,
                toModelId: step.toModelId,
            });
        });

        for (const step of joinSteps) {
            const joinStr = `JOIN ${step.toTable} ON ${step.toTable}.id = ${step.fromTable}.${step.fieldName}`;
            const existingModel = this.state.models.find(m => m.table === step.toTable);
            if (existingModel) {
                if (existingModel.linked_by?.join && this._normalizeJoin(existingModel.linked_by.join) !== this._normalizeJoin(joinStr)) {
                    this.showMessage(`"${existingModel.name}" is already linked via a different path.`, "warning");
                }
                continue;
            }
            await this.setModelFromTable({
                name: step.toModelName,
                model: step.toTable,
                join: joinStr,
                linked: true,
                field: step.fieldName,
                model_id: step.toModelId,
            });
        }

        const relModelTable = selectedField.table;
        const column = `${relModelTable}.${selectedField.name}`;
        const alias = column.replace('.', '_');
        const { query, monetaryInBase } = this._buildFieldQuery(column, alias, selectedField);

        const labelParts = [
            field.label,
            ...path.map(p => p.fieldLabel),
            selectedField.label,
        ].filter(Boolean);
        const val = {
            type,
            value: labelParts.join(" > "),
            alias,
            query,
            column,
            field_type: selectedField.type,
            is_json: selectedField.is_json || false,
            monetaryInBase,
            relational: {
                table: relModelTable,
                field: selectedField.name,
            }
        };

        if (!this.query_data[type].filter(item => item.query == val.query).length) {
            this.query_data[type].push(val);
        }
        this.env.bus.trigger("CY:SYNC_CHILDREN", {
            targetType: type,
            children: this.query_data[type],
            axis: axis || false,
        });
        this.genQuery();
    }

    _normalizeJoin(joinStr) {
        return (joinStr || "").replace(/\s+/g, ' ').trim().toLowerCase();
    }

    _buildFieldQuery(column, alias, field) {
        const companyId = this.company.currentCompany?.id;
        let query = `${column} AS ${alias}`;
        let monetaryInBase = false;
        if (field.is_json) {
            query = `${column} ->> 'en_US' AS ${alias}`;
        } else if (field.type === "monetary") {
            const modelName = column.split(".")[0];
            const currency_rate = `COALESCE((
                    SELECT rate FROM res_currency_rate
                    WHERE currency_id = ${modelName}.currency_id
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
        }
        return { query, monetaryInBase };
    }

    async setModelFromTable(join) {
        await this.orm.call('ir.model', 'get_model_from_table', [join.model]).then(model => {
            if (!this.state.models.map(mdl => mdl.id).includes(model.id)) {
                join.model = model.model
                join.name = model.name
                model.linked_by = join
                model.linked_by.string = join.linked ? this.getLinkString(join, model) : false
                Object.values(model.fields).forEach(field => {
                    field.model = model
                })
                this.state.models.push(model)
                this.setFields()
            }
        })
    }

    onUpdate(data) {
        this.state.kpiValue = data
        return this.state.kpiValue
    }

    onClickDashboardPage(dashboard) {
        const selectedDashboard = this.sheet.el.querySelectorAll(dashboard)[0]
        this.sheet.el.querySelectorAll('.dashboard-note').forEach(div => {
            if (div !== selectedDashboard) {
                div.classList.remove('show');
            }
        });
        selectedDashboard.classList.add('show');
    }

    getLinkString(join, model) {
        if (!join.join) return false
        var link = join.join.replace(/join/ig, ' Linked by ')
        return link
    }

    onClickDeleteFilter(index, filterId) {
        this.query_data.where = this.query_data.where.filter((item, idx) => idx !== index);
        this.updateWhere(this.query_data.where)
        const isInteger = typeof filterId === 'number' && isFinite(filterId) && Math.floor(filterId) === filterId;
        if (filterId && isInteger) {
            this.orm.unlink("dashboard.sheet.filter", [filterId]);
        }
    }

    onClickEditFilter(where) {
        this.dialog.add(SheetFilterDomain, {
            where,
            isEdit: true,
            confirm: this.addWhere.bind(this),
            models: this.state.models,
            fields: this.state.fields
        })
    }

    goBack() {
        this.state.savingMode = false
        this.state.loading = true
        browser.history.go(-1)
        if (this.isNewSheet) {
            this.env.bus.trigger("PN:RLD")
        }
    }

    async changeRecord(event) {
        if (!this.id) {
            return
        }
        var index = this.navState.allRecords.findIndex(item => item === this.id)
        index = event === "fwd" ? index + 1 : index - 1
        if (index > this.navState.allRecords.length - 1) {
            index = 0
        } else if (index < 0) {
            index = this.navState.allRecords.length - 1
        }
        this.id = this.navState.allRecords[index]
        this.state.id = this.navState.allRecords[index]
        this.saveManually(this.id)
        this.navState.recordValue = index + 1
    }

    /**
     * Returns true when any active preset measure has no aggregate function
     * configured for ANY of its variables (i.e. all vars use scalar expressions).
     * In that case GROUP BY would produce invalid SQL, so we hide the drop zone.
     */
    get presetBlocksGroupBy() {
        const presetMeasures = this.query_data.measure.filter(m => m.isPreset);
        if (!presetMeasures.length) return false;

        return presetMeasures.some(m => {
            // Row-level presets never produce aggregates
            if (m.calculation_type === 'row') return true;

            // Aggregate presets: check if at least one variable has an agg function.
            // If NONE have one, then the formula is still non-aggregated.
            let configs;
            try {
                configs = typeof m.variable_configs === 'string'
                    ? JSON.parse(m.variable_configs)
                    : (m.variable_configs || []);
            } catch (e) {
                configs = [];
            }
            // If there are no variable configs at all, we cannot guarantee aggregation
            if (!configs.length) return true;
            const hasAnyAggregate = configs.some(vc => vc.aggregate && vc.aggregate.trim());
            return !hasAnyAggregate;
        });
    }

    get axis() {
        let x, y, group;
        switch (this.state.selectedType[1].toLowerCase()) {
            case "gauge":
            case "kpi":
                const dimensionAxis = this.query_data.dimension_axis
                x = dimensionAxis === 'y';
                y = !x;
                group = false;
                break;
            case "map":
                x = true;
                y = true;
                group = false;
                break;
            default:
                x = true;
                y = true;
                group = true;
        }
        return {
            x,
            y,
            group
        };
    }

    async onClickDiscard() {
        if (this.id) {
            // Revert to the saved DB state IN PLACE. soft_reload re-dispatches the
            // action, which loses the fullscreen chrome and brings the top navbar
            // back. Re-fetching reverts every config field and resets the dirty
            // baseline (via updateData → _markSaved) without leaving fullscreen.
            this.unlinkList = { axis: [], tables: [], where: [], configs: [] }
            await this.updateSheet()
        } else {
            // New, never-saved sheet: nothing in the DB to revert to.
            this.action.doAction("soft_reload")
        }
    }

    onClickNew() {
        // Cover the transition while the fresh sheet action is dispatched.
        this.state.savingMode = false
        this.state.loading = true
        this.removeManually()
        return this.action.doAction("cyllo_analytics.cyllo_dashboard_sheet", {
            target: "fullscreen",
        })
    }

    static props = { ...standardActionServiceProps }
}

// Define the template for the CylloSheet component
CylloSheet.template = "CylloSheet"
CylloSheet.components = {
    FieldList,
    ModelViewer,
    DropZone,
    SQLEditor,
    GraphTile,
    Many2XAutocomplete,
    FieldAutoComplete,
    FieldAutoCompleteGlobal,
    KpiSheet,
    Table,
    Number,
    FieldTraversalDialog,
}
registry.category("actions").add("cy_analytic_sheet", CylloSheet);
