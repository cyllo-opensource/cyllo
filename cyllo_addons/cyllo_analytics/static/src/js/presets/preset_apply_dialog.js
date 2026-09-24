/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { SheetFilterDomain } from "@cyllo_analytics/js/sheet_filter/sheetFilterDomain";
import { generateSqlAlias } from "@cyllo_analytics/js/utils";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

const { Component, useState, onWillStart, useRef, useEffect } = owl;

const AGG_OPTIONS = ['', 'SUM', 'COUNT', 'AVG', 'MIN', 'MAX'];

export class PresetApplyDialog extends Component {
    static template = "PresetApplyDialog";
    static components = { Dialog, AutoComplete };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.company = useService("company");


        const dedupeByColumn = (arr) => {
            const seen = new Set();
            return arr.filter(f => {
                if (seen.has(f.column)) return false;
                seen.add(f.column);
                return true;
            });
        };
        this.measureFields = dedupeByColumn(
            (this.props.fields || []).filter(
                f => ['float', 'integer', 'monetary'].includes(f.field_type) && !f.isPreset
            )
        );
        this.allFields = dedupeByColumn((this.props.fields || []).filter(f => !f.isPreset));

        const edit = this.props.editMeasure;

        this.state = useState({
            viewMode: edit ? 'apply' : (this.props.initialMode || 'apply'),
            presets: [],
            selectedPresetId: edit ? (edit.preset_id || 'custom') : '',
            selectedPresetLabel: '',
            rawFormula: edit ? (edit.rawFormula || '') : '',
            variables: [],
            variableConfigs: {},   // { varName: { column, aggregate, filter_domain, filter_domain_py, filter_name } }
            fieldName: edit ? (edit.value || edit.original_label || '') : '',
            calculationType: edit ? (edit.calculation_type || 'aggregate') : 'aggregate',
            showFormula: true,
            error: '',
            missingAggs: [],
        });

        this.errorRef = useRef("errorRef");

        useEffect(
            () => {
                if (this.state.error && this.errorRef.el) {
                    this.errorRef.el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            },
            () => [this.state.error]
        );

        onWillStart(async () => {
            const presets = await this.orm.call(
                "calculation.preset", "get_all_presets", [this.props.sheet_id || false]
            );
            this.state.presets = presets;

            if (edit) {
                this._loadEditMeasure(edit);
                if (this.state.selectedPresetId === 'custom') {
                    this.state.selectedPresetLabel = '-- Custom / Edited Formula --';
                } else if (this.state.selectedPresetId) {
                    const preset = this.state.presets.find(p => String(p.id) === String(this.state.selectedPresetId));
                    if (preset) {
                        this.state.selectedPresetLabel = preset.name;
                    }
                }
            }
        });
    }

    // ── Constants exposed to template ────────────────────────────────────
    get aggOptions() { return AGG_OPTIONS; }
    get measureFieldOptions() { return this.measureFields; }

    get presetSources() {
        return [
            {
                options: (searchValue) => {
                    const search = (searchValue || "").toLowerCase();
                    const options = this.state.presets
                        .filter((p) => p.name.toLowerCase().includes(search))
                        .map((p) => ({
                            label: p.name,
                            value: String(p.id),
                            isSelected: this.state.selectedPresetId === String(p.id),
                        }));

                    if (this.state.selectedPresetId === 'custom' || this.props.editMeasure) {
                        if ("-- custom / edited formula --".includes(search)) {
                            options.unshift({
                                label: 'Custom/Edited Formula',
                                value: 'custom',
                                isSelected: this.state.selectedPresetId === 'custom',
                            });
                        }
                    }
                    return options;
                },
                optionTemplate: "PresetApplyDialog.AutoCompleteOption",
            },
        ];
    }

