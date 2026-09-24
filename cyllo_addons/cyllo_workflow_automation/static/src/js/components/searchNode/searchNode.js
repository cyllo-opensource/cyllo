/** @odoo-module */
const { useState, onWillStart, useRef, useEffect, onMounted } = owl
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Dialog } from "@web/core/dialog/dialog";
import { CustomSearchDomainSelector } from "./subComponents/custom_search_domain_selector.js"
import { domainFromTree } from "./subComponents/custom_search_condition_tree";
import { Domain } from "@web/core/domain";
import { CharField } from "@web/views/fields/char/char_field";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { Record } from "@web/model/record";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { DynamicModelFieldSelectorChar } from "@web/views/fields/dynamic_widget/dynamic_model_field_selector_char";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { Select, Input } from "@web/core/tree_editor/tree_editor_components";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SearchNode extends ConfigurationBase {
    static template = "cyllo_workflow_automation.SearchNode"
    static components = {
        Dialog,
        CustomSearchDomainSelector,
        Many2XAutocomplete,
        CharField,
        IntegerField,
        SelectionField,
        Record,
        ModelFieldSelector,
        DynamicModelFieldSelectorChar,
        Many2OneField,
        CheckBox,
        Select,
        Input,
        Dropdown,
        DropdownItem
    }
    static props = ["*"];

    static defaultProps = {
        isDebugMode: false,
        readonly: false,
        context: {},
    };

    setup() {
        super.setup()
        this.fieldState = useState({ ...ConfigurationBase.fieldState, search_domain_tree: null })
        this.confirmButtonRef = useRef("confirm");
        this.modelState = useState({});
        useEffect((value) => {
            if (value) {
                this.setNewValue()
            }
        }, () => [this.fieldState.search_limit, this.modelState.model_name,]);
    }
    async fetchData() {
        await super.fetchData();
        await this.setModelState();
    }

    async setModelState() {
        const selectedModelId = this.fieldState.model_id;
        if (selectedModelId) {
            const selectedModel = await this.orm.read("ir.model", [selectedModelId], ["display_name", "model"]);
            if (selectedModel.length > 0) {
                const { display_name, model, id } = selectedModel[0];
                this.updateModelState({ display_name, model, id });
                return;
            }
        }

        if (!this.props.resModel) {
            return;
        }
        const model_res = await this.orm.searchRead("ir.model", [['model', '=', this.props.resModel]], ['display_name', 'model']);
        if (model_res.length > 0) {
            const { display_name, model, id } = model_res[0];
            this.updateModelState({ display_name, model, id })
        }
    }

    get pythonKeywords() {
        return this.props.identifiers?.pythonKeywords || [];
    }

    get existingVariables() {
        return (this.props.identifiers?.variableNames || []).filter(item => item !== this.initialVariableName);
    }

    get variableNameSuggestions() {
        const suggestions = new Set();
        const modelName = this.modelState?.model_name || '';

        if (modelName) {
            const parts = modelName.split('.');
            const last = parts[parts.length - 1];
            const full = modelName.replace(/\./g, '_');
            suggestions.add(`${last}s`);
            suggestions.add(last);
            suggestions.add(`${full}_results`);
        }

        suggestions.add('search_result');
        suggestions.add('records');

        const current = (this.state.searchInput || '').trim();
        if (current) suggestions.delete(current);

        return [...suggestions].slice(0, 5);
    }

    selectSuggestion(name) {
        this.state.searchInput = name;
        this.setNewValue();
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

    getModelsDomain() {
        return [];
    }

    get isSearchAll() {
        return !this.fieldState.search_limit;
    }

    toggleSearchAll(record, checked) {
        if (checked) {
            if (this.fieldState.search_limit) {
                this.state.lastSearchLimit = this.fieldState.search_limit;
            }
            record.update({ search_limit: 0 });
        } else {
            record.update({ search_limit: this.state.lastSearchLimit || 80 });
        }
    }

    onChangeLabel(label) {
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    get recordProps() {
        const related = {
            display_name: {
                name: "display_name",
                type: "char"
            }
        }
        const label = {
            type: "char",
            string: "Label"
        }
        const search_limit = {
            type: "integer",
            string: "Limit",
        }
        const search_order = {
            type: "selection",
            string: "Order",
        }

        const fields = { search_limit, search_order, label }
        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (var key in changes) {
                    this.fieldState[key] = changes[key]
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    async handleModelSelect(ev) {
        this.fieldState.search_domain_tree = {
            "children": [],
            "negate": false,
            "type": "connector",
            "value": "&"
        }
        if (!ev) {
            this.updateModelState({ display_name: false, model: '', id: false });
            this.fieldState.model_id = false;
            return;
        }
        const modelData = await this.orm.read('ir.model', [ev[0].id], ['display_name', 'model']);
        const display_name = ev[0].display_name ? ev[0].display_name : modelData[0].display_name;
        this.updateModelState({ ...modelData[0], display_name });
        this.fieldState.model_id = ev[0].id;
    }

    async updateModelBackend(model_id) {
        await this.orm.write("node.struct", [this.props.id], { model_id });
    }

    updateModelState({ display_name, model, id }) {

        this.modelState.model = display_name;
        this.modelState.model_id = id;
        this.modelState.model_name = model;
    }
    updatePath(path) {
        this.fieldState.search_order_field = path;
    }

    get domainSelectorProps() {
        return {
            className: this.props.className,
            readonly: this.props.readonly,
            isDebugMode: this.props.isDebugMode,
            defaultConnector: this.props.defaultConnector,
            resModel: this.modelState.model_name,
            tree: this.fieldState.search_domain_tree,
            variables: this.variables,
            update: (tree) => {
                this.fieldState.search_domain_tree = { ...tree };
            },
        };
    }

    onConfirm() {
        super.onConfirm();
    }

    getTreeValues(tree, variableMap) {
        if (tree.type === "condition") {
            tree.value = this.processConditionValue(tree.value, variableMap);
            return tree;
        }
        if (Array.isArray(tree.children)) {
            for (let i = 0; i < tree.children.length; i++) {
                tree.children[i] = this.getTreeValues(tree.children[i], variableMap);
            }
        }
        return tree;
    }

    processConditionValue(value, variableMap) {
        if (value && typeof value === "object" && 'record' in value) {
            const variableName = variableMap.get(value.record);
            this.updateUsedVariables(value.record);
            return variableName ? `v_${variableName}.${value.pathValue}` : value;
        } else if (value && typeof value === "object" && 'selectedVariable' in value) {
            this.updateUsedVariables(value.selectedVariable)
            return `v_${value.pathValue}`;
        }
        return value;
    }

    generateCode() {
        const variableMap = new Map(this.variables.map(v => [v.id, v.variable_name]));
        let domain = '[]';
        if (this.fieldState.search_domain_tree) {
            const result = this.getTreeValues(
                JSON.parse(JSON.stringify(this.fieldState.search_domain_tree)),
                variableMap
            );
            domain = Domain.and([domainFromTree(result)]).toString();
        }
        const limit = this.fieldState.search_limit || null;
        const order = this.findOrder(this.fieldState.search_order_field, this.fieldState.search_order);
        const formatedDomain = domain.replace(/"v_([^"]*)"/g, '$1');
        return `${this.fieldState.search_variable.variable_name} = env['${this.modelState.model_name}'].search(${formatedDomain}${order ? order : ''}${limit ? ', limit=' + limit : ''})`;
    }

    findOrder(field, order) {
        if (order && field) {
            return `, order="${field} ${order}"`;
        } else if (field) {
            return `, order="${field}"`;
        }
        return false;
    }

    get getOptions() {
        const variables = this.variables.map(variable => [variable.variable_name, variable.variable_name]);
        return [[false, ""], ...variables];
    }

    validateForm() {
        const { model_id, search_limit, search_variable, label } = this.fieldState;
        // Validation rules
        const errors = {};

        // Validate model_id: must be a non-empty string
        if (!model_id) {
            errors.model_id = "Model ID must be a non-empty.";
        }

        // Validate search_limit: must be a positive integer
        if (typeof (search_limit) == 'string' || search_limit < 0) {
            errors.search_limit = "Search limit must be a positive integer.";
        }

        // Validate search_variable: must be a non-empty string
        if (!search_variable.variable_name || typeof search_variable.variable_name !== 'string') {
            errors.search_variable = "Search variable must be a non-empty string.";
        } else {
            if (!this.validateInput(search_variable.variable_name)) {
                errors.search_variable = "Enter valid variable name."
            }
            clearTimeout(this.messageTimeout);
            this.messageTimeout = setTimeout(() => {
                owl.status(this) !== "destroyed" && this.clearMessages();
            }, 5000);
        }

        if (!label || typeof label !== 'string') {
            errors.label = "Label must be a non-empty string.";
        }

        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        // If no errors, form is valid
        return { isValid: true };

    }

    setNewValue() {
        if (this.fieldState.search_variable) {
            this.fieldState.search_variable = { id: this.fieldState.search_variable.id, variable_name: this.state.searchInput, modelId: this.fieldState.model_id, modelName: this.modelState.model_name, variable_type: this.fieldState.search_limit === 1 ? "record" : "recordset", variable_value: false, code: "", usedIn: [], delete: false }
        } else {
            this.fieldState.search_variable = { id: new Date().toISOString(), variable_name: this.state.searchInput, modelId: this.fieldState.model_id, modelName: this.modelState.model_name, variable_type: this.fieldState.search_limit === 1 ? "record" : "recordset", variable_value: false, code: "", usedIn: [], delete: false }
        }

    }
}
