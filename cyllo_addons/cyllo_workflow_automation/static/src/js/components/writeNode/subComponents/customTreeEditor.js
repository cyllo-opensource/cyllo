/** @odoo-module **/

import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {Component, onWillStart, onWillUpdateProps, useState} from "@odoo/owl";
import {useLoadFieldInfo} from "@web/core/model_field_selector/utils";
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {CheckBox} from "@web/core/checkbox/checkbox";
import {Input, Select} from "@web/core/tree_editor/tree_editor_components";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {filterVariable} from "../../Assists/utils/utils";
import {RecordPathSelector} from "../../Assists/recordPathSelector/recordPathSelector";
import {VariableSelector} from "../../Assists/variableSelector/variableSelector";
import {FieldTypeDropdown} from "../../Assists/fieldTypeDropdown/fieldTypeDropDown";

export const computeDefaultValue = (fieldDef) => {
    switch (fieldDef.type) {
        case 'one2many':
        case 'many2many':
            return [];
            break;
        case 'many2one':
        case 'boolean':
            return false;
            break
        case 'char':
            return '';
            break;
        case 'integer':
        case 'monetary':
        case 'float':
            return 0;
            break;
        case 'selection':
            const val = getValueEditorInfo(fieldDef, "=");
            const props = val.extractProps({
                value: false, update: () => {
                }
            });
            return props.options[0]?.[0] ?? false
            break;
        default:
            return false;
    }
}

export class CustomTreeEditor extends Component {
    static template = "cyllo_workflow_automation.CustomTreeEditor";
    static components = {
        ModelFieldSelector,
        CheckBox,
        Dropdown,
        DropdownItem,
        FieldTypeDropdown
    };
    setup() {
        this.loadFieldInfo = useLoadFieldInfo();
        this.tree = [];
        this.fieldDef = {};
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    async onPropsUpdated(np) {
        this.tree = np.tree
        const paths = this.extractPathsFromTree(np.tree);
        await this.loadFieldDefs(np.resModel, paths)
    }

    extractPathsFromTree(tree) {
        const paths = tree.map(node => node.path);
        return paths;
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
        this.fieldDefs = fieldDefs;
    }

    getFieldDef(path) {
        if (typeof path === "string") {
            return this.fieldDefs[path];
        }
        return null;
    }

    getValueEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operator = node.operator ? node.operator : "=";
        const editorValue = getValueEditorInfo(fieldDef, operator);
        if (node.selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        fieldDef,
                        variables: this.props.variables,
                    }
                }
            }
        } else if (node.selectionType === "record") {
            return {
                component: RecordPathSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        variables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                        fieldInfo: node.info,
                    }
                }
            }
        }
        return editorValue
    }


    async updatePath(node, path, info) {
        const {fieldDef} = await this.loadFieldInfo(this.props.resModel, path);
        if (!fieldDef) return
        const value = computeDefaultValue(fieldDef);
        this.props.nodeUpdate(node, {...node, path, value, type: fieldDef.type, info})
    }

    updateLeafValue(node, value) {
        this.props.nodeValueUpdate(node, {...node, value})
    }

    createNode() {
        this.props.createNewNode()
    }

    deleteNode(node) {
        this.props.deleteNode(node)
    }

    toggleIncludeVariable(value, node) {
        const isNewSelection = [value, undefined].includes(node.selectionType);
        node.selectionType = value;
        node.isVariable = value;
        const newValue = isNewSelection ? node.value : computeDefaultValue(node);
        this.updateLeafValue(node, newValue);
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }
}
