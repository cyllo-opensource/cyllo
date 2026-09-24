/** @odoo-module */
import {Component, useState, useRef, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import {usePosition} from "@web/core/position_hook";
import {useAutofocus, useForwardRefToParent, useService} from "@web/core/utils/hooks";

export class CustomDropdown extends Component {
    /**
     * CustomDropdown is a component that displays a dropdown list of options
     * that users can select from. It supports search functionality and can
     * handle various props to customize its behavior and appearance.
     */
    static template = "CustomDropdown";
    static props = {
        options: {type: Array},
        defaultValue: { optional: true},
        onChange: {type: Function, optional: true},
        placeholder: {type: String, optional: true, default: "Select..."},
        searchable: {type: Boolean, optional: true, default: false},
        width: {type: String, optional: true, default: "250px"},
        maxHeight: {type: String, optional: true, default: "200px"},
        disabled: {type: Boolean, optional: true, default: false},
        noChange: {type: Boolean, optional: true, default: false},
    };

    setup() {
        this.state = useState({
            isOpen: false,
            options: this.props.options,
            selectedOption: this.props.options.find(option => option.value === this.props.defaultValue) || null,
            searchTerm: "",
        });
        this.dropdown = useRef("dropdown");
        this.triggerRef = useRef("trigger");
        onMounted(() => {
            document.addEventListener('click', this.handleOutsideClick);
        });
        onWillUnmount(() => {
            document.removeEventListener('click', this.handleOutsideClick);
        });
        this.inputRef = useRef("input");
        usePosition("recordList", () => this.targetDropdown, this.dropdownOptions);
        onWillUpdateProps((props) => {
            if (!props.noChange)
                this.state.selectedOption = props.options?.find(option => option.value === props.defaultValue) || null;
        })
    }

    get getIsOpen(){
        return this.state.isOpen;
    }

    get targetDropdown() {
        return this.inputRef.el || this.triggerRef.el;
    }

    get dropdownOptions() {
        return {
            position: "bottom-start",
        };
    }

    handleOutsideClick = (event) => {
        if (this.dropdown.el && !this.dropdown.el.contains(event.target)) {
            this.state.isOpen = false;
        }
    }

    toggleDropdown() {
        this.state.isOpen = !this.state.isOpen;
    }
    checkActive(option) {
        return option.value === this.state.selectedOption?.value
    }

    selectOption(option) {
        this.state.selectedOption = option;
        this.state.isOpen = false;
        this.state.searchTerm = "";
        if (this.props.onChange) {
            this.props.onChange(option.value);
        }
    }

    onInput() {
        if (!this.state.isOpen) {
            this.state.isOpen = true;
        }
    }

    get displayValue() {
            return this.state.selectedOption ? this.state.selectedOption.label : this.props.placeholder;
    }

    get ulDropdownClass() {
        let classList = "";
        if (this.state.isOpen) {
            classList += " dropdown-menu ui-autocomplete";
        } else {
            classList += " list-group";
        }
        return classList;
    }

    get filteredOptions() {
        if (!this.props.searchable || !this.state.searchTerm) {
            return this.props.options || [];
        }
        const searchTerm = this.state.searchTerm.toLowerCase();
        return (this.props.options || []).filter(option =>
            option.label.toLowerCase().includes(searchTerm)
        );
    }
}
