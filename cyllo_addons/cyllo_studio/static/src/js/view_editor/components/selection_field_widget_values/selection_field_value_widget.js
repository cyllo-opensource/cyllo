/** @odoo-module **/
import { Component, useState, useEffect, onWillUpdateProps } from "@odoo/owl";

/**
 * SelectionFieldValue
 *
 * Component representing a single selection value in a selection field.
 * Handles internal state of the value and notifies parent component on changes.
 *
 * Props:
 *  - value: Initial value of this selection
 *  - index: Index of the selection value in the parent list
 *  - changeValue: Function to call when this value changes
 */
export class SelectionFieldValue extends Component {

    setup() {
        this.state = useState({
            value: this.props.value,
        });

        useEffect(()=> {
            this.props.changeValue(this.props.index, this.state.value)
        }, ()=> [this.state.value])

        onWillUpdateProps((nextProps) => {
            this.state.value = nextProps.value
        });
    }

}

SelectionFieldValue.template = "cyllo_studio.SelectionFieldValue"