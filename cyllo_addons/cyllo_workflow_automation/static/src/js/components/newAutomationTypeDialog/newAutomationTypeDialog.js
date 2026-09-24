/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class NewAutomationTypeDialog extends Component {
    onChoose(isReusable) {
        this.props.onSelect(isReusable);
        this.props.close();
    }

    onDiscard() {
        if (this.props.onDiscard) {
            this.props.onDiscard();
        }
        this.props.close();
    }
}

NewAutomationTypeDialog.template = "NewAutomationTypeDialog";
NewAutomationTypeDialog.components = { Dialog };
NewAutomationTypeDialog.props = {
    close: Function,
    title: { type: String, optional: true },
    onSelect: Function,
    onDiscard: { type: Function, optional: true },
};
