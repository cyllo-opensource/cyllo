/** @odoo-module **/
import { Component, useState, useRef, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { usePosition } from "@web/core/position_hook";

export class MultiSelectDropDown extends Component {
    static template = "cyllo_studio.MultiSelectDropDown";
    static components = { TagsList };
    static props = {
        selectedValues: { type: Array, optional: true },
        allValues: { type: Object, optional: false },
        onUpdate: { type: Function, optional: false },
        class: { type: String, optional: true },
        style: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            isOpen: false,
            searchTerm: "",
            selectedValues: this.props.selectedValues || [],
            allValues: this.props.allValues,
        });
        this.dropdownRef = useRef("dropdown");
        this.inputRef = useRef("searchInput");

        onMounted(() => {
            document.addEventListener("click", this.handleOutsideClick, { capture: true });
        });
        onWillUnmount(() => {
            document.removeEventListener("click", this.handleOutsideClick, { capture: true });
        });

        usePosition("recordList", () => this.dropdownRef.el, { position: "bottom-start" });

        onWillUpdateProps((nextProps) => {
            this.state.allValues = nextProps.allValues;
            this.state.selectedValues = nextProps.selectedValues || [];
        });
    }

    handleOutsideClick = (ev) => {
        if (this.dropdownRef.el && !this.dropdownRef.el.contains(ev.target)) {
            this.state.isOpen = false;
            this.state.searchTerm = "";
        }
    };

    openDropdown() {
        this.state.isOpen = true;
    }

    toggleDropdown() {
        this.state.isOpen = !this.state.isOpen;
        if (!this.state.isOpen) {
            this.state.searchTerm = "";
        }
    }

    onInput(ev) {
        this.state.searchTerm = ev.target.value;
        this.state.isOpen = true;
    }

    onSelected(key) {
        const updated = [...this.state.selectedValues, key];
        this.state.searchTerm = "";
        this.props.onUpdate(updated);
    }

    getTagProps(key) {
        return {
            id: key,
            text: this.state.allValues[key],
            onDelete: () => this.deleteTag(key),
        };
    }

    deleteTag(key) {
        this.props.onUpdate(this.state.selectedValues.filter((k) => k !== key));
    }

    get tags() {
        return this.state.selectedValues.map((key) => this.getTagProps(key));
    }

    get filteredKeys() {
        const term = this.state.searchTerm.toLowerCase();
        return Object.keys(this.state.allValues).filter((k) => {
            if (this.state.selectedValues.includes(k)) return false;
            if (!term) return true;
            return (this.state.allValues[k] || "").toLowerCase().includes(term);
        });
    }
}
