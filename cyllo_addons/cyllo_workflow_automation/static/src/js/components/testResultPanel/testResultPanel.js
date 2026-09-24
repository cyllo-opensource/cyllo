/** @odoo-module */
import { Component } from "@odoo/owl";

export class TestResultPanel extends Component {
    get hasErrors() {
        return Boolean(this.props.summary?.error);
    }

    get hasWarnings() {
        return Boolean(this.props.summary?.warning);
    }

    toggleMinimize() {
        if (this.props.onToggleMinimize) {
            this.props.onToggleMinimize();
        }
    }
}

TestResultPanel.template = "cyllo_workflow_automation.TestResultPanel";
TestResultPanel.props = {
    visible: { type: Boolean },
    minimized: { type: Boolean, optional: true },
    summary: { type: Object, optional: true },
    results: { type: Array, optional: true },
    onToggleMinimize: { type: Function, optional: true },
};
