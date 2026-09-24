/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useInputField} from "@web/views/fields/input_field_hook";

const {Component, useRef} = owl;

/**
 * We define this module for the function of creating a time picker widget
 *
 */
export class FieldTimePicker extends Component {
    setup() {
        this.input = useRef('input_time');
        this.closeEventListener = false;
        useInputField({getValue: () => this.props.record.data[this.props.name] || "", refName: "input_time"});
    }

    onBlur() {
        /**
         * Handle the blur event for the timepicker input field.
         *
         * This function is responsible for handling the blur event on the timepicker input field.
         * It checks if the close button is present in the timepicker, and if so, it adds a click event
         * listener to it to handle the closing of the timepicker.
         *
         * @returns {void}
         */
        const root = this.input.el.ownerDocument
        const closeTime = root.querySelector('.wickedpicker__close');
        if (closeTime) {
            this.closeEventListener ? '' : closeTime.addEventListener('click', this.closeHandler.bind(this))
            this.closeEventListener = true;
        }
    }

    closeHandler() {
        /**
         * Handle the click event for closing the timepicker.
         *
         * This function is responsible for handling the click event on the close button of the timepicker.
         * It updates the associated record's field with the value from the timepicker input field, if available.
         *
         * @returns {void}
         */
        this.props.record.update({[this.props.name]: this.input.el?.value})
    }

    /**
     * Click function to show the timepicker
     */
    _onClickTimeField(event) {
        const value = this.input.el.value
        $(this.input.el).wickedpicker({
            title: 'Schedule Dark Mode',
            now: event.value,
            twentyFour: false, // Set to false for twelve-hour clock format
            closeOnClickOutside: true,
            onExternalClick: this.closeHandler.bind(this),
            date: value
        });
    }
}

// Set the template for the FieldTimePicker component
FieldTimePicker.template = 'FieldTimePicker';
export const fieldTimePicker = {
    component: FieldTimePicker,
    supportedTypes: ["char"],
};
// Add the timepicker to the fields category
registry.category("fields").add("timepicker", fieldTimePicker);