/** @odoo-module **/
const {useState, useRef, onWillUpdateProps, Component, onPatched, useEffect, onMounted} = owl;
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {FieldSelector} from "./subComponents/FieldSelector/fieldSelector";
import {ValueSelector} from "./subComponents/ValueSelector/valueSelector";
import {Select} from "@web/core/tree_editor/tree_editor_components";
import {
    getDefaultValue,
} from "@web/core/tree_editor/tree_editor_value_editors";
import {
    getVariableDefaultValue,
    OPERATORS,
    validateCondition,
    VARIABLE_OPERATORS
} from "../Assists/utils/utils";

export class ConditionComponent extends Component {
    setup() {
        this.state = useState({
            isValid: true,
        });
        this.env.bus.addEventListener("VALIDATE-CONDITION", this.validateCondition.bind(this))
        onPatched(() => {
            this.validateCondition();
        })
    }

    validateCondition() {
        const {condition} = this.props;
        this.state.isValid = validateCondition(condition);
        condition.isValid = this.state.isValid
    }

    updateCondition(key, value) {
        this.props.condition[key] = value;
    }

    handleUpdateFieldType = type => {
        this.props.condition.fieldType = type;
        this.props.condition.field = "";
        this.props.condition.operator = "=";
        this.props.condition.value = {value: "", fieldType: "static"}
    }

    handleUpdateValueFieldType = type => {
        if (type === "static") {
            if (this.props.condition.field.isVariable) {
                this.props.condition.value.value = getVariableDefaultValue(this.props.condition, this.props.variables);
            } else {
                this.props.condition.value.value = getDefaultValue(this.props.condition.field.info.fieldDef, this.props.condition.operator)
            }
        } else {
            this.props.condition.value.value = ""
        }
        this.props.condition.value.fieldType = type;
    }

    updateConditionField(field, value) {
        this.props.condition["fieldType"] = value.isVariable ? "variable" : "record";
        if (value.isVariable) {
            this.props.condition["value"] = {
                value: getVariableDefaultValue(this.props.condition, this.props.variables), fieldType: "static",
            };
        } else if (!value.isVariable) {
            this.props.condition["value"] = {
                value: getDefaultValue(value.info.fieldDef, this.props.condition.operator), fieldType: "static",
            };
        }
        this.props.condition.field = value
    }

    updateConditionValue(key, value) {
        this.props.condition.value = {...value}
    }

    updateConditionOperator(key, value) {
        const def = this.props.condition?.fieldType === "record" ? this.props.condition.field.info?.fieldDef : false
        this.props.condition["value"] = def ? {value: getDefaultValue(def, value), fieldType: "static"} : {
            value: false,
            fieldType: "static"
        };
        this.props.condition.operator = value
    }

    getOperatorEditorInfo() {
        const {condition, variables} = this.props;
        if (condition.fieldType === "variable") {
            return this.getVariableOperatorEditorInfo(condition, variables);
        } else if (condition.fieldType === "record") {
            return this.getRecordOperatorEditorInfo(condition);
        }
        return null;
    }

    getVariableOperatorEditorInfo(condition, variables) {
        const variable = variables.find(v => v.id === condition.field.selectedVariable);
        const options = variable ? this.operatorsList(variable) : this.getDefaultOperators();
        return this.createSelectComponent(options);
    }

    getRecordOperatorEditorInfo(condition) {
        const fieldDef = condition.field?.info?.fieldDef;
        return this.createSelectComponent(fieldDef ? OPERATORS[fieldDef.type] : this.getDefaultOperators());
    }

    createSelectComponent(options) {
        return {
            component: Select,
            extractProps: ({value, update}) => ({
                value,
                update,
                options: options || this.getDefaultOperators(),
            }),
        };
    }

    getDefaultOperators() {
        return [
            ["=", "equals"],
            ["!=", "not equals"],
            [">", "greater than"],
            ["<", "less than"],
            [">=", "greater than or equal to"],
            ["<=", "less than or equal to"],
            ["in", "in"],
            ["not in", "not in"]
        ];
    }
    operatorsList(variable) {
        return VARIABLE_OPERATORS[variable.variable_type] || [];
    }
}

ConditionComponent.template = 'ConditionComponent';
ConditionComponent.components = {FieldSelector, ValueSelector};
ConditionComponent.props = ["*"]


class GroupComponent extends owl.Component {
    setup() {
        this.fields = this.props.fields;
        this.operators = this.props.operators;
    }

    addCondition() {
        this.props.addCondition(this.props.groupIndex);
    }

