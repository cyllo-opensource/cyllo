/** @odoo-module */

import { Component } from "@odoo/owl";

export class TypeToggler extends Component {
    /**
     * TypeToggler is a component that allows users to toggle between different types or options.
     */
    static template = "TypeToggler";
    static props = {
        options: { type: Array },
        value: { optional: true },
        updateValue: { type: Function },
        width: { type: Number, optional: true },
    };
    get containerStyle() {
        return `width: ${this.props.width || 25}%;`;
    }

    get itemStyle() {
        return `width: ${100 / this.props.options.length}%;`;
    }

    toggleInput(option) {
        this.props.updateValue(option);
    }

    /**
     * Checks if the provided option is currently active (selected).
     * @param {Object} option - The option to check
     * @returns {boolean} True if the option is active, otherwise false
     */
    isActive(option) {
        return option.value === this.props.value;
    }
}