    // ── Load from edit measure ───────────────────────────────────────────
    _loadEditMeasure(edit) {
        const formula = edit.rawFormula || '';
        this.state.rawFormula = formula;
        this.state.calculationType = edit.calculation_type || 'aggregate';
        this._parseVariables(formula);

        // Restore variable configs if available
        let savedConfigs = {};
        if (edit.variable_configs) {
            try {
                const parsed = typeof edit.variable_configs === 'string'
                    ? JSON.parse(edit.variable_configs) : edit.variable_configs;
                if (Array.isArray(parsed)) {
                    parsed.forEach(vc => { savedConfigs[vc.name] = vc; });
                }
            } catch (_) { /* ignore parse errors */ }
        }

        // Also restore from legacy variables if no variable_configs
        if (!Object.keys(savedConfigs).length && edit.variables) {
            try {
                const vars = typeof edit.variables === 'string'
                    ? JSON.parse(edit.variables) : edit.variables;
                if (Array.isArray(vars)) {
                    vars.forEach(v => {
                        savedConfigs[v.name] = {
                            name: v.name,
                            column: v.selection || '',
                            aggregate: '',
                            filter_domain: '',
                            filter_domain_py: [],
                            filter_name: '',
                        };
                    });
                }
            } catch (_) { /* ignore */ }
        }

        // Merge saved configs into state
        for (const v of this.state.variables) {
            if (savedConfigs[v.name]) {
                const config = { ...this._emptyVarConfig(v.name), ...savedConfigs[v.name] };
                // Ensure we use the clean field name for the dropdown selector
                if (config.original_column) {
                    config.column = config.original_column;
                }
                this.state.variableConfigs[v.name] = config;
            }
        }
    }

