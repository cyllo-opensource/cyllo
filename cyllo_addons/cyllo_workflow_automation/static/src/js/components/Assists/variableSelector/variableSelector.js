/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
const { useState, onWillStart, Component, onWillUpdateProps } = owl;
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { useVariable } from "../utils/utils";

export class VariableSelector extends Component {
    /**
     * VariableSelector is a component that allows users to select a variable from a list,
     * filtering variables based on field definitions and selected operators.
     */
    static defaultProps = {
        operator: "=",
        fieldDef: undefined
    }
    setup() {
        this.filterVariables = useVariable("def");
        this.filterVariablesNoDef = useVariable("noDef");
        this.orm = useService("orm");
        this.state = useState({
            variables: [],
            selectedVariable: false,
        })
        onWillStart(async () => {
            await this.handleProps(this.props);
        })
        onWillUpdateProps(async (p) => {
            await this.handleProps(p)
        })
    }
    /**
     * Handles the component's props and updates the state based on the provided properties.
     * @param {Object} props - The properties passed to the component
     */
    async handleProps (props) {
        this.state.selectedVariable = props.value?.selectedVariable || false
        if (!props.fieldDef) {
            this.state.variables = props.variables
        } else {
            if (props.fieldDef.noDef) {
                this.state.variables = this.filterVariablesNoDef(props.variables, props.fieldDef, props.operator)
            } else {
                this.state.variables = await this.filterVariables(props.variables, props.fieldDef, props.operator)
            }
        }
    }

    generatePathValue(value) {
        const { fieldDef, variables, operator } = this.props;
        const variable = variables.find(item => item.id === value);
        let pathVal = variable?.variable_name || false;
        if (!pathVal || !fieldDef) return pathVal;
        const type = fieldDef.noDef ? fieldDef.variable_type : fieldDef.type;
        const idOperators = new Set(["=", "!="]);
        const idsOperators = new Set(["in", "not in"]);
        if (type === "record" || type === "many2one") {
            if (idOperators.has(operator)) pathVal += ".id";
            else if (idsOperators.has(operator)) pathVal += ".ids";
        } else if (type === "recordset" || type === "many2many" || type === "one2many") {
            if (idOperators.has(operator) || idsOperators.has(operator)) pathVal += ".ids";
        }
        return pathVal;
    }

    get options() {
        return [[false, ""], ...this.state.variables.map(variable => [variable.id, variable.variable_name])];
    }

    async handleUpdateVariable(value) {
        this.props.update({ selectedVariable: value, pathValue: this.generatePathValue(value), isVariable: true });
    }
}

VariableSelector.template = "VariableSelector";
VariableSelector.components = { Select  };