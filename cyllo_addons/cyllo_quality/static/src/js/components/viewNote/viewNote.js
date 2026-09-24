/** @odoo-module */
import { registry } from '@web/core/registry';
import { Component, useState, onWillStart } from "@odoo/owl";

const MAX_LEN = 20;

export class ViewNote extends Component {
    static template = 'viewNote';

    setup() {
        // Ensure value exists and is an array
        this.state = useState({
            endIndex: 0,
            isExpanded: false,
        });
        onWillStart(() => {
            const validLength = this.value.length;
            this.state.endIndex = (validLength - 1 < MAX_LEN) ? validLength - 1 : MAX_LEN
        })
    }

    get value() {
        return this.props.record?.data?.[this.props.name] || "";
    }

    get collapsedValue() {
        return this.value.slice(0, this.state.endIndex);
    }

    handleOnClickExpand() {
        this.state.endIndex = this.value.length -1
        this.state.isExpanded = true
    }
}

export const viewNote = {
    component: ViewNote,
};

registry.category("fields").add("view_qc_note", viewNote);
