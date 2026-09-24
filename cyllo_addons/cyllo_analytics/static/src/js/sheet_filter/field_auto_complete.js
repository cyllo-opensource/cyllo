/** @odoo-module **/
import { DomainCreator } from "./domain_creator"
import { usePosition } from "@web/core/position_hook";
import { session } from "@web/session";
import { Component, useState, useRef } from "@odoo/owl";

/**
 * FieldAutoComplete class for handling autocomplete functionality in a component.
 * @class
 * @extends {Component}
 */
export class FieldAutoComplete extends Component {
    /**
     * Initializes the FieldAutoComplete class.
     * @function
     */
    setup(){
        this.state = useState({
            data: [],
            domain: [],
            value: false,
            open: false,
            id: 0
        })
        const extractFieldName = (expression) => {
            const regex = /(.+?)\s*->>\s*'.*'/;
            const match = expression.match(regex);
            return match ? match[1].trim() : expression.trim();
        }

        if (this.props.filterDomain){
            this.props.filterDomain.forEach(filter => {
                var mainDomainVal = this.props.options.find(field => field.name === extractFieldName(filter.field) && field.model.table === filter.table)
                var domainVal = {...mainDomainVal}
                var value = filter.rhs
                if (['datetime','date'].includes(domainVal.field_type)) {
                    const { DateTime } = luxon;
                    const { tz: zone } = session.user_context
                    value = DateTime.fromISO(value.replace(/^'|'$/g, ''), { zone });
                }
                else if(domainVal.field_type == 'selection' || domainVal.field_type == 'boolean'){
                    value = value.replace(/^'|'$/g, '')
                }
                domainVal.value = value
                domainVal.operator = filter.operator
                domainVal.id = this.state.id ++
                this.state.domain.push(domainVal)
            })
        }
        this.ref = useRef('input')
        usePosition("sourcesList", () => this.ref.el, {
            position: "bottom-start",
        });
    }
    /**
     * Handles the blur event on the input.
     * @function
     */
    onInputBlur(){
        this.state.open = false
    }
    /**
     * Handles the input event on the input.
     * @param {Event} e - The input event.
     * @function
     */
    onInput(e){
        if(this.state.value){
            this.state.data = this.props.options.filter(field => {
                return field.label.toLowerCase().includes(this.state.value.toLowerCase())
            })
        } else {
            this.state.data = this.props.options
        }
        this.state.open = !!this.state.data.length
    }
    /**
     * Handles the click event on an option.
     * @param {Object} option - The selected option.
     * @function
     */
    onOptionClick(option){
        var opt = {...option, id: this.state.id++}
        this.state.domain.push(opt)
        this.state.open = false
        this.state.value = false
    }
    onClickRemove(props){
        var { label, value, name, operator } = props.domain
        const data = this.state.domain.filter(item => !(item.name === name && item.operator === operator && JSON.stringify(item.value) === JSON.stringify(value)));
        this.state.domain = data
        this.props.onClickRemove(props)
    }
}
FieldAutoComplete.template = "FieldAutoComplete"
FieldAutoComplete.components = { DomainCreator }