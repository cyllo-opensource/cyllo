/** @odoo-module */
const { useState, Component, useEffect, onWillStart } = owl;
import { Record } from "@web/model/record";
import { CharField } from "@web/views/fields/char/char_field";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { ConfigurationBase } from "../configurationBase/configurationBase.js"
import { TypeToggler } from "../Assists/typeToggler/TypeToggler";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { Input } from "@web/core/tree_editor/tree_editor_components";

const EXCEPTION_IMPORT = 'from odoo.exceptions import'
const ERRORS = {
    'UserError': 'UserError',
    'ValidationError': 'ValidationError',
    'AccessError': 'AccessError',
    'MissingError': 'MissingError',
    'AccessDenied': 'AccessDenied',
    'CacheMiss': 'CacheMiss',
    'RedirectWarning': 'RedirectWarning',
}

export class WarningNode extends ConfigurationBase {
    get recordProps() {
        const warning_text = {
             type: "char",
             string: "Warning Text",
        }
        const warning = {
             type: "selection",
             string: "Warning",
        }
        const label = {
            type: "char",
            string: "Label"
        }
        const warning_type = {
            type: "char",
            string: "Warning Type",
        }
        const notification_type = {
            type: "char",
            string: "Notification Type",
        }
        const notification_title = {
            type: "char",
            string: "Notification Title",
        }
        const notification_sticky = {
            type: "boolean",
            string: "Sticky",
        }
        const fields = {
             warning_text,
             warning,
             label,
             warning_type,
             notification_type,
             notification_title,
             notification_sticky,
        }
         return {
             mode: "edit",
             onRecordChanged: (record, changes) => {
                for (var key in changes){
                    this.fieldState[key] = changes[key]
                }
             },
             resModel: "node.struct",
             resId: this.props.id,
             fieldNames: fields,
             activeFields: fields,
         };
    }

    onChangeLabel(label){
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL",{label,nodeId});
    }

    get types() {
        return [
            {label: "Error", value: "error"},
            {label: "Notification", value: "notification"},
        ]
    }

    get options() {
        return [
            { label: "Info", value: "info" },
            { label: "Success", value: "success" },
            { label: "Warning", value: "warning" },
            { label: "Danger", value: "danger" },
        ]
    }

    handleUpdate(value, key) {
        this.fieldState[key] = value;
    }

    generateCode() {
        if (this.fieldState.warning && this.fieldState.warning_text && this.fieldState.warning_type === "error") {
            this.props.updateImports({ parent: EXCEPTION_IMPORT, child: this.fieldState.warning, nodeId: this.props.id })
            return `raise ${this.fieldState.warning}("${this.fieldState.warning_text}")`
        }
        else if (this.fieldState.warning_type === "notification") {
            const sticky = this.fieldState.notification_sticky === true ? 'True' : 'False';
            return `action = {
'type': 'ir.actions.client',
'tag': 'display_notification',
'params': { 
    'title': '${this.fieldState.notification_title}',
    'type': '${this.fieldState.notification_type}',
    'message': '${this.fieldState.warning_text}',
    'sticky': ${sticky},
    'next': {'type': 'ir.actions.act_window_close'},
    },
}
channel = 'bus_do_action'
message = {
    "channel": channel,
    "auth": {
        "user": env.user.id
    },
    "action": action
}
env['bus.bus']._sendone(channel, "notification", message)
`
        }
        return ""
    }

    validateForm() {
        const { warning, warning_text, label, notification_type, notification_title, warning_type  } = this.fieldState;
        const errors = {};

        if (!label || label === '' || label.trim() === "") {
            errors.label = "Label must be a non-empty string.";
        }
        if (warning_type === "error"){
            if (!warning) {
                errors.warning = "Please select warning.";
            }
        } else {
            if (!notification_type) {
                errors.notification_type = "Please select type.";
            }
            if (!notification_title || notification_title === '' || notification_title.trim() === "") {
                errors.notification_title = "Title must be a non-empty string.";
            }
        }

        if (!warning_text || warning_text === "" || warning_text.trim() === "") {
            errors.warning_text = "Set Warning text.";
        }

        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }

        return { isValid: true };
    }
}

WarningNode.template = "WarningNode";
WarningNode.components = { ...ConfigurationBase.components, SelectionField, CharField, Record, TypeToggler, CustomDropdown, Input };