    setComplexCondition() {
        this.props.setComplexCondition(this.props.groupIndex);
    }

    updateCondition(condition, key, value) {
        condition[key] = value;
    }

    removeCondition() {}
}

GroupComponent.template = 'GroupComponent';
GroupComponent.props = ["*"]
GroupComponent.components = {ConditionComponent};

export class ConditionNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.labelInput = useRef("labelInput")
        this.state = useState({
            groups: [{
                conditions: [{
                    type: 'simple',
                    fieldType: 'variable',
                    field: '',
                    operator: '=',
                    value: {value: "", fieldType: "static"},
                    logicalOperator: 'and'
                }],
                groupOperator: 'and'
            }],
            // For cron mode: the ID of the chosen search-variable (recordset)
            cronVariableId: null,
        });

        onMounted(() => {
            this.labelInput.el.focus()
        })
    }

    /** Returns true when the workflow is driven by a time/cron trigger. */
    get isCronMode() {
        return this.props.triggerType === 'time';
    }

    /**
     * Returns recordset/record variables available for cron-mode conditioning.
     * Excludes internally generated `_complement` variables, which are managed
     * automatically and should not be user-selectable in the condition picker.
     */
    get recordsetVariables() {
        return (this.props.variables || []).filter(
            v => (v.variable_type === 'recordset' || v.variable_type === 'record')
                && !v.variable_name?.endsWith('_complement')
        );
    }

    /** Returns the full variable object for the currently selected cron variable. */
    get selectedCronVariable() {
        if (!this.state.cronVariableId) return null;
        return (this.props.variables || []).find(v => v.id === this.state.cronVariableId) || null;
    }

    selectCronVariable(variableId) {
        this.state.cronVariableId = variableId || null;
    }

    async fetchData() {
        await super.fetchData();
        if (this.fieldState.condition_tree_value) {
            const saved = this.fieldState.condition_tree_value;
            if (saved && saved.cronMode) {
                // Restore the previously saved cron variable selection.
                this.state.cronVariableId = saved.variableId || null;
            } else if (!saved?.cronMode) {
                // Normal mode: restore condition groups.
                this.state.groups = saved;
            }
        }
        // Auto-select the first available recordset variable when opening a
        // fresh cron-mode condition that has no prior selection.
        if (this.isCronMode && !this.state.cronVariableId) {
            const first = this.recordsetVariables[0];
            if (first) this.state.cronVariableId = first.id;
        }
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(label) {
        this.fieldState.label = label
        const nodeId = this.props.id
        if (this.labelInput.el.classList.contains('invalid')) this.labelInput.el.classList.remove('invalid')
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    addGroup() {
        this.state.groups.push({
            conditions: [{
                type: 'simple',
                fieldType: 'variable',
                field: '',
                operator: '=',
                value: {value: "", fieldType: "static"},
                logicalOperator: 'and'
            }],
            groupOperator: 'and'
        });
    }

    removeGroup(groupIndex) {
        this.state.groups.splice(groupIndex, 1);
    }

    addCondition(groupIndex) {
        const lastCondition = this.state.groups[groupIndex].conditions[this.state.groups[groupIndex].conditions.length - 1];
        this.state.groups[groupIndex].conditions.push({
            type: 'simple',
            fieldType: 'variable',
            field: '',
            operator: '=',
            value: {value: "", fieldType: "static"},
            logicalOperator: lastCondition ? lastCondition.logicalOperator : 'and'
        });
    }

    removeCondition(groupIndex, conditionIndex) {
        this.state.groups[groupIndex].conditions.splice(conditionIndex, 1);
    }

    updateGroupOperator(groupIndex, value) {
        this.state.groups[groupIndex].groupOperator = value;
    }

    setComplexCondition(groupIndex) {
        const lastCondition = this.state.groups[groupIndex].conditions[this.state.groups[groupIndex].conditions.length - 1];
        this.state.groups[groupIndex].conditions.push({
            type: 'complex',
            expression: '',
            logicalOperator: lastCondition ? lastCondition.logicalOperator : 'and'
        });
    }

    get pythonCode() {
        let pythonCode = this.generatePythonCode()
        let imports = new Set();
        if (pythonCode.includes('re.match')) {
            imports.add('import re');
        }
        if (pythonCode.includes('datetime')) {
            imports.add('from datetime import datetime');
        }
        if (imports.size > 0) {
            pythonCode = Array.from(imports).join('\n') + '\n\n' + pythonCode;
        }
        return pythonCode;
    }

    generatePythonCode(onConfirm = false) {
        // Cron mode: the condition is simply "if <recordset>:" — the complement
        // block is appended separately by the code-generation engine.
        if (this.isCronMode) {
            const variable = this.selectedCronVariable;
            if (!variable) return '';
            return `if ${variable.variable_name}:`;
        }

        // Normal mode: build the full condition expression from the group tree.
        const generateCondition = (cond) => {
            if (cond.type === 'complex') {
                return cond.expression || '';
            } else if (cond.field && cond.operator) {
                let fieldType, leftField, rightField;
                if (cond.fieldType === "variable") {
                    const variable = this.variables.find(item => item.id === cond.field.selectedVariable);
                    if (!variable) return "invalid";
                    if (cond.field.selectedVariable && onConfirm) {
                        this.updateUsedVariables(cond.field.selectedVariable);
                    }
                    fieldType = variable.variable_type;
                    leftField = variable.variable_name;  // Use the variable name
                } else if (cond.fieldType === "record") {
                    const record = this.props.variables.find(item => item.id === cond.field.record);
                    if (cond.field.record && onConfirm) {
                        this.updateUsedVariables(cond.field.record);
                    }
                    fieldType = cond.field.info.fieldDef.type;
                    leftField = record.variable_name + "." + cond.field.path;  // Assume we're working with a 'record' object

                } else {
                    // Handle unknown fieldType
                    return '';
                }

                if (cond.value.fieldType === "static") {
                    if (["integer", "float", "monetary", "number"].includes(fieldType)) {
                        rightField = cond.value.value === "" ? "0" : Number(cond.value.value);
                    } else if (fieldType === "boolean") {
                        rightField = cond.value.value ? "True" : "False";
                    } else {
                    rightField = JSON.stringify(cond.value.value);
                    }
                } else if (cond.value.fieldType === "variable") {
                    if (cond.value?.value && onConfirm) {
                        this.updateUsedVariables(cond.value.value.selectedVariable);
                    }
                    rightField = cond.value.value.pathValue;
                } else if (cond.value.fieldType === "record") {
                    if (cond.value?.value && onConfirm) {
                        this.updateUsedVariables(cond.value.value.record);
                    }
                    const variableValue = this.variables.find(item => item.id === cond.value.value.record);
                    rightField = variableValue && variableValue.variable_name + "." + cond.value.value.pathValue;
                } else return ""
                if (cond.operator === 'in' && cond.value.value && cond.value.fieldType === 'static' && !["string"].includes(fieldType)) {
                    // Check if it's a Proxy object or an array-like object
                    if (Array.isArray(cond.value.value) || 'length' in cond.value.value) {
                        // Convert to array and join the values
                        rightField = `[${Array.from(cond.value.value).join(', ')}]`;
                    } else {
                        // If it's not array-like, fallback to default handling
                        rightField = JSON.stringify(cond.value);
                    }
                }
                switch (fieldType) {
                    case 'string':
                    case 'char':
                    case 'text':
                    case 'html':
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${rightField}`;
                            case '!=':
                                return `${leftField} != ${rightField}`;
                            case 'ilike':
                                return `${leftField} and ${rightField} and ${leftField}.lower().find(${rightField}.lower()) != -1`;
                            case 'not ilike':
                                return `not (${leftField} and ${rightField} and ${leftField}.lower().find(${rightField}.lower()) != -1)`;
                            case 'like':
                                return `${leftField} and ${rightField} and ${leftField}.find(${rightField}) != -1`;
                            case 'not like':
                                return `not (${leftField} and ${rightField} and ${leftField}.find(${rightField}) != -1)`;
                            case 'in':
                                return `${leftField} in ${rightField}`;
                            case 'not in':
                                return `${leftField} not in ${rightField}`;
                            case '=like':
                                return `${leftField} and ${rightField} and re.match(${rightField}, ${leftField})`;
                            case '=ilike':
                                return `${leftField} and ${rightField} and re.match(${rightField}, ${leftField}, re.IGNORECASE)`;
                            case 'set':
                                return `${leftField} and ${leftField}.strip()`;
                            case 'not_set':
                                return `not ${leftField} or not ${leftField}.strip()`;
                            default:
                                return '';
                        }
                    case 'number':
                    case 'integer':
                    case 'float':
                    case 'monetary':
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${rightField}`;
                            case '!=':
                                return `${leftField} != ${rightField}`;
                            case '>':
                                return `${leftField} > ${rightField}`;
                            case '>=':
                                return `${leftField} >= ${rightField}`;
                            case '<':
                                return `${leftField} < ${rightField}`;
                            case '<=':
                                return `${leftField} <= ${rightField}`;
                            case 'in':
                                return `${leftField} in ${rightField}`;
                            case 'not in':
                                return `${leftField} not in ${rightField}`;
                            case 'between':
                                return `${rightField}[0] <= ${leftField} <= ${rightField}[1]`;
                            case 'set':
                                return `${leftField} is not None`;
                            case 'not_set':
                                return `${leftField} is None`;
                            default:
                                return '';
                        }
                    case 'boolean':
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${rightField === "true" ? 'True' : 'False'}`;
                            case '!=':
                                return `${leftField} != ${rightField === "true" ? 'True' : 'False'}`;
                            default:
                                return '';
                        }
                    case 'date': {
                        // Only parse static strings with strptime(); variable/record
                        // right-hand sides are already Python date objects.
                        const isStaticDate = cond.value.fieldType === 'static';
                        const parsedDateRight = isStaticDate
                            ? `datetime.strptime(${rightField}, "%Y-%m-%d").date()`
                            : rightField;
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${parsedDateRight}`;
                            case '!=':
                                return `${leftField} != ${parsedDateRight}`;
                            case '>':
                                return `${leftField} > ${parsedDateRight}`;
                            case '>=':
                                return `${leftField} >= ${parsedDateRight}`;
                            case '<':
                                return `${leftField} < ${parsedDateRight}`;
                            case '<=':
                                return `${leftField} <= ${parsedDateRight}`;
                            case 'between':
                                return isStaticDate
                                    ? `datetime.strptime(${rightField}[0], "%Y-%m-%d").date() <= ${leftField} <= datetime.strptime(${rightField}[1], "%Y-%m-%d").date()`
                                    : `${rightField}[0] <= ${leftField} <= ${rightField}[1]`;
                            case 'set':
                                return `${leftField} is not None`;
                            case 'not_set':
                                return `${leftField} is None`;
                            default:
                                return '';
                        }
                    }
                    case 'datetime': {
                        // Only parse static strings with strptime(); variable/record
                        // right-hand sides are already Python datetime objects.
                        const isStaticDatetime = cond.value.fieldType === 'static';
                        const parsedDatetimeRight = isStaticDatetime
                            ? `datetime.strptime(${rightField}, "%Y-%m-%d %H:%M:%S")`
                            : rightField;
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${parsedDatetimeRight}`;
                            case '!=':
                                return `${leftField} != ${parsedDatetimeRight}`;
                            case '>':
                                return `${leftField} > ${parsedDatetimeRight}`;
                            case '>=':
                                return `${leftField} >= ${parsedDatetimeRight}`;
                            case '<':
                                return `${leftField} < ${parsedDatetimeRight}`;
                            case '<=':
                                return `${leftField} <= ${parsedDatetimeRight}`;
                            case 'between':
                                return isStaticDatetime
                                    ? `datetime.strptime(${rightField}[0], "%Y-%m-%d %H:%M:%S") <= ${leftField} <= datetime.strptime(${rightField}[1], "%Y-%m-%d %H:%M:%S")`
                                    : `${rightField}[0] <= ${leftField} <= ${rightField}[1]`;
                            case 'set':
                                return `${leftField} is not None`;
                            case 'not_set':
                                return `${leftField} is None`;
                            default:
                                return '';
                        }
                    }
                    case 'record':
                    case 'many2one':
                        switch (cond.operator) {
                            case '=':
                                return `${leftField}.id == ${rightField}`;
                            case '!=':
                                return `${leftField}.id != ${rightField}`;
                            case 'in':
                                return `${leftField}.id in ${rightField}`;
                            case 'not in':
                                return `${leftField}.id not in ${rightField}`;
                            case 'set':
                                return `bool(${leftField})`;
                            case 'not_set':
                                return `not bool(${leftField})`;
                            default:
                                return '';
                        }
                    case 'recordset':
                    case 'one2many':
                    case 'many2many':
                        switch (cond.operator) {
                            case 'in':
                                return `any(r.id in ${rightField} for r in ${leftField})`;
                            case 'not in':
                                return `all(r.id not in ${rightField} for r in ${leftField})`;
                            case '=':
                                return `${leftField}.ids == ${rightField}`;
                            case '!=':
                                return `${leftField}.ids != ${rightField}`;
                            case 'set':
                                return `bool(${leftField})`;
                            case 'not_set':
                                return `not bool(${leftField})`;
                            default:
                                return '';
                        }
                    case 'selection':
                        switch (cond.operator) {
                            case '=':
                                return `${leftField} == ${rightField}`;
                            case '!=':
                                return `${leftField} != ${rightField}`;
                            case 'in':
                                return `${leftField} in ${rightField}`;
                            case 'not in':
                                return `${leftField} not in ${rightField}`;
                            case 'set':
                                return `${leftField} is not None`;
                            case 'not_set':
                                return `${leftField} is None`;
                            default:
                                return '';
                        }
                    default:
                        return '';
                }
            }
            return '';
        };

        const groupConditions = this.state.groups.map((group, index) => {
            const conditions = group.conditions.map((cond, condIndex) => {
                let conditionStr = generateCondition(cond);
                return condIndex > 0 ? `${cond.logicalOperator} (${conditionStr})` : conditionStr;
            }).filter(c => c !== '');
            let groupStr = conditions.length ? `(${conditions.join(' ')})` : '';
            if (index > 0) {
                groupStr = `${group.groupOperator} ${groupStr}`;
            }
            return groupStr;
        }).filter(g => g !== '');
        let pythonCode = groupConditions.length ? `if ${groupConditions.join(' ')}:` : '';
        return pythonCode;
    }

    /**
     * Builds the Python line that searches for the complement recordset
     * (records NOT in the original search result). This line is stored on
     * the node and injected by the code-generation engine at the start of
     * the ELSE block, making both branches independently executable.
     *
     * @returns {string|null} Python assignment string, or null if unavailable.
     */
    _buildElseSetupCode() {
        if (!this.isCronMode) return null;
        const variable = this.selectedCronVariable;
        if (!variable) return null;
        const modelName = variable.modelName || variable.modelId;
        if (!modelName) return null;
        return `${variable.variable_name}_complement = env['${modelName}'].search([('id', 'not in', ${variable.variable_name}.ids)])`;
    }

    get debug() {
        return !!odoo.debug
    }

    hasInvalidCondition(groups) {
        // Check all groups
        if (groups && Array.isArray(groups)) {
            for (let group of groups) {
                if (group.conditions.length < 1) return true;
                if (group.conditions && Array.isArray(group.conditions)) {
                    let condition = true;
                    for (let cond of group.conditions) {
                        condition = validateCondition(cond);
                        if (!condition) {
                            cond.isValid = false;
                            return true;
                        }
                    }
                }
            }
        }

        return false;
    }

    validateForm() {
        const inValidLabel = this.fieldState.label === "" || this.fieldState.label.trim() === ""
        const errors = {}
        if (inValidLabel) {
            this.labelInput.el.focus();
            this.labelInput.el.classList.add('invalid');
            errors["label"] = "invalid label";
        }

        // Cron mode only requires a search variable to be selected.
        if (this.isCronMode) {
            if (!this.state.cronVariableId) {
                errors["cronVariable"] = "Please select a search variable for the condition.";
            }
            let isValid = Object.entries(errors).length === 0;
            return { isValid, errors };
        }

        // Normal mode validates the full condition group tree.
        const inValidConditions = this.hasInvalidCondition(this.fieldState.condition_tree_value)
        if (inValidConditions) {
            errors["condition"] = "All condition must be valid!";
        }
        let isValid = Object.entries(errors).length === 0;
        return {isValid, errors};
    }

    generateCode() {
        const pythonCode = this.generatePythonCode(true)
        if (pythonCode.includes('re.match')) {
            this.props.updateImports({parent: "import re", child: "", nodeId: this.props.id})
        }
        if (pythonCode.includes('datetime')) {
            this.props.updateImports({parent: "from datetime import ", child: "datetime", nodeId: this.props.id})
        }
        return pythonCode
    }

    onConfirm() {
        if (this.isCronMode) {
            const variable = this.selectedCronVariable;
            // Persist the cron selection as a tagged object in condition_tree_value.
            // variableId restores the dropdown on re-open; variableName and modelName
            // are used by the parent node handler to register the complement variable.
            this.fieldState.condition_tree_value = {
                cronMode: true,
                variableId: this.state.cronVariableId,
                variableName: variable?.variable_name || null,
                modelName: variable?.modelName || variable?.modelId || null,
            };
            // Build and store the complement search line so the code-generation
            // engine can inject it at the boundary of the ELSE block.
            this.fieldState.else_setup_code = this._buildElseSetupCode();
        } else {
        this.fieldState.condition_tree_value = this.state.groups;
            // Clear any else_setup_code left from a previous cron-mode save.
            this.fieldState.else_setup_code = null;
        }
        this.env.bus.trigger("VALIDATE-CONDITION")
        super.onConfirm();
    }
}

ConditionNode.template = 'ConditionNode';
ConditionNode.components = {...ConfigurationBase.components, GroupComponent};
