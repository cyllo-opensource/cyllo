/** @odoo-module */
const {useState, onWillStart, useEffect} = owl;
import {useService} from "@web/core/utils/hooks";
import {Record} from "@web/model/record";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {Select, Input} from "@web/core/tree_editor/tree_editor_components";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {AutoComplete} from "@web/core/autocomplete/autocomplete";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {VariableSelector} from "../Assists/variableSelector/variableSelector";
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {TypeToggler} from "../Assists/typeToggler/TypeToggler";
import {FieldTypeDropdown} from "../Assists/fieldTypeDropdown/fieldTypeDropDown";
import {MailRecordPathSelector} from "../mailNode/subcomponents/mailRecordPathSelector";
import {MultiDataSelector} from "../FollowerNode/subComponents/multiDataSelector";
import {_t} from "@web/core/l10n/translation";
import {VariablePickerDialog} from "../Assists/variablePickerDialog/variablePickerDialog";

export class SmsNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.messageTextareaRef = owl.useRef("messageTextarea");
        this.dialogService = useService("dialog");
    }

    get getEmailTypes() {
        return [
            {label: "custom", value: false},
            {label: "Template", value: true},
        ]
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(ev) {
        this.fieldState.label = ev
        const label = ev
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    get getType() {
        return this.fieldState.sms_isTemplate || false
    }

    setType(value) {
        this.fieldState.sms_isTemplate = value.value
    }

    get getMessage() {
        return this.fieldState.sms_message || ''
    }

    updateMessage(message) {
        this.fieldState.sms_message = message
    }

    openVariablePicker() {
        this.dialogService.add(VariablePickerDialog, {
            variables: this.props.variables,
            modelState: this.modelState,
            onInsert: (expression) => {
                const textarea = this.messageTextareaRef.el;
                if (textarea) {
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    const text = this.getMessage;
                    const before = text.substring(0, start);
                    const after = text.substring(end, text.length);
                    const newText = before + expression + after;
                    this.updateMessage(newText);
                    setTimeout(() => {
                        textarea.value = newText;
                        textarea.focus();
                        textarea.setSelectionRange(start + expression.length, start + expression.length);
                    }, 0);
                } else {
                    this.updateMessage(this.getMessage + expression);
                }
            }
        });
    }

    setInputValue(ev) {
        this.fieldState.mailCustomData.subject = ev
    }

    setMessageValue(ev) {
        this.fieldState.mailCustomData.message = ev
    }

    getDomain() {
        return [["model_id", "=", this.getModelId]]
    }

    get getModelId() {
        const modelId = this.variables.find(variable => variable.id === this.fieldState.sms_record.value)
        return modelId?.modelId || false
    }

    get getModel() {
        return this.fieldState.sms_record?.variable_name || ""
    }

    get getTemplate() {
        return this.fieldState.sms_template.name || ''
    }

    get getRecords() {

        let variables = []
        this.variables.forEach(variable => {
            variable.variable_type === 'record' && variable.modelId ? variables.push({
                value: variable.id,
                label: variable.variable_name
            }) : null
        })
        return variables
    }

    updateObject(record) {
        this.fieldState.sms_record = this.getRecords.find((item) => item.value === record)
    }

    getReceiverData() {
        !this.fieldState.sms_partner_ids ? this.fieldState.sms_partner_ids = [{value: []}] : false
        return this.fieldState.sms_partner_ids
    }

    setReceiverData(value, index) {
        const actualIndex = index ? index : 0
        this.fieldState.sms_partner_ids[actualIndex] = this.fieldState.sms_partner_ids[actualIndex] || {}
        this.fieldState.sms_partner_ids[actualIndex].value = value
    }

    getValueEditorInfo(field) {
        const fieldDef = {type: 'many2many', relation: 'res.partner', string: 'Partners'}
        const operator = "in";
        const editorValue = getValueEditorInfo(fieldDef, 'in');
        const selectionType = field.selectionType || ''
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        allVariable: true,
                        variables: (this.props.variables || []).filter(variable => (variable.variable_type === "recordset" || variable.variable_type === "record") && [85, 97].includes(variable.modelId)),
                    }
                }
            }
        } else if (selectionType === "record") {
            const fieldInfo = {
                resModel: this.modelState.model['model'],
                fieldDef: {type: 'many2one', relation: ['res.partner', 'res.users']}
            }
            return {
                component: MailRecordPathSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        variables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                        fieldInfo,
                    }
                }
            }
        }
        return editorValue
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    toggleIncludeVariable(value, index) {
        if (!this.fieldState.sms_partner_ids[index] || typeof this.fieldState.sms_partner_ids[index] !== 'object') {
            this.fieldState.sms_partner_ids[index] = {value: [], selectionType: value};
        } else if (![value, undefined].includes(this.fieldState.sms_partner_ids[index].selectionType)) {
            this.fieldState.sms_partner_ids[index] = {value: [], selectionType: value}
        } else this.fieldState.sms_partner_ids[index].selectionType = value
    }

    removeData(indexToRemove, field) {
        this.fieldState.sms_partner_ids = this.fieldState.sms_partner_ids.filter((_, index) => index !== indexToRemove)
    }

    insertData(index) {
        index !== false ? this.fieldState.sms_partner_ids.splice(index + 1, 0, {value: []}) : this.fieldState.sms_partner_ids.push({value: []})
    }

    onSelectSms(ev) {
        if (!this.fieldState.sms_template) {
            this.fieldState.sms_template = {}
        }
        this.fieldState.sms_template.name = ev[0]?.display_name
        this.fieldState.sms_template.id = ev[0]?.id
    }

    getRecipientsIds(sms_partner_ids) {
        let sms_rec;
        let sms_to = [];
        sms_partner_ids ? sms_partner_ids.forEach((sms_partner_id) => {
            if (sms_partner_id.selectionType === 'variable') {
                this.updateUsedVariables(sms_partner_id.value.selectedVariable);
                sms_rec = this.props.variables.find(variable => variable.id === sms_partner_id.value.selectedVariable)
                if (sms_rec.modelName === 'res.users') {
                    if (sms_rec.variable_type === "recordset") {
                        sms_to.push(`*[rec.partner_id.id for rec in ${sms_rec.variable_name}]`)
                    } else {
                        sms_to.push(`${sms_rec.variable_name}.partner_id.id`)
                    }
                } else {
                    sms_to.push(`*${sms_rec.variable_name}.ids`)
                }
            } else if (sms_partner_id.selectionType === 'record') {
                this.updateUsedVariables(sms_partner_id.value.record);
                sms_rec = this.props.variables.find((variable) => variable.id === sms_partner_id.value.record)
                if (sms_partner_id.value.info?.fieldDef.relation === "res.users") {
                    sms_to.push(sms_rec.variable_name + '.' + sms_partner_id.value.path + '.partner_id.id')
                } else {
                    sms_to.push(sms_rec.variable_name + '.' + sms_partner_id.value.pathValue)
                }
            } else {
                sms_to.push('[' + sms_partner_id.value + ']')
            }
        }) : false
        return sms_to
    }

    generateCode() {
        const {sms_record, sms_template, sms_partner_ids, sms_isTemplate, sms_message} = this.fieldState
        // let modelRecord = sms_record
        const record = this.variables.find(variable => variable.id === sms_record.value)
        // const partner_selectionType = sms_partner_ids.selectionType
        const sms_to = this.getRecipientsIds(sms_partner_ids)
        let code = ``
        if (sms_isTemplate) {
            code = `template = env["sms.template"].browse(${sms_template.id})\n${record.variable_name}._message_sms_with_template(template=template,partner_ids=${sms_to})`
        } else {
            const processed_sms_message = (sms_message || "").replace(/\{\{\s*/g, '{').replace(/\s*\}\}/g, '}');
            code = `recipients =env["res.partner"].browse(${sms_to})\nsms_values = [{'body': f"""${processed_sms_message}""", 'number':recipient.phone,'partner_id':recipient.id} for recipient in recipients]\nrecords.env['sms.sms'].sudo().create(sms_values).send()`
        }
        return code || "";
    }

    validateForm() {
        const {sms_record, sms_template, sms_partner_ids, sms_isTemplate, sms_message, label} = this.fieldState;
        // Validation rules
        const errors = {};
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false
        // Validate sms_template: must not be empty
        sms_isTemplate ? !sms_template.name ? errors.sms_template = "Sms Template must be a non-empty. plz choose appropriate template and record" : false : false
        // Validate sms_record: must not be empty
        sms_template ? !sms_record ? errors.sms_template = "Sms Record must be a non-empty." : false : false
        // Validate sms_message must not be empty
        !sms_isTemplate ? !sms_message ? errors.sms_template = "Sms Message must be a non-empty." : false : false
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        // If no errors, form is valid
        return {isValid: true};
    }
}

SmsNode.template = "SmsNode";
SmsNode.components = {
    ...ConfigurationBase.components,
    Many2OneField,
    Record,
    Select,
    Input,
    Many2XAutocomplete,
    Dropdown,
    DropdownItem,
    TypeToggler,
    FieldTypeDropdown,
    CustomDropdown,
    MultiDataSelector,
};
