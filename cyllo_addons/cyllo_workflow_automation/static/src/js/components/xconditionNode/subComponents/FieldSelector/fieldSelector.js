/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
const { useState, onWillStart, Component, onWillUpdateProps } = owl;
import { RecordPathSelector } from "../../../Assists/recordPathSelector/recordPathSelector";
import { VariableSelector } from "../../../Assists/variableSelector/variableSelector";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { FieldTypeDropdown } from "../../../Assists/fieldTypeDropdown/fieldTypeDropDown";

const DEFAULT_OPTIONS = [{
        value: 'variable',
        label: 'Variable',
    },
    {
        value: 'record',
        label: 'Record',
    },]

const COMPONENTS = {
    variable : VariableSelector,
    record : RecordPathSelector,
}

export class FieldSelector extends Component {
    static defaultProps = {
        operator: "="
    }
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            fieldType: this.props.fieldType,
            value: this.props.field,
        })

        onWillUpdateProps((props) => {
            this.state.fieldType = props.fieldType
            this.state.value = props.field
        })

    }
    updateField(value) {
        this.state.value = value;
        this.props.update(value)
    }

    get component() {
        return COMPONENTS[this.state.fieldType];
    }

    get variableProps() {
        return {
            value: this.state.value,
            update: this.updateField.bind(this),
            variables: this.props.variables,
        }
    }

    get recordProps() {
        return {
            value: this.state.value,
            update: this.updateField.bind(this),
            variables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
        }
    }

    get extractProps() {
        if (this.state.fieldType === "variable") return this.variableProps
        else if (this.state.fieldType === "record") return this.recordProps
    }

    selectFieldType(type) {
        this.props.updateFieldType(type)
    }

    get defaultOptions() {
        return DEFAULT_OPTIONS
    }

    getDropdownLabel(selectionType) {
        if (selectionType === "variable") return "Variable";
        else if (selectionType === "record") return "Record";
    }

}

FieldSelector.template = "FieldSelector";
FieldSelector.components = { VariableSelector, RecordPathSelector, DropdownItem, Dropdown, FieldTypeDropdown };
