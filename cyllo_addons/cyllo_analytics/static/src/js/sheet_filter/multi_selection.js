/** @odoo-module **/
import { Component, useState, useRef } from "@odoo/owl";
import { usePosition } from "@web/core/position_hook";

export class MultiSelection extends Component {
    setup(){
        this.state = useState({
            open: false,
            selectedOptions: this.props.value || [],
            value: '',
            options: this.remOptions(this.props.value)
        })
        this.ref = useRef('input')
        usePosition("sourcesList", () => this.ref.el, {
            position: "bottom-start",
        });
    }
    remOptions(opts = []){
        // Remaining options
        return this.props.options.filter(opt => !opts.includes(opt[0]))
    }
    onOptionClick(option){
        if (this.state.selectedOptions.includes(option[0])) return
        this.state.selectedOptions.push(option[0])
        this.props.onClick(this.state.selectedOptions)
    }
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
            this.state.options = this.remOptions(this.state.selectedOptions).filter(field => {
                return field.label.includes(this.state.value)
            })
        } else {
            this.state.options = this.remOptions(this.state.selectedOptions)
        }
        this.state.open = !!this.remOptions(this.state.selectedOptions).length
    }
    removeSelection(value){
        var index = this.state.selectedOptions.indexOf(value)
        this.state.selectedOptions.splice(index, 1)
    }
}

MultiSelection.template = "MultiSelection"