    // ── Parse variables from formula ─────────────────────────────────────
    _parseVariables(formula) {
        const matches = formula.match(/\{([^}]+)\}/g) || [];
        const seen = new Set();
        const vars = [];
        for (const m of matches) {
            const name = m.slice(1, -1);
            if (!seen.has(name)) {
                seen.add(name);
                vars.push({ name, label: name });
            }
        }
        this.state.variables = vars;
        for (const v of vars) {
            if (!this.state.variableConfigs[v.name]) {
                this.state.variableConfigs[v.name] = this._emptyVarConfig(v.name);
            }
        }
    }

    _emptyVarConfig(name) {
        return {
            name,
            column: '',
            aggregate: '',
            filter_domain: '',         // SQL WHERE string
            filter_domain_py: [],      // structured domain expressions
            filter_name: '',           // display name for the filter
        };
    }

    // ── Event handlers ──────────────────────────────────────────────────
    onPresetSelect(selected) {
        const val = selected.value;
        const label = selected.label;
        this.state.selectedPresetId = val;
        this.state.selectedPresetLabel = label;
        this._applyPreset(val);
    }

    _applyPreset(val) {
        this.state.error = '';

        if (val === 'custom' || !val) {
            this.state.rawFormula = '';
            this.state.variables = [];
            this.state.variableConfigs = {};
            this.state.calculationType = 'aggregate';
            return;
        }

        const preset = this.state.presets.find(p => String(p.id) === val);
        if (preset) {
            this.state.rawFormula = preset.formula || '';
            this.state.calculationType = preset.calculation_type || 'aggregate';
            this._parseVariables(preset.formula || '');

            try {
                const pVars = typeof preset.variables === 'string'
                    ? JSON.parse(preset.variables) : (preset.variables || []);
                if (Array.isArray(pVars)) {
                    this.state.variables = pVars.map(pv => ({
                        name: pv.name,
                        label: pv.label || pv.name,
                    }));
                }
            } catch (_) { /* ignore */ }
        }
    }

    onFormulaChange() {
        this._parseVariables(this.state.rawFormula);
    }

    switchToCreate() {
        this.state.viewMode = 'create';
        this.state.rawFormula = '';
        this.state.variables = [];
        this.state.variableConfigs = {};
        this.state.fieldName = '';
        this.state.calculationType = 'aggregate';
        this.state.selectedPresetId = '';
        this.state.selectedPresetLabel = '';
        this.state.error = '';
    }

    switchToApply() {
        this.state.viewMode = 'apply';
        this.state.rawFormula = '';
        this.state.variables = [];
        this.state.variableConfigs = {};
        this.state.fieldName = '';
        this.state.calculationType = 'aggregate';
        this.state.selectedPresetId = '';
        this.state.selectedPresetLabel = '';
        this.state.error = '';
    }

    // ── Variable config setters ──────────────────────────────────────────
    setVarColumn(varName, ev) {
        this.state.variableConfigs[varName].column = ev.target.value;
    }

    setVarAggregate(varName, agg) {
        this.state.variableConfigs[varName].aggregate = agg;
        if (agg && this.state.missingAggs) {
            this.state.missingAggs = this.state.missingAggs.filter(name => name !== varName);
        }
    }

    getVarLabel(varName) {
        const col = this.state.variableConfigs[varName]?.column;
        if (!col) return '';
        const field = this.measureFields.find(f => f.column === col);
        return field ? field.label : '';
    }

    variableSources(varName) {
        return [
            {
                options: (searchValue) => {
                    const search = (searchValue || "").toLowerCase();
                    return this.measureFields
                        .filter((f) => f.label.toLowerCase().includes(search))
                        .map((f) => ({
                            label: f.label,
                            value: f.column,
                            isSelected: this.state.variableConfigs[varName]?.column === f.column,
                        }));
                },
                optionTemplate: "PresetApplyDialog.AutoCompleteOption",
            },
        ];
    }

    onVarSelect(varName, selected) {
        this.state.variableConfigs[varName].column = selected.value;
    }

    // ── Open the sheet filter dialog for a variable ──────────────────────
    openFilterDialog(varName) {
        const cfg = this.state.variableConfigs[varName];
        const where = {
            name: cfg.filter_name || `Filter for ${varName}`,
            domain: cfg.filter_domain || '',
            domain_py_expression: cfg.filter_domain_py || [],
            active: true,
        };

        this.dialogService.add(SheetFilterDomain, {
            confirm: (data) => {
                this.state.variableConfigs[varName].filter_domain = data.domain || '';
                this.state.variableConfigs[varName].filter_domain_py = data.domain_py_expression || [];
                this.state.variableConfigs[varName].filter_name = data.name || '';
            },
            models: this.props.models || [],
            fields: this.props.fields || [],
            where,
            isEdit: !!cfg.filter_domain,
        });
    }

    clearFilter(varName) {
        this.state.variableConfigs[varName].filter_domain = '';
        this.state.variableConfigs[varName].filter_domain_py = [];
        this.state.variableConfigs[varName].filter_name = '';
    }

    // ── Apply preset ────────────────────────────────────────────────────
    async onApply() {
        this.state.missingAggs = [];
        const { rawFormula, fieldName, calculationType, variables, variableConfigs } = this.state;

        if (!fieldName) {
            this.state.error = 'Please provide a field name.';
            return;
        }
        const sanitized = fieldName
            .toLowerCase()
            .replace(/[^a-z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_+|_+$/g, '');
        if (!sanitized || /^[0-9]/.test(sanitized)) {
            this.state.error = 'Field name must contain letters and cannot be only numbers or symbols.';
            return;
        }
        if (!rawFormula) {
            this.state.error = 'No formula defined.';
            return;
        }

        for (const v of variables) {
            const cfg = variableConfigs[v.name];
            if (!cfg || !cfg.column) {
                this.state.error = `Please select a field for variable "{${v.name}}".`;
                return;
            }
        }

        if (calculationType === 'aggregate') {
            const hasAggregated = variables.some(v => variableConfigs[v.name]?.aggregate);
            if (hasAggregated) {
                const missingAggs = variables.filter(v => !variableConfigs[v.name]?.aggregate);
                if (missingAggs.length > 0) {
                    this.state.missingAggs = missingAggs.map(v => v.name);
                    const names = missingAggs.map(v => `{${v.name}}`).join(', ');
                    this.state.error = `When using aggregated functions, all variables must have an aggregation function. Variable(s) ${names} are missing one.`;
                    return;
                }
            }
        }

        try {
            const companyId = this.company.currentCompany?.id;
            const alias = generateSqlAlias(fieldName, true);
            let hasMonetary = false;

            const varConfigList = variables.map(v => {
                const cfg = variableConfigs[v.name];
                const field = this.props.fields.find(f => f.column === cfg.column);
                let colExpr = cfg.column;

                if (field?.field_type === 'monetary') {
                    hasMonetary = true;
                    const modelName = cfg.column.split(".")[0];
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
                    colExpr = `ROUND(${cfg.column} / ${currency_rate}, 2)`;
                }

                return {
                    name: v.name,
                    column: colExpr,
                    aggregate: cfg.aggregate,
                    filter_domain: cfg.filter_domain,
                    filter_domain_py: cfg.filter_domain_py,
                    filter_name: cfg.filter_name,
                    original_column: cfg.column, // Keep track of the actual column
                };
            });

            let columnExpr;

            if (varConfigList.length) {
                const tables = this._extractTables(varConfigList);
                columnExpr = await this.orm.call(
                    "calculation.preset",
                    "translate_to_sql_advanced",
                    [rawFormula, varConfigList, tables, calculationType]
                );
            } else {
                const bindings = {};
                for (const v of variables) {
                    bindings[v.name] = variableConfigs[v.name].column;
                }
                columnExpr = await this.orm.call(
                    "calculation.preset",
                    "translate_to_sql",
                    [rawFormula, bindings]
                );
            }

            const presetId = this.state.selectedPresetId && this.state.selectedPresetId !== 'custom'
                ? parseInt(this.state.selectedPresetId) : false;

            const measureObj = {
                type: 'measure',
                isPreset: true,
                rawFormula,
                calculation_type: calculationType,
                aggregate_func: false,
                variables: JSON.stringify(variables.map(v => ({
                    ...v,
                    selection: variableConfigs[v.name].column,
                }))),
                variable_configs: JSON.stringify(varConfigList),
                value: fieldName,
                original_label: fieldName,
                alias,
                column: columnExpr,
                query: `${columnExpr} AS ${alias}`,
                preset_id: presetId,
                monetaryInBase: hasMonetary ? columnExpr : false,
            };

            if (this.props.editMeasure?.id || this.props.editMeasure?.alias) {
                measureObj.id = this.props.editMeasure.id;
                measureObj.alias = this.props.editMeasure.alias || alias;
                measureObj.oldAlias = this.props.editMeasure.alias;
                measureObj.query = `${columnExpr} AS ${measureObj.alias}`;
            }

            this.props.onApply(measureObj);
            this.props.close();
        } catch (e) {
            this.state.error = e.data?.message || e.message || 'An error occurred.';
        }
    }

    _extractTables(varConfigList) {
        const tables = new Set();
        for (const vc of varConfigList) {
            if (vc.column && vc.column.includes('.')) {
                tables.add(vc.column.split('.')[0]);
            }
        }
        return Array.from(tables).join(', ');
    }

    // ── Save new template ───────────────────────────────────────────────
    async onSaveAsTemplate() {
        const { rawFormula, fieldName, calculationType } = this.state;

        if (!fieldName) {
            this.state.error = 'Please provide a template name.';
            return;
        }
        if (/^\d/.test(fieldName)) {
            this.state.error = 'Template name cannot start with or be a numeric value.';
            return;
        }
        if (!rawFormula) {
            this.state.error = 'Formula is required.';
            return;
        }

        if (calculationType === 'aggregate') {
            const aggPattern = /\b(SUM|COUNT|AVG|MIN|MAX)\s*\(/i;
            if (aggPattern.test(rawFormula)) {
                this.state.error = 'For Aggregated type, do not write aggregate functions (SUM, COUNT, etc.) in the formula. Use only placeholders like {variable}. You will select the aggregate function per-variable during application.';
                return;
            }
        }

        try {
            const vars = this.state.variables.map(v => ({ name: v.name, label: v.label || v.name }));
            const savedName = fieldName;
            const savedPresetId = await this.orm.call("calculation.preset", "save_preset", [{
                name: fieldName,
                formula: rawFormula,
                variables: JSON.stringify(vars),
                calculation_type: calculationType,
                sheet_id: false,
            }]);

            this.state.presets = await this.orm.call(
                "calculation.preset", "get_all_presets", [this.props.sheet_id || false]
            );

            // Switch to apply mode with the newly saved preset auto-selected,
            // but clear fieldName so the template name doesn't default as the field name
            this.state.viewMode = 'apply';
            this.state.fieldName = '';
            this.state.error = '';
            const newPreset = this.state.presets.find(p => p.id === savedPresetId);
            if (newPreset) {
                this.state.selectedPresetId = String(newPreset.id);
                this.state.selectedPresetLabel = newPreset.name;
                this._applyPreset(String(newPreset.id));
            } else {
                this.state.selectedPresetId = '';
                this.state.selectedPresetLabel = '';
            }

            this.notification.add("Preset saved successfully!", { type: "success" });
            this.env.bus.trigger("CY:PRESET_SAVED");
        } catch (e) {
            this.state.error = e.data?.message || e.message || 'Failed to save preset.';
        }
    }

    onCancel() {
        this.props.close();
    }
}
