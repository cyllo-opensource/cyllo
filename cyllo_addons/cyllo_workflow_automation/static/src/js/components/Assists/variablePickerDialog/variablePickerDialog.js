/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { FieldTypeDropdown } from "../fieldTypeDropdown/fieldTypeDropDown";
import { VariableSelector } from "../variableSelector/variableSelector";
import { RecordPathSelector } from "../recordPathSelector/recordPathSelector";

export class VariablePickerDialog extends Component {
    static template = "cyllo_workflow_automation.VariablePickerDialog";
    static components = { Dialog, FieldTypeDropdown, VariableSelector, RecordPathSelector };
    static props = {
        close: Function,
        onInsert: Function,
        variables: Array,
        modelState: { type: Object, optional: true },
    };

    setup() {
        this.state = useState({
            selectionType: 'variable',
            value: {},
        });
    }

    setSelectionType(type) {
        this.state.selectionType = type;
        this.state.value = {};
    }

    getDropdownLabel(selectionType) {
        const labels = {
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Variable';
    }

    get typeOptions() {
        return [
            { value: 'variable', label: 'Variable' },
            { value: 'record', label: 'Record' },
        ];
    }

    onUpdateValue(value) {
        this.state.value = value;
    }

    get recordVariables() {
        return (this.props.variables || []).filter(variable => variable.variable_type === "record");
    }

    get recordFieldInfo() {
        return null;
    }

    get canInsert() {
        if (this.state.selectionType === 'variable') {
            return !!this.state.value.pathValue;
        } else if (this.state.selectionType === 'record') {
            return !!this.state.value.record && !!this.state.value.pathValue;
        }
        return false;
    }

    onInsert() {
        if (this.state.selectionType === 'variable') {
            this.props.onInsert(`{{ ${this.state.value.pathValue} }}`);
        } else if (this.state.selectionType === 'record') {
            const recordVar = this.props.variables.find(v => v.id === this.state.value.record);
            if (recordVar) {
                this.props.onInsert(`{{ ${recordVar.variable_name}.${this.state.value.pathValue} }}`);
            }
        }
        this.props.close();
    }
}
