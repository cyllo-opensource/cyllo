/** @odoo-module */
const {useState, useEffect} = owl;
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Record} from "@web/model/record";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {CharField} from "@web/views/fields/char/char_field";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {CustomTreeEditor, computeDefaultValue} from "../writeNode/subComponents/customTreeEditor"
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {CheckBox} from "@web/core/checkbox/checkbox";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import {VariableSelector} from "../Assists/variableSelector/variableSelector";
import {useLoadFieldInfo} from "@web/core/model_field_selector/utils";
import {FieldTypeDropdown} from "../Assists/fieldTypeDropdown/fieldTypeDropDown"
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";

export class CreateNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.state = useState({
            fieldDefs: {}
        })
        this.loadFieldInfo = useLoadFieldInfo()
        this.fieldService = useService("field")

        useEffect(() => {
            this.setNewValue();
        }, () => [this.modelState.model])
    }
    async fetchData() {
        await super.fetchData();
        await this.updateModelState(true);
        const paths = this.requiredField.map(field => field.name)
        this.state.fieldDefs = this.modelState.model?.model
            ? await this.loadFieldDefs(this.modelState.model.model, paths)
            : {}
    }
    async loadFieldDefs(resModel, paths) {
        const promises = [];
        const fieldDefs = {};
        for (const path of paths) {
            if (typeof path === "string") {
                promises.push(
                    this.loadFieldInfo(resModel, path).then(({fieldDef}) => {
                        fieldDefs[path] = fieldDef;
                    })
                );
            }
        }
        await Promise.all(promises);
        return fieldDefs;
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(label) {
        this.fieldState.label = label
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    get tree() {
        return this.fieldState.create_tree_fields_values || [];
    }

    get requiredField() {
        return this.fieldState.create_required_field || [];
    }

    get createFields() {
        return this.fieldState.create_req_fields_values || {}
    }

    get pythonKeywords() {
        return this.props.identifiers.pythonKeywords || [];
    }

    get existingVariables() {
        return this.props.identifiers.variableNames.filter(item => item !== this.initialVariableName) || [];
    }

    handleInput(event) {
        this.validateInput(this.state.searchInput)
        clearTimeout(this.messageTimeout);
        this.messageTimeout = setTimeout(() => {
            owl.status(this) !== "destroyed" && this.clearMessages();
        }, 5000);
    }

    clearMessages() {
        this.state.errorMessage = "";
        this.state.successMessage = "";
    }

    get variableNameSuggestions() {
        const suggestions = new Set();
        const modelName = this.modelState?.model?.model || '';

        if (modelName) {
            const parts = modelName.split('.');
            const last = parts[parts.length - 1];
            const full = modelName.replace(/\./g, '_');
            suggestions.add(`new_${last}`);
            suggestions.add(last);
            suggestions.add(`${full}_record`);
        }

        suggestions.add('new_record');
        suggestions.add('record');

        const current = (this.state.searchInput || '').trim();
        if (current) suggestions.delete(current);

        return [...suggestions].slice(0, 5);
    }

    selectSuggestion(name) {
        this.state.searchInput = name;
        this.setNewValue();
    }

    getPathEditorInfo() {
        const resModel = this.modelState.model['model'];
        const isDebugMode = true;
        let component = ModelFieldSelector
        return {
            component: component,
            extractProps: ({update, value: path}) => {
                return {
                    path,
                    update,
                    resModel,
                    isDebugMode,
                    readonly: false,
                    followRelations: false,
                    filter: this.filterFields.bind(this),
                };
            },
            isSupported: (path) => [0, 1].includes(path) || typeof path === "string",
            defaultValue: () => "id",
            stringify: (path) => path,
            message: _t("Invalid field chain"),
        };
    }

    createNewNode() {
        this.fieldState.create_tree_fields_values = [
            ...this.tree,
            {
                id: new Date(),
                path: '',
                value: 1,
                type: 'integer'
            }
        ];
    }

    nodeUpdate(prevNode, node) {
        const tree = this.tree.filter(item => item.path !== node.path)
        const index = tree.findIndex(item => item.path === prevNode.path);
        if (index !== -1) {
            const updatedTree = [...tree];
            updatedTree[index] = owl.reactive(node);
            this.fieldState.create_tree_fields_values = updatedTree;
            this.settingFieldState(updatedTree);
        }
    }

    settingFieldState(tree) {
        this.fieldState.create_model_field_value = JSON.stringify([...tree]);
    }

    onChangeLabel(label) {
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    nodeValueUpdate(prevNode, node) {
        const index = this.tree.findIndex(item => item.path === prevNode.path);
        if (index !== -1) {
            const updatedTree = [...this.tree];
            updatedTree[index] = owl.reactive(node);
            this.fieldState.create_tree_fields_values = updatedTree;
            this.settingFieldState(updatedTree);
        }
    }

    deleteNode(node) {
        const filteredTree = this.tree.filter(item => item.id !== node.id);
        this.fieldState.create_tree_fields_values = filteredTree;
        this.settingFieldState(filteredTree);
    }

    removeObjectsWithPresentDependencies(data) {
        const fieldNames = data.map(item => item[0]);
        return data.filter(item => {
            const fieldName = item[0];
            const properties = item[1];
            if (fieldName === "company_id") {
                return false;
            }
            if (!properties.depends || properties.depends.length === 0) {
                return true;
            }
            return !properties.depends.some(dep => fieldNames.includes(dep));
        });
    }

    async fetchFields() {
        if (this.requiredField.length) return;
        const {model} = this.modelState.model;
        const fieldDefs = await this.fieldService.loadFields(model);
        const filteredDef = Object.entries(fieldDefs).filter(item => {
            if (model === "res.partner" && item[0] === "name") return true;
            return item[1].store && item[1].required && !item[1].readonly
        });
        const cleanedData = this.removeObjectsWithPresentDependencies(filteredDef);
        let defs = {}
        cleanedData.forEach(item => {
            defs[item[0]] = item[1];
        })
        const fields = cleanedData.map(item => {
            return {
                comodel: item[1].relation,
                is_property: !!item[1].relation,
                name: item[1].name,
                string: item[1].string,
                type: item[1].type,
            }
        })
        const paths = fields.map(field => field.name);
        this.state.fieldDefs = defs
        this.fieldState.create_required_field = [...fields]
    }

    updateField(field, value) {
        const updatedField = this.requiredField.find(item => item.name === field.name)
        updatedField.value = value;
    }

    getComponentProps(info, field) {
        const fieldDef = this.state.fieldDefs[field.name];
        const value = field.value || computeDefaultValue(fieldDef)
        if (!field.value) {
            this.updateField(field, computeDefaultValue(fieldDef))
        }
        const update = (value) => this.updateField(field, value);
        return info.extractProps({value, update})
    }

    getValueEditorInfo(field) {
        const fieldDef = this.state.fieldDefs[field.name]
        const operator = field.operator ? field.operator : "=";
        const editorValue = getValueEditorInfo(fieldDef, operator);
        if (field.selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        fieldDef,
                        variables: this.variables,
                    }
                }
            }
        } else if (field.selectionType === "record") {
            return {
                component: RecordPathSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        variables: this.variables.filter(variable => variable.variable_type === "record"),
                        fieldInfo: {fieldDef, resModel: this.modelState.model['model']},
                    }
                }
            }
        }
        return editorValue
    }

    filterFields(defs, path) {
        return defs.name !== "id" && defs.store;
    }

    async updateModelState(initial) {
        if (!this.fieldState.model_id) return
        if (!initial) this.fieldState.create_required_field = []
        const model = await this.orm.read("ir.model", [this.fieldState.model_id], []);
        this.modelState.model = model ? model[0] : {}
        await this.fetchFields()
    }

    toggleIncludeVariable(value, field) {
        const updatedField = this.requiredField.find(fld => fld.name === field)
        if (![value, undefined].includes(updatedField.selectionType)) {
            updatedField.value = computeDefaultValue(updatedField);
        }
        updatedField.selectionType = value;
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    get recordProps() {
        const related = {
            display_name: {
                name: "display_name",
                type: "char"
            }
        }
        const model_id = {
            type: "many2one",
            relation: "ir.model",
            string: "Model",
            related: {
                activeFields: related,
                fields: related,
            },
        }
        const fields = {
            model_id,
        }
        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (var key in changes) {
                    this.fieldState[key] = changes[key]
                    if (key === "model_id") this.updateModelState(false);
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    get getVariables() {
        let variables = []
        this.variables.map(variable => {
            if (!(variable.modelId === this.props.primaryModelId && this.props.trigger === this.props.nodeName)) {
                variables.push(variable);
            }
        })
        return variables
    }

    get getDomain() {
        let domain = [['transient', '=', false]];
        if (this.props.trigger === this.props.nodeName) {
            domain = [['id', '!=', this.props.primaryModelId], ['transient', '=', false]];
        }
        return domain;
    }

    generateCode() {
        const {model} = this.modelState.model;
        const {search_variable} = this.fieldState;
        const varName = search_variable?.variable_name || 'new_record';
        const vals = {};
        [...this.requiredField, ...this.tree].forEach(val => {
            const key = val.name || val.path;
            if (key) {
                vals[key] = this.processValue(val);
            }
        });
        const stringifiedVals = JSON.stringify(vals).replace(/"var_([^"]*)"/g, '$1');
        return `${varName} = env["${model}"].create(${stringifiedVals})`;
    }

    validateForm() {
        const {model_id, search_variable, label} = this.fieldState;
        const errors = {};
        if (!search_variable || !search_variable.variable_name || typeof search_variable.variable_name !== 'string') {
            errors.search_variable = "variable must be a non-empty string.";
        } else {
            if (!this.validateInput(search_variable.variable_name)) {
                errors.search_variable = "Enter valid variable name."
            }
            clearTimeout(this.messageTimeout);
            this.messageTimeout = setTimeout(() => {
                owl.status(this) !== "destroyed" && this.clearMessages();
            }, 5000);
        }
        if (!model_id) {
            errors.model_id = "Missing Model.";
        } else if (this.props.trigger === this.props.nodeName && this.props.primaryModelId === model_id) {
            errors.model_id = "You can't create a node for the same model.";
        }
        this.requiredField.forEach(val => {
            if (!val.value && val.value !== 0) {
                errors[val.name] = `Missing ${val.string}.`;
            }
        })
        if (!label || typeof label !== 'string') {
            errors.label = "Label must be a non-empty string.";
        }
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        // If no errors, form is valid
        return {isValid: true};
    }

    setNewValue() {
        if (this.fieldState.search_variable) {
            this.fieldState.search_variable = {
                id: this.fieldState.search_variable.id,
                variable_name: this.state.searchInput,
                modelId: this.fieldState.model_id,
                modelName: this.modelState.model.model,
                variable_type: "record",
                variable_value: false,
                code: "",
                usedIn: [],
                delete: false
            }
        } else {
            this.fieldState.search_variable = {
                id: new Date().toISOString(),
                variable_name: this.state.searchInput,
                modelId: this.fieldState.model_id,
                modelName: this.modelState.model.model,
                variable_type: "record",
                variable_value: false,
                code: "",
                usedIn: [],
                delete: false
            }
        }
    }
}

CreateNode.template = "CreateNode";
CreateNode.components = {
    ...ConfigurationBase.components,
    Many2OneField,
    CharField,
    Record,
    CustomTreeEditor,
    CheckBox,
    DropdownItem,
    Dropdown,
    RecordPathSelector,
    FieldTypeDropdown
};