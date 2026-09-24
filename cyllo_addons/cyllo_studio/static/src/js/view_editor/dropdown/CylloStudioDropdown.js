/** @odoo-module */

/**
 * CylloStudioDropdown
 *
 * A reusable custom dropdown component for Odoo Studio with:
 * - Searchable input support
 * - Click-outside handling
 * - Positioning with `usePosition`
 * - Customizable width, height, and placeholder
 * - Callback support for option change
 *
 * Props:
 * - options (Array): List of option objects [{label, value}, ...]
 * - defaultValue (any): Initially selected value
 * - onChange (Function): Callback triggered when selection changes
 * - placeholder (String): Text shown when no value is selected
 * - searchable (Boolean): Whether dropdown is searchable
 * - width, maxHeight, disabled, noChange: UI customization
 */
import {Component, useState, useRef, onMounted, onWillUnmount, onWillUpdateProps, xml } from "@odoo/owl";
import {usePosition} from "@web/core/position_hook";

export class CylloStudioDropdown extends Component {
    static template = xml`<div class="custom-dropdown o-autocomplete" t-attf-class="{ state.isOpen? 'dropdown':'' }" t-ref="dropdown"
             t-att-style="'width: ' + props.width">
            <div t-on-click.stop="toggleDropdown" class="d-flex">
                <t t-if="props.searchable">
                    <input
                            t-if="props.searchable"
                            type="text"
                            style="color: #000000;"
                            class="o-autocomplete--input o_input input_drop"
                            t-model="state.searchTerm"
                            t-att-placeholder="displayValue"
                            t-att-value="displayValue"
                            t-att-title="displayValue"
                            t-on-input="onInput"
                            t-att-readonly="!state.isOpen"
                            t-ref="input"
                            t-att-disabled="props.disabled"
                            required="true"
                    />
                </t>
                <t t-else="" t-on-click.stop="toggleDropdown">
                    <span class="selected-text" t-att-title="displayValue">
                        <t t-esc="displayValue"/>
                    </span>
                </t>
                <i t-att-class="(state.isOpen ? 'fa fa-chevron-up' : 'fa fa-chevron-down') + (props.disabled ? ' cy-dropdown-icon--disabled' : '')" class="cy-dropdown-icon"/>
            </div>
            <t t-if="state.isOpen  and !props.disabled">
                <ul class="o-autocomplete--dropdown-menu ui-widget show"
                    t-att-style="'width: ' + props.width and !props.searchable ? 'margin-top: 13%;margin-left: 0;' : '' "
                    t-att-class="ulDropdownClass"
                    t-ref="recordList">
                    <li t-foreach="filteredOptions" t-as="option" t-key="option.value"
                        t-att-class="o_m2o_dropdown_option"
                        t-on-click.stop="() => this.selectOption(option)"
                        class="o-autocomplete--dropdown-item ui-menu-item d-block "
                    >
                        <a
                                class="dropdown-item ui-menu-item-wrapper text-truncate"
                                t-att-class="{ 'ui-state-active': checkActive(option) }"
                                t-att-title="option.label"
                        >
                            <span>
                                <t t-esc="option.label"/>
                            </span>
                        </a>
                    </li>
                    <li t-if="filteredOptions.length === 0" class="no-results">No results found</li>
                </ul>
            </t>

        </div>`
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

        onMounted(() => {
            document.addEventListener('click', this.handleOutsideClick, { capture: true });
        });

        onWillUnmount(() => {
            document.removeEventListener('click', this.handleOutsideClick, { capture: true });
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
        return this.inputRef.el;
    }

    get dropdownOptions() {
        return {
            position: "bottom-start",
        };
    }

    /**
     * Close dropdown if clicked outside the component.
     */
    handleOutsideClick = (event) => {
        if (this.dropdown.el && !this.dropdown.el.contains(event.target)) {
            this.state.isOpen = false;
        }
    }

    toggleDropdown() {
        if (this.props.disabled) return;
        this.state.isOpen = !this.state.isOpen;
    }
    checkActive(option) {
        return option.value === this.state.selectedOption?.value
    }

    /**
     * Handle option selection.
     * Updates state and triggers `onChange` callback.
     *
     * @param {Object} option - Selected option {label, value}
     */
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
        return this.state.selectedOption ? this.state.selectedOption.label : this.props.defaultValue;
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

    /**
     * Filter options by search term (case-insensitive).
     *
     * @returns {Array} Filtered options list
     */
    get filteredOptions() {
        if (!this.props.searchable || !this.state.searchTerm) {
            return this.props.options;
        }
        const searchTerm = this.state.searchTerm.toLowerCase();
        return this.props.options.filter(option =>
            option.label?.toLowerCase().includes(searchTerm)
        );
    }
}