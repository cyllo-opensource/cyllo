/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";

export class RenameAutomationDialog extends Component {
    setup() {
        this.state = useState({
            name: this.props.initialName || "",
        });
    }

    get confirmDisabled() {
        return !this.state.name.trim();
    }

    onInput(ev) {
        this.state.name = ev.target.value;
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.onConfirm();
        }
    }

    onConfirm() {
        const name = this.state.name.trim();
        if (!name) {
            return;
        }
        this.props.onConfirm(name);
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }
}

RenameAutomationDialog.template = "RenameAutomationDialog";
RenameAutomationDialog.components = { Dialog };
RenameAutomationDialog.props = {
    close: Function,
    title: { type: String, optional: true },
    initialName: { type: String, optional: true },
    onConfirm: Function,
};
