/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { CustomDropdown } from "../../components/Assists/dropdown/CustomDropdown"
import { Component, useState, useEffect } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { formatText } from "@web/views/fields/formatters";
import { cookie } from "@web/core/browser/cookie";

export class CharSelection extends Component {
    static template = "cyllo_workflow_automation.CharSelection";
    static props = {
        ...standardFieldProps,
    };

    static components = { CustomDropdown };

    setup() {
        this.state = useState({ functions: [], selectedFunction: this.props.record.data[this.props.name] });
        this.orm = this.env.services.orm
        useEffect((model) => {
            if(model) {
                this.fetchFunctions(model);
            }
        }, () => [this.props.record.data.model_id]);
    }

    async fetchFunctions(model) {
        this.state.functions = await this.env.services.orm.call("work.auto", "parse_view_and_fetch_functions", [], {model_id: model[0]});
    }

    get functions() {
        return this.state.functions.map(fn => ({
            value: fn.button_function,
            label: fn.button_string,
            function_name: fn.button_function
        }));
    }

    get defaultValue () {
        return this.state.selectedFunction || ""
    }

    get disabled (){
        return this.env.model.config.mode !== "edit"
    }

    onChangeFunction(value) {
        this.handleChange(value);
    }

     handleChange(editedValue) {
        if (this.state.selectedFunction !== editedValue) {
            this.state.selectedFunction = editedValue;
            this.commitChanges();
        }
    }

    commitChanges() {
        this.props.record.update({ [this.props.name]: this.state.selectedFunction });
    }
}

export const charSelection = {
    component: CharSelection,
    supportedTypes: ["char"],
};

registry.category("fields").add("charSelection", charSelection);
