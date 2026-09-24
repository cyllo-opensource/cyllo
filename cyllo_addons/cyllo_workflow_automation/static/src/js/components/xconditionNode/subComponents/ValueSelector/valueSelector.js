/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
const { useState, onWillStart, Component, onWillUpdateProps } = owl;
import { RecordPathSelector } from "../../../Assists/recordPathSelector/recordPathSelector";
import { VariableSelector } from "../../../Assists/variableSelector/variableSelector";
import {
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import { Input, Select, Range } from "@web/core/tree_editor/tree_editor_components";
import {
    DomainSelectorAutocomplete, DomainSelectorSingleAutocomplete
} from "@web/core/tree_editor/tree_editor_autocomplete";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { FieldTypeDropdown } from "../../../Assists/fieldTypeDropdown/fieldTypeDropDown";
import {ErrMessage} from "../../../Assists/errorComponent/error";

const { DateTime } = luxon;

const COMPONENTS = {
    variable: VariableSelector,
    record: RecordPathSelector,
};

const STATIC_COMPONENTS = {
    number: Input,
    string: Input,
    boolean: Select,
    record: DomainSelectorSingleAutocomplete,
    recordset: DomainSelectorAutocomplete,
    date: DateTimeInput,
    datetime: DateTimeInput,
};

export class ValueSelector extends Component {
    static defaultProps = {
        operator: "="
    };

    static template = "ValueSelector";
    static components = { FieldTypeDropdown };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            fieldType: this.props.fieldType,
            condition: this.props.condition,
            value: this.props.value,
        });

        this.varModelDefs = new Map();
        onWillStart(async () => {
            await this.processVariablesAndModels();
        });

        onWillUpdateProps((props) => {
            this.state.fieldType = props.fieldType;
            this.state.condition = props.condition
            this.state.value = props.value;
        })
    }

    async processVariablesAndModels() {
        const varModels = this.props.variables
            .filter(item => item.modelId)
            .map(item => ({
                variableId: item.id,
                modelId: item.modelId,
            }));

        const modelIds = [...new Set(varModels.map(item => item.modelId))];
        const models = await this.orm.read("ir.model", modelIds, ["model"]);
        const modelMap = new Map(models.map(model => [model.id, model.model]));
        this.varModelDefs = new Map(
            varModels.map(variable => [
                variable.variableId,
                modelMap.get(variable.modelId)
            ])
        );
    }

    handleUpdateValue(value) {
        this.props.update({ value, fieldType: this.state.fieldType });
    }

    get btwError() {
        return {
            component: ErrMessage,
            extractProps: ({}) => ({
                message: "Between operator is not applicable to dynamic values !"
            })
        }
    }

    get component() {
        return COMPONENTS[this.state.fieldType];
    }

    get getFieldInfo() {
        const { field, fieldType, operator } = this.state.condition;
        if (!field) return false;

        const handlers = {
            record: () => this.handleRecordFieldType(field, operator),
            variable: () => this.handleVariableFieldType(field, operator)
        };

        return fieldType && operator ? handlers[fieldType]?.() : false;
    }

    handleRecordFieldType(field, operator) {
        const { info: { fieldDef } } = field;
        const handlers = {
            static: () => this.getStaticRecordEditorInfo(fieldDef, operator),
            variable: () => this.getVariableSelectorInfo(operator, fieldDef),
            record: () => this.getRecordPathSelectorInfo(operator, field.info)
        };
        return handlers[this.state.fieldType]?.();
    }

    getStaticRecordEditorInfo(fieldDef, operator) {
        if (!fieldDef) {
            return false;
        }
        if (fieldDef.type === "record") {
            if (["set", "not_set"].includes(operator)) {
                return false;
            }
            if (["in", "not in"].includes(operator)) {
                return {
                    component: DomainSelectorAutocomplete,
                    extractProps: ({ value, update }) => ({
                        resIds: value || [],
                        update,
                        resModel: fieldDef.relation || "",
                        placeholder: "Select records here..."
                    }),
                };
            }
            if (["=", "!="].includes(operator)) {
                return {
                    component: DomainSelectorSingleAutocomplete,
                    extractProps: ({ value, update }) => ({
                        resId: value || false,
                        update,
                        resModel: fieldDef.relation || "",
                        placeholder: "Select record here..."
                    }),
                };
            }
            return false;
        }
        if (fieldDef.type === "recordset") {
            if (["set", "not_set"].includes(operator)) {
                return false;
            }
            return {
                component: DomainSelectorAutocomplete,
                extractProps: ({ value, update }) => ({
                    resIds: value || [],
                    update,
                    resModel: fieldDef.relation || "",
                    placeholder: "Select records here..."
                }),
            };
        }
        return getValueEditorInfo(fieldDef, operator);
    }

    handleVariableFieldType(field, operator) {
        const variable = this.props.variables.find(v => v.id === field.selectedVariable);
        const info = {
            fieldDef: {
                type: variable?.variable_type,    //TODO:Temporarily added ternary function to avoid error
                relation: variable?.modelName,
            }
        }
        const handlers = {
            variable: () => this.getVariableSelectorInfo(operator, { isVariable: true, noDef: true, ...variable }),
            record: () => this.getRecordPathSelectorInfo(operator, info),
            static: () => this.staticEditorValue(variable, operator)
        };

        return handlers[this.state.fieldType]?.();
    }
    getVariableSelectorInfo(operator, fieldDef) {
        if(["set", "not_set"].includes(operator)) return false;
        if (operator === "between") {
            return this.btwError
        }
        return {
            component: VariableSelector,
            extractProps: ({value, update}) => ({
                value,
                update,
                operator,
                fieldDef,
                variables: this.props.variables,
            })
        };
    }

    getRecordPathSelectorInfo(operator, fieldInfo = undefined) {
        if(["set", "not_set"].includes(operator)) return false;
        if (operator === "between") {
            return this.btwError
        }
        return {
            component: RecordPathSelector,
            extractProps: ({value, update}) => ({
                value,
                update,
                operator,
                fieldInfo,
                variables: (this.props.variables || []).filter(v => v.variable_type === "record"),
            })
        };
    }

    staticEditorValue(variable, operator) {
        if(!variable) return false;
        if(["set", "not_set"].includes(operator)) return false;
        const { id, variable_type } = variable;
        const handlers = {
            number: () => this.inputComponent("number", operator),
            string: () => this.inputComponent("string", operator),
            boolean: () => this.booleanComponent,
            record: () => this.getRecordComponent(variable_type, id, operator),
            recordset: () => this.getRecordsetComponent(variable_type, id),
            date: () => this.getDateTimeComponent(variable_type, operator),
            datetime: () => this.getDateTimeComponent(variable_type, operator),
        };
        return handlers[variable_type]?.() || false;
    }

    getBetweenComponent (type, defaultValue) {
        const editorInfo = getValueEditorInfo({type}, "=");
            return {
                component: Range,
                extractProps: ({value, update}) => ({
                    value: value ? value : defaultValue,
                    update,
                    editorInfo,
                }),
                isSupported: (value) => Array.isArray(value) && value.length === 2,
                defaultValue: () => {
                    const {defaultValue} = editorInfo;
                    return [defaultValue(), defaultValue()];
                },
            };
    }

    inputComponent(type, operator) {
        if (operator === "between") {
            return this.getBetweenComponent("float", [0, 0]);
        }
        return {
            component: Input,
            extractProps: ({value, update}) => ({ value, update }),
        };
    }

    get booleanComponent() {
        return {
            component: Select,
            extractProps: ({value, update}) => ({
                value,
                update,
                options: [[false, 'False'], [true, 'True']],
            }),
        };
    }

    getDateTimeComponent(type, operator) {
        if (operator === "between") {
            return this.getBetweenComponent(type, [false, false]);
        }
        return {
            component: DateTimeInput,
            extractProps: ({value, update}) => ({
                value: value === false ? false : this.genericDeserializeDate(type, value),
                placeholder: type === "date" ? "Select date" : "Select datetime",
                type,
                onApply: (value) => {
                    if (value) {
                        update(this.genericSerializeDate(type, value || DateTime.local()));
                    }
                },
            }),
        };
    }

    getRecordsetComponent(type, variableId) {
        return {
            component: DomainSelectorAutocomplete,
            extractProps: ({value, update}) => {
                return {
                    resIds: value || [],
                    update,
                    resModel: this.varModelDefs.get(variableId),
                    placeholder: "Select records here..."
                }
            },
        };
    }

    getRecordComponent(type, variableId, operator) {
        if (["in", "not in"].includes(operator)) {
            return this.getRecordsetComponent(type, variableId);
        } else if (["=", "!="].includes(operator)) {
            return {
                component: STATIC_COMPONENTS[type],
                extractProps: ({value, update}) => {
                    return {
                        resId: value || false,
                        update,
                        resModel: this.varModelDefs.get(variableId) || "",
                        placeholder: "Select record here..."
                    }
                },
            };
        }
        return false;
    }

    genericDeserializeDate(type, value) {
        return type === "date" ? deserializeDate(value) : deserializeDateTime(value);
    }

    genericSerializeDate(type, value) {
        return type === "date" ? serializeDate(value) : serializeDateTime(value);
    }

    get getDefaultValue() {
        return this.state.value;
    }

    selectFieldType(type) {
        this.props.updateFieldType(type)
    }

    getDropdownLabel(selectionType) {
        const labels = {
            variable: "Variable",
            record: "Record",
            static: "Fixed"
        };
        return labels[selectionType] || "Fixed";
    }
}
