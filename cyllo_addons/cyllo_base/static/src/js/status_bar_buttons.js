/** @odoo-module **/
import { StatusBarButtons } from "@web/views/form/status_bar_buttons/status_bar_buttons";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

export class CylloStatusBarButtons extends StatusBarButtons {
    setup() {
        super.setup();
        this.dropdownState = useState({ isOpen: false });
    }

    toggleDropdown() {
        this.dropdownState.isOpen = !this.dropdownState.isOpen;
    }

    closeDropdown() {
        this.dropdownState.isOpen = false;
    }

    get _limit() {
        const val = parseInt(this.props.buttonLimit, 10);
        return (!isNaN(val) && val > 0) ? val : null;
    }

    get primarySlotNames() {
        const limit = this._limit;
        if (!limit) {
            return this.visibleSlotNames;
        }
        return this.visibleSlotNames.slice(0, limit);
    }

    get extraSlotNames() {
        const limit = this._limit;
        if (!limit) {
            return [];
        }
        return this.visibleSlotNames.slice(limit);
    }

    get hasExtraButtons() {
        return this.extraSlotNames.length > 0;
    }
}

CylloStatusBarButtons.template = "cyllo_base.StatusBarButtons";
CylloStatusBarButtons.components = {
    ...StatusBarButtons.components,
    Dropdown,
    DropdownItem,
};
CylloStatusBarButtons.props = {
    ...StatusBarButtons.props,
    buttonLimit: { type: [Number, String], optional: true },
};

patch(FormCompiler.prototype, {
    compileHeader(el, params) {
        const statusBar = super.compileHeader(el, params);

        const buttonLimit = el.getAttribute("button_limit");
        if (buttonLimit) {
            // Walk the compiled output to find the StatusBarButtons element
            // and inject the buttonLimit prop.
            const walk = (node) => {
                if (!node) return null;
                if (node.nodeName === "StatusBarButtons") return node;
                for (const child of (node.childNodes || [])) {
                    const found = walk(child);
                    if (found) return found;
                }
                return null;
            };
            const statusBarButtons = walk(statusBar);
            if (statusBarButtons) {
                statusBarButtons.setAttribute("buttonLimit", buttonLimit);
            }
        }

        return statusBar;
    }
});

FormRenderer.components = {
    ...FormRenderer.components,
    StatusBarButtons: CylloStatusBarButtons,
};
