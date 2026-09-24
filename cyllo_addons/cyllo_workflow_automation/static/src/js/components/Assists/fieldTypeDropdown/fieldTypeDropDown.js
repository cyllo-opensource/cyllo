/** @odoo-module */
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const DEFAULT_OPTIONS = [
    {
        value: 'static',
        label: 'Fixed',
    },
    {
        value: 'variable',
        label: 'Variable',
    },
    {
        value: 'record',
        label: 'Record',
    },
]

export class FieldTypeDropdown extends Component {
    /**
     * FieldTypeDropdown component allows users to select an option and view additional information
     * about the selected option in a tooltip.
     */
    static template = "FieldTypeDropdown";
    static components = { Dropdown, DropdownItem };
    static props = {
        currentLabel: { type: String },
        onSelected: { type: Function },
        options: { type: Object, optional: true },
    };

    static defaultProps = {
        options: DEFAULT_OPTIONS,
    }

    setup() {
        this.state = useState({
            options: this.props.options,
            showTooltip: false,
            tooltipPosition: { x: 0, y: 0 }
        });

        this.dropdownRef = useRef("dropdown");
        this.tooltipTimeout = null;
        onMounted(() => {
            document.addEventListener('click', this.handleOutsideClick);
        });

        onWillUnmount(() => {
            document.removeEventListener('click', this.handleOutsideClick);
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
            }
        });
    }
    handleOutsideClick = (event) => {
        if (this.dropdownRef.el && !this.dropdownRef.el.contains(event.target)) {
            this.state.showTooltip = false;
        }
    }

    getTooltipContent() {
        const currentOption = this.state.options.find(option => option.label === this.props.currentLabel);
        return currentOption ? currentOption.explanation : 'Select an option to see more information';
    }

    onOptionSelected(value) {
        const selectedOption = this.state.options.find(option => option.value === value);
        this.props.onSelected(value);
        this.showTooltip();
    }

    showTooltip() {
        if (this.tooltipTimeout) {
            clearTimeout(this.tooltipTimeout);
        }
        this.state.showTooltip = true;
        this.tooltipTimeout = setTimeout(() => {
            this.state.showTooltip = false;
            this.render();
        }, 3000);
    }

    toggleTooltip() {
        this.state.showTooltip = !this.state.showTooltip;
        if (this.state.showTooltip) {
            this.showTooltip();
        } else if (this.tooltipTimeout) {
            clearTimeout(this.tooltipTimeout);
        }
    }
}
