/** @odoo-module */
const { useState, useEffect, onMounted, xml, markup, useRef } = owl;
import { Input, Select } from "@web/core/tree_editor/tree_editor_components";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { ConfigurationBase } from "../configurationBase/configurationBase.js"
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import RealTimeInput from "../Assists/Input/Input";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
const { DateTime } = luxon;

export class VariableNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.fieldState = useState({ ...this.props.variable })
        this.initialLoad = true
        this.state = useState({
            errorMessage: "",
            successMessage: "",
            valueErrorMessage: "",
        });
        this.variableNameRef = useRef("variableName");
        useEffect((type) => {
            if (!this.initialLoad) this.fieldState.variable_value = false
            this.initialLoad = false
        }, () => [this.fieldState.type]);
    }

    getComponent(type) {
        switch (type) {
            case 'string':
            case 'number':
            case 'code':
                return this.getInputComponent(type);
            case 'boolean':
                return this.getBooleanComponent();
            case 'date':
            case 'datetime':
                return this.getDateTimeComponent(type);
            case 'object':
                return this.getRecordPathSelector()
            default:
                throw new Error(`Unknown type: ${type}`);
        }
    }

    getInputComponent(type) {
        return {
            'component': RealTimeInput,
            'extractProps': (value, update) => ({
                value,
                update,
            }),
        };
    }

    getBooleanComponent() {
        return {
            'component': Select,
            'extractProps': (value, update) => ({
                value,
                update,
                options: [[false, 'False'], [true, 'True']],
            }),
        };
    }

    getDateTimeComponent(type) {
        return {
            'component': DateTimeInput,
            'extractProps': (value, update) => ({
                value: value === false
                    ? false
                    : this.genericDeserializeDate(type, value),
                type,
                onApply: (value) => {
                    if (value) {
                        update(this.genericSerializeDate(type, value || DateTime.local()));
                    }
                },
            }),
        };
    }

    getRecordPathSelector = () => {
        return {
            'component': RecordPathSelector,
            extractProps: (value, update) => {
                return {
                    value,
                    update,
                    variables: this.filterVariables,
                }
            },
        };
    }

    get optionsType() {
        return [
            {value: false, label: ''},
            {value: 'string', label: 'String'},
            {value: 'number', label: 'Number'},
            {value: 'date', label: 'Date'},
            {value: 'datetime', label: 'DateTime'},
            {value: 'boolean', label: 'Boolean'},
            {value: 'code', label: 'Python Expression'},
            {value: 'object', label: 'Records'}
        ];
    }

    get returnTypeOptions() {
        return [
            { value: false, label: '' },
            { value: 'string', label: 'String' },
            { value: 'number', label: 'Number' },
            { value: 'date', label: 'Date' },
            { value: 'datetime', label: 'DateTime' },
            { value: 'boolean', label: 'Boolean' },
        ];
    }

    get variableName() {
        return this.fieldState.variable_name || false
    }

    get variableType() {
        return this.fieldState.type || false
    }

    get variableValue() {
        return this.fieldState.variable_value || false
    }

    get pythonKeywords() {
        return this.props.identifiers.pythonKeywords || []
    }

    get codeReturnType() {
        return this.fieldState.code_return_type || false
    }

    get existingVariables () {
        return this.props.identifiers.variableNames.filter(item => item !== this.props.variable.variable_name) || [];
    }

    handleInput(event) {
        const value = event.target.value;
        this.fieldState.variable_name = value;
        this.validateInput(value);
        clearTimeout(this.messageTimeout);
        this.messageTimeout = setTimeout(() => {
            owl.status(this) !== "destroyed" && this.clearMessages();
        }, 5000);
    }

    clearMessages() {
        this.state.errorMessage = "";
        this.state.successMessage = "";
    }

    handleUpdateField(field, value) {
        this.fieldState[field] = value
        if (field === "code_return_type" && this.fieldState.type === "code") {
            this.fieldState.variable_type = value || "string";
            // Important: Sync to props if available
            this.state.successMessage = ""; // Clear success on change
        }
    }

    genericDeserializeDate(type, value) {
        return type === "date" ? deserializeDate(value) : deserializeDateTime(value);
    }

    genericSerializeDate(type, value) {
        return type === "date" ? serializeDate(value) : serializeDateTime(value);
    }

    get filterVariables () {
        return (this.props.variables || []).filter(variable => {
            if (variable.scopeId === this.fieldState.scopeId) {
                if (this.fieldState.id) {
                    return new Date(this.fieldState.id) > new Date(variable.id) && variable.variable_type === "record"
                }
            }
            return variable.variable_type === "record"
        })
    }

    validateVariableValue(type, value) {
        let isValid = true;
        let errorMessage = "";

        switch (type) {
            case 'string':
                // check if it's a valid string
                if (typeof value !== "string" || value.trim() === "") {
                    isValid = false;
                    errorMessage = "String cannot be empty.";
                }
                break;
            case 'number':
                // Check if it's a valid number
                if (isNaN(Number(value))) {
                    isValid = false;
                    errorMessage = "Please enter a valid number.";
                }
                break;
            case 'boolean':
                // Check if it's a valid boolean
                if (value !== true && value !== false) {
                    isValid = false;
                    errorMessage = "Boolean value must be true or false.";
                }
                break;
            case 'date':
                // Check if it's a valid date
                if (isNaN(Date.parse(value))) {
                    isValid = false;
                    errorMessage = "Please enter a valid date.";
                }
                break;
            case 'datetime':
                // Check if it's a valid datetime
                if (isNaN(Date.parse(value))) {
                    isValid = false;
                    errorMessage = "Please enter a valid date and time.";
                }
                break;
            case 'code':
                // Check if it's a valid python expression
                if (typeof value !== "string" || value.trim() === "") {
                    isValid = false;
                    errorMessage = "Code cannot be empty.";
                }
                break;
            case 'object':
                // For object, we might want to check if it has the required properties
                if (!value || !value.record || !value.pathValue) {
                    isValid = false;
                    errorMessage = "Please select a valid record and path.";
                }
                break;
        }
        return {isValid, errorMessage};
    }

    async updateVariableValue (value) {
        const { isValid, errorMessage} = this.validateVariableValue(this.fieldState.type, value)
        this.fieldState.variable_value = value;

        if (!isValid) {
            this.state.valueErrorMessage = errorMessage;
            clearTimeout(this.valueMessageTimeout);
            this.valueMessageTimeout = setTimeout(() => {
                if (owl.status(this) !== "destroyed") this.state.valueErrorMessage = "";
            }, 5000);
            return;
        } else {
            this.state.valueErrorMessage = "";
        }
        this.fieldState.modelId = undefined;
        if (this.fieldState.type === "object") {
            const { info : { fieldDef: { type, relation }, resModel } } = value;
            const model = await this.orm.searchRead("ir.model", [["model", "=", relation]], ["model"])
            if (type === "many2one") {
                this.fieldState.variable_type = "record";
                this.fieldState.modelId = model[0].id
                this.fieldState.modelName = relation
            }
            else if (["many2many", "one2many"].includes(type)) {
                this.fieldState.variable_type = "recordset";
                this.fieldState.modelId = model[0].id
                this.fieldState.modelName = relation
            }
            else if (["html", "char", "selection", "text"].includes(type)) {
                this.fieldState.variable_type = "string";
            }
            else if (type === "boolean") {
                this.fieldState.variable_type = "boolean";
            }
            else if (["monetary", "float", "integer"].includes(type)) {
                this.fieldState.variable_type = "number";
            }
            else if (type === "datetime") {
                this.fieldState.variable_type = "datetime";
            }
            else if (type === "date") {
                this.fieldState.variable_type = "date";
            }
            else if (type === "binary") {}
        } else if (this.fieldState.type === "code") {
            this.fieldState.variable_type = this.fieldState.code_return_type || "string"; // fallback
        }else {
            this.fieldState.variable_type = this.fieldState.type;
        }
    }

    generateCode() {
        const { variable_name, variable_value, type } = this.fieldState;
        let code = `${variable_name} = ${this.generateCodeValue(type, variable_value)}`
        return code || ""
    }

    generateCodeValue(type, value) {
        if (['string', 'date', 'datetime'].includes(type)) return `"${value}"`;
        else if (['boolean'].includes(type)) return value ? 'True' : 'False';
        else if (type === "object") {
            if ("record" in value) {
                return `${this.props.variables.find(item => item.id === value.record).variable_name}.${value.path}`
            }
        }
        else return value;
    }

    validateForm() {
         // Destructure fields from the field state
        const { type, code_return_type, variable_type, variable_name, variable_value } = this.fieldState;
        const { isValid, errorMessage } = this.validateVariableValue(type, variable_value)
        // Initialize an errors object
        const errors = {};
        if (type === "code" && !code_return_type) {
            errors.code_return_type = "Please select a return type for the Python expression."
        }
        if (!variable_type) {
            errors.variable_type = "Missing variable type."
        }
        if (!variable_name) {
            errors.variable_name = "Missing variable name."
        } else {
            if(!this.validateInput(variable_name)) {
                errors.variable_name = "Enter valid variable name."
            }
            clearTimeout(this.messageTimeout);
            this.messageTimeout = setTimeout(() => {
                owl.status(this) !== "destroyed" && this.clearMessages();
            }, 5000);
        }

        if (!variable_value) {
            errors.variable_value = "Missing variable value."
        }

        if(!isValid) {
            this.state.valueErrorMessage = errorMessage;
            errors.value = errorMessage;
        }

        //Dependency check (don't allow rename if usedIn is not empty)
        const originalVariable = this.props.variables.find(v => v.variable_name === this.props.variable.variable_name);
        if (this.props.mode === 'edit' && originalVariable?.usedIn?.length > 0) {
            if (this.fieldState.variable_name !== originalVariable.variable_name) {
                errors.variable_name = "This variable is used in other nodes. Rename blocked until dependencies are cleared.";
            }
        }

        // Return the validation result
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        return { isValid: true };
    }

    renderGroup() {
        return markup(`<h1>HHHHHAAAAAAAIIIIIII</h1>`);
    }

}

// Define the tempalate and components for the ConfigurationDialog component
VariableNode.template = "VariableNode";
VariableNode.components = { ...ConfigurationBase.components, Input, Select, DateTimeInput, CustomDropdown };