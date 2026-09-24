/** @odoo-module */

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const DEFAULT_VALUE = {
    value: 0,
    unit: { id: false, name: "" },
};

export class MeasureUOM extends Component {
    static template = "cyllo_quality.measureUOM";

    setup() {
        this.orm = useService("orm");
        this.root = useRef("root");

        this.state = useState({
            value: this.props.record.data[this.props.name] || 0,
            uom: this.props.record.data.uom_id || false,
            uomOptions: [],
            uomInput: this.props.record.data.uom_id ? this.props.record.data.uom_id[1] : '',
            showUomValues: false,
            uomValues: [],
            editMode: false,
        });

        // Fetch UOMs at the start
        onWillStart(() => this.fetchUOMs());
    }
    addGlobalListener() {
        document.addEventListener('click', this.globalClickListener.bind(this));
    }
    globalClickListener(ev) {
        if (this.root.el === null || this.root.el === undefined) {
            return;
        }

        else if (this.root.el.contains(ev.target)) {
            return;
        }


        this.state.editMode = false;
        document.removeEventListener('click', this.globalClickListener.bind(this));
    }
    handleClick() {
        if (this.props.readonly) return;
        this.addGlobalListener()
        this.state.editMode = true;
    }

    get defaultValue() {
        return {
            value: 0,
            unit: { id: false, name: "" },
        };
    }

    get jsonValue() {
        return this.props.record.data[this.props.name] || this.defaultValue;
    }

    // Add readonly check
    get isReadonly() {
        return this.props.readonly;
    }

    // Fetch UOMs using optimized search_read
    async fetchUOMs() {
        if (!this.state.uomOptions.length) {
            this.state.uomOptions = await this.orm.call(
                "uom.uom",
                "search_read",
                [[], ['id', 'name']]
            );
        }
    }

    // Handle input value change for measurement
    onInputChange(ev) {
        if (this.isReadonly) return;
        const newValue = parseFloat(ev.target.value);
        this.state.value = isNaN(newValue) ? 0 : newValue;
        this.updateRecord();
    }

    // Handle UOM dropdown change
    onUOMChange(ev) {
        if (this.isReadonly) return;
        const newUomId = parseInt(ev.target.value, 10);
        if (newUomId) {
            const unit = this.state.uomOptions.find(uom => uom.id === newUomId);
            const value = { ...this.jsonValue, unit };
            this.updateRecord(value);
        }
    }

    // Update the record with the current state
    updateRecord(value = this.jsonValue) {
        if (this.isReadonly) return;
        this.props.record.update({

            [this.props.name]: value,
        });
    }
    get dependField() {

        return this.props.fieldName ? this.props.record.data[this.props.fieldName] : true;
    }
}

MeasureUOM.props = {
    ...standardFieldProps,
    fieldName: { type: String, optional: true },
};

export const measureUOM = {
    component: MeasureUOM,
    supportedTypes: ["json"],
    extractProps: (fieldInfo, dynamicInfo) => ({
        fieldName: fieldInfo.options?.fieldName,
    }),
};

registry.category("fields").add("MeasureUOM", measureUOM);