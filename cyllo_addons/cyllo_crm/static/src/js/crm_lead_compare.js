/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DropdownWidget extends Component {
    static template = "cyllo_crm.dropdown_Widget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        const initialValue = this.props.record.data[this.props.name] || "";
        this.state = useState({
            selectedValue: initialValue,
            availableOptions: this.getOptionsFromField(initialValue)
        });
        this.selectValue = this.selectValue.bind(this);
    }

    getOptionsFromField(value) {

        const fieldOptions = value ? value.split(", ") : [];
        return fieldOptions;
    }

    selectValue(value) {
        this.state.selectedValue = value;
        if (!this.state.availableOptions.includes(value)) {
            this.state.availableOptions.push(value);
        }
        this.props.record.update({ [this.props.name]: value });
    }

    get values() {
        // Reorder the options to put selected value first
        const options = [...this.state.availableOptions];
        if (this.state.selectedValue && options.includes(this.state.selectedValue)) {
            // Remove the selected value from its current position
            const index = options.indexOf(this.state.selectedValue);
            options.splice(index, 1);
            // Add it to the beginning
            options.unshift(this.state.selectedValue);
        }
        return options;
    }
}

export const dropdownWidget = {
    component: DropdownWidget,
    supportedTypes: ["char", "text"],
};

registry.category("fields").add("dropdown_widget", dropdownWidget);