/** @odoo-module **/
import { DomainCreator } from "./domain_creator"
import { usePosition } from "@web/core/position_hook";
import { Component, useState, useRef } from "@odoo/owl";
import { FieldAutoComplete } from "@cyllo_analytics/js/sheet_filter/field_auto_complete"

/**
 * FieldAutoCompleteGlobal class extending FieldAutoComplete for handling global autocomplete functionality.
 * @class
 * @extends {FieldAutoComplete}
 */
export class FieldAutoCompleteGlobal extends FieldAutoComplete {
    /**
     * Initializes the FieldAutoCompleteGlobal class.
     * @function
     */
    setup(){
        super.setup();
        this.state.value = this.props.value && this.props.value.label
    }
    /**
     * Handles the click event on an option, triggering a global click event.
     * @param {Object} option - The selected option.
     * @function
     */
    onOptionClick(option){
        this.props.onClick && this.props.onClick(option, this.props.filter)
        this.state.value = option.label
        this.state.open = false
    }
    static defaultProps = {
        defaultOption: false
    }
}

FieldAutoCompleteGlobal.template = "FieldAutoCompleteGlobal"
FieldAutoCompleteGlobal.components = {}