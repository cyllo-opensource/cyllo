/** @odoo-module **/
import { Component, useState, useEffect, onMounted } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { MultiSelection } from "@cyllo_analytics/js/sheet_filter/multi_selection"

/**
 * DomainCreator class for creating domain conditions for the sheet filter.
 * @class
 * @extends {Component}
 */
export class DomainCreator extends Component {
    /**
     * Initializes the DomainCreator class.
     * @function
     */
    setup(){
        this.field = this.props.domain
        this.options = ["=", "!=", ">=", "<=", ">", "<"]
        this.specialOptions = {
            selection: ["IN", "NOT IN"],
        }
        this.state = useState({
            operator: "=" ,
            value: this.Value,
            textVal: false,
            multiValue: this.multiValue
        })
        onMounted(() => {
            this.state.value = this.special.includes(this.field.field_type) ? this.field.value : this.state.value
            this.state.operator = this.field.operator ? this.field.operator : this.state.operator
        })
        useEffect(() => {
            if(this.options.includes(this.state.operator) && this.state.multiValue.length){
                this.state.value = this.state.multiValue[0]
                this.state.multiValue = []
                return
            } else  if(!this.options.includes(this.state.operator) && !this.state.multiValue.length){
                this.state.multiValue = this.multiValue
                this.state.value = this.arrayToTupleString(this.state.multiValue)
                return
            }
            if(!this.state.value){
                this.state.value = this.Value
                return
            }
            let val = this.options.includes(this.state.operator) ? `'${this.state.value}'` : this.state.value
            let value = this.nonStringTypes(this.field.field_type) ? this.state.value : val
            let jsonData = this.field.is_json ? "->> 'en_US'" : ''
            let domain = `${this.field.model.table}.${this.field.name} ${jsonData} ${this.state.operator} ${value}`
            this.props.addToDomain(domain, this.props.index)

        }, () => [this.state.operator, this.state.value])
    }
    get multiValue(){
        let operator = this.field.operator || "="
        if(this.options.includes(operator)) return []
        return this.Value.match(/\b\w+\b/g)
    }
    arrayToTupleString(tupleArray) {
        var tupleString = "(" + tupleArray.map(element => "'" + element + "'").join(', ') + ")";
        return tupleString;
    }
    getOptions(type){
        if(this.specialOptions[type]){
            return [...this.options, ...this.specialOptions[type]]
        }
        return this.options
    }
    onDeleteDomain(){
        this.props.remove(this.props)
    }
    /**
     * Checks if the field type is non-string.
     * @param {string} type - The type of the field.
     * @returns {boolean} - True if the field type is non-string.
     * @function
     */
    nonStringTypes(type){
        return ["boolean", "many2one", "integer", "float", "monetary"].includes(type)
    }
    /**
     * Gets the default value for the field.
     * @member {any}
     * @readonly
     */
    get Value () {
        var value = this.field.value ? this.field.value : null
        if (!value && this.field.field_type == "selection") {
            value = this.field.selection[0][0]
        }
        return value
    }
    /**
     * Gets the special field types.
     * @member {Array}
     * @readonly
     */
    get special(){
        return ["selection", "boolean", "date", "datetime"]
    }
    /**
     * Sets the value for the state.
     * @param {any} value - The value to be set.
     * @function
     */
    setValue(value){
        this.state.value = value
    }
    /**
     * Handles the change event for selection fields.
     * @param {Event} ev - The change event.
     * @function
     */
    selectionChange(ev){
        this.setValue(ev.target.value)
    }
    /**
     * Handles the change event for boolean fields.
     * @param {Event} ev - The change event.
     * @function
     */
    boolChange(ev){
        const { selectedOptions } = ev.target
        var value = selectedOptions[0].value == "FALSE" ? false : true
        this.setValue(value)
    }
    /**
     * Handles the change event for the operator.
     * @param {Event} ev - The change event.
     * @function
     */
    onChangeOperator(ev){
        this.state.operator = ev.target.value
    }
    onAddValue(val){
        this.state.multiValue = val
        this.setValue(this.arrayToTupleString(this.state.multiValue))
    }
}
DomainCreator.template = "DomainCreator"
DomainCreator.components = { DateTimeInput, MultiSelection }