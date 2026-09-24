/** @odoo-module */
const {useState, Component, useEffect, onWillStart} = owl;
import {Record} from "@web/model/record";
import {CharField} from "@web/views/fields/char/char_field";
import {SelectionField} from "@web/views/fields/selection/selection_field";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {Many2ManyTagsField} from "@web/views/fields/many2many_tags/many2many_tags_field";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {MultiDataSelector} from "./subComponents/multiDataSelector";
import {VariableSelector} from "../Assists/variableSelector/variableSelector";
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {TypeToggler} from "../Assists/typeToggler/TypeToggler";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {
    DomainSelectorAutocomplete,
} from "@web/core/tree_editor/tree_editor_autocomplete";

export class FollowerNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.state = useState({
            filteredRecords: [],
        });
        onWillStart(async () => {
            await this.getFollowerRecords()
        })
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(label) {
        this.fieldState.label = label
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    setType(value) {
        this.fieldState.isRemoveFollower = value.value
    }

    get getOptions() {
        return [
            {label: "Add", value: false},
            {label: "Remove", value: true},
        ]
    }

    async getFollowerRecords() {
        const recordVariables = this.props.variables.filter(
            (variable) =>
                ["record", "recordset"].includes(variable.variable_type) && variable.modelId
        );

        let filteredRecords = [];
        if (recordVariables.length) {
            const modelIds = [...new Set(recordVariables.map((variable) => variable.modelId))];
            const models = await this.orm.read("ir.model", modelIds, ["is_mail_thread"]);
            const mailThreadModelIds = new Set(
                models.filter((model) => model.is_mail_thread).map((model) => model.id)
            );
            filteredRecords = recordVariables
                .filter((variable) => mailThreadModelIds.has(variable.modelId))
                .map((variable) => ({value: variable.id, label: variable.variable_name}));
        }
        this.state.filteredRecords = filteredRecords
    }

    getFollowerData() {
        !this.fieldState.followers ? this.fieldState.followers = [{value: []}] : false

        return this.fieldState.followers
    }

    get getAddFollowerTo() {
        return this.fieldState.follower_record?.value
    }

    setAddFollowerData(value, index) {
        const actualIndex = index ? index : 0
        this.fieldState.followers[actualIndex] = this.fieldState.followers[actualIndex] ? this.fieldState.followers[actualIndex] : {}
        this.fieldState.followers[actualIndex].value = value
    }

    updateAddFollowerRec(record) {
        this.fieldState.follower_record = this.state.filteredRecords.find((item) => item.value === record)
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
                        fieldDef,
                        allVariable: true,
                        variables: (this.props.variables || []).filter(variable => (variable.variable_type === "recordset" || variable.variable_type === "record") && variable.modelId === 85),
                    }
                }
            }
        } else if (selectionType === "record") {
            const fieldInfo = {
                resModel: this.modelState.model['model'],
                fieldDef: {type: 'many2one', relation: 'res.partner'}
            }
            return {
                component: RecordPathSelector,
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

    toggleIncludeVariable(type, index) {
        if (!this.fieldState.followers[index] || typeof this.fieldState.followers[index] !== 'object') {
            this.fieldState.followers[index] = {value: [], selectionType: type};
        } else if(![type, undefined].includes(this.fieldState.followers[index].selectionType)) {
            this.fieldState.followers[index] = {value: [], selectionType: type}
        }else this.fieldState.followers[index].selectionType = type
    }

    insertNewAddFollower() {
        this.fieldState.followers.push({value: []})
    }

    removeAddFollower(indexToRemove) {
        const filteredAddFollower = this.fieldState.followers.filter((_, index) => index !== indexToRemove)
        this.fieldState.followers = filteredAddFollower
    }

    getFollowerIds(followers) {
        let ids = []
        followers ? followers.forEach((follower) => {
            if (follower.selectionType === 'variable') {
                this.updateUsedVariables(follower.value.selectedVariable);
                ids.push(`*${follower.value.pathValue}`)
            } else if (follower.selectionType === 'record') {
                const variable = this.props.variables.find(variable => variable.id === follower.value.record)
                this.updateUsedVariables(follower.value.record);
                ids.push(`${variable.variable_name}.${follower.value.pathValue}`)
            } else {
                const value = follower.value
                ids.push(...value)
            }
        }) : false
        return ids
    }

    generateCode() {
        const {isRemoveFollower, followers, follower_record} = this.fieldState
        const record = this.variables.find(variable => variable.id === follower_record.value)
        const generateSubscribeCode = (partner_ids, variable, variableType) => {
            const code = variableType === "record"
                ? `${variable}.${!isRemoveFollower ? 'message_subscribe' : 'message_unsubscribe'}(partner_ids = [${partner_ids}])`
                : variableType === "recordset"
                    ? `for rec in ${variable}:\n\trec.${!isRemoveFollower ? 'message_subscribe' : 'message_unsubscribe'}(partner_ids = [${partner_ids}])`
                    : "";
            return code
        };
        const Partner_ids = this.getFollowerIds(followers)
        const variable = record.variable_name
        const variableType = record.variable_type
        return generateSubscribeCode(Partner_ids, variable, variableType)
    }

    validateForm() {
        const {followers, follower_record, isRemoveFollower} = this.fieldState;
        // Validation rules
        const errors = {};
        // Validate follower_record: must be a non-empty
        !follower_record ? errors.follower_record = `${isRemoveFollower ? "Remove Followers From" : "Add Followers To"} field must be a non-empty.` : false
        // Validate followers: must not be empty
        let isError = false
        followers.forEach(follower => (follower.value.length < 1) ? isError = true : false)
        isError ? errors.followers = `${isRemoveFollower ? "Follower to Remove" : "Follower To Add"} field must be a non-empty.` : false
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        // If no errors, form is valid
        return {isValid: true};
    }
}

FollowerNode.template = "FollowerNode";
FollowerNode.components = {
    ...ConfigurationBase.components,
    Record,
    Many2ManyTagsField,
    Dropdown,
    CharField,
    DropdownItem,
    MultiDataSelector,
    TypeToggler,
    CustomDropdown,
};