/** @odoo-module */
const {useState} = owl;
import {_t} from "@web/core/l10n/translation";
import {Record} from "@web/model/record";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {Select, Input} from "@web/core/tree_editor/tree_editor_components";
import {CustomTreeEditor} from "./subComponents/customTreeEditor";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {CharField} from "@web/views/fields/char/char_field";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";

export class WriteNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.state = useState({
            model: null,
            modelId: null,
            tree: [],
        });
    }

    async fetchData() {
        await super.fetchData();
        await this.settingInitialModel();
        this.settingTreeData();
    }

    async settingInitialModel() {
        await this.settingModel();
    }

    async settingModel() {
        const selectedRecord = this.fieldState.write_selected_record;
        const model_id = (this.variables.find(v => v.id === selectedRecord?.value))?.modelId;
        if (model_id) {
            const [{model, id: modelId}] = await this.orm.read("ir.model", [model_id], ['model']);
            this.state.modelId = modelId;
            this.state.model = model;
        } else {
            this.state.modelId = null;
            this.state.model = null;
        }
    }

    settingTreeData() {
        if (this.fieldState.write_field_value) {
            this.state.tree = JSON.parse(this.fieldState.write_field_value);
        }
    }

    async updateObject(record) {
        this.fieldState.write_selected_record = this.getRecords.find(item => item.value === record);
        await this.settingModel();
        this.state.tree = [];
    }

    get getRecords() {
        const variables = [];
        this.variables.forEach(variable => {
            if (["record", "recordset"].includes(variable.variable_type) && variable.modelId) {
                variables.push({ value: variable.id, label: variable.variable_name });
            }
        });
        return variables;
    }

    get getVariables() {
        return this.variables.filter(variable => {
            return !(variable.modelId === this.props.primaryModelId && this.props.trigger === this.props.nodeName);
        });
    }

    get recordProps() {
        const label = { type: "char", string: "Label" };
        const fields = { label };
        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (const key in changes) {
                    this.fieldState[key] = changes[key];
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    filterFields(defs) {
        return defs.name !== "id" && defs.store;
    }

    getPathEditorInfo() {
        const resModel = this.state.model;
        const isDebugMode = true;
        return {
            component: ModelFieldSelector,
            extractProps: ({update, value: path}) => {
                return {
                    path,
                    update,
                    resModel,
                    isDebugMode,
                    filter: this.filterFields.bind(this),
                    readonly: false,
                    followRelations: false,
                };
            },
            isSupported: (path) => [0, 1].includes(path) || typeof path === "string",
            defaultValue: () => "id",
            stringify: (path) => path,
            message: _t("Invalid field chain"),
        };
    }

    nodeUpdate(prevNode, node) {
        const tree = this.state.tree.filter(item => item.path !== node.path);
        const index = tree.findIndex(item => item.path === prevNode.path);
        if (index !== -1) {
            tree.splice(index, 1, owl.reactive(node));
            this.state.tree = tree;
            this.settingFieldState(tree);
        }
    }

    nodeValueUpdate(prevNode, node) {
        const index = this.state.tree.findIndex(item => item.path === prevNode.path);
        if (index !== -1) {
            this.state.tree.splice(index, 1, owl.reactive(node));
            this.settingFieldState(this.state.tree);
        }
    }

    settingFieldState(tree) {
        this.fieldState.write_field_value = JSON.stringify([...tree]);
    }

    onChangeLabel(label) {
        const nodeId = this.props.id;
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    createNewNode() {
        this.state.tree = [
            ...this.state.tree,
            { id: new Date(), path: '', value: 1, type: 'integer' }
        ];
    }

    deleteNode(node) {
        const filteredTree = this.state.tree.filter(item => item.id != node.id);
        this.state.tree = filteredTree;
        this.settingFieldState(filteredTree);
    }

    generateCode() {
        const {write_field_value, write_selected_record} = this.fieldState;
        const writeValues = JSON.parse(write_field_value);
        const record = this.variables.find(v => v.id === write_selected_record?.value);
        let vals = {};
        writeValues.forEach(val => {
            if (val.path) {
                vals[val.path] = this.processValue(val);
            }
        });
        // For recordset: buildFlowLines already wraps in "for current_record in <var>:",
        // so write directly to current_record. For single record: use the variable name.
        const writeTarget = record.variable_type === 'recordset' ? 'current_record' : record.variable_name;
        return `${writeTarget}.write(${JSON.stringify(vals).replace(/"var_([^"]*)"/g, '$1')})`;
    }

    validateForm() {
        const {write_selected_record, write_field_value} = this.fieldState;
        const errors = {};

        if (!write_selected_record || Object.keys(write_selected_record).length === 0) {
            errors.write_selected_record = "A record must be selected.";
        }

        try {
            const parsed = JSON.parse(write_field_value);
            if (!parsed || parsed.length === 0) {
                errors.write_field_value = "You must set up fields and values to write.";
            } else if (parsed.some(item => item.path === "id")) {
                errors.write_field_value = "Id field is not writable.";
            }
        } catch (e) {
            errors.write_field_value = "Invalid field value.";
        }

        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        return {isValid: true};
    }
}

WriteNode.template = "WriteNode";
WriteNode.components = {
    ...ConfigurationBase.components,
    Many2OneField,
    CharField,
    CustomTreeEditor,
    Record,
    Select,
    Input,
    CustomDropdown,
};
