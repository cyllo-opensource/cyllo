/** @odoo-module */
import {Record} from "@web/model/record";
import {CharField} from "@web/views/fields/char/char_field";
import {ConfigurationBase} from "../configurationBase/configurationBase.js";
import {AceField} from "@web/views/fields/ace/ace_field";
import {CodeEditor} from "@web/core/code_editor/code_editor";

export class CodeNode extends ConfigurationBase {
    get recordProps() {
        const code_code = {
            type: "char",
            string: "Code",
        }
        const label = {
            type: "char",
            string: "Label"
        }

        const fields = {
            code_code,
            label
        }

        return {
            mode: "edit",
            onRecordChanged: (record, changes) => {
                for (var key in changes) {
                    this.fieldState[key] = changes[key]
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    get variables() {
        return this.props.variables;
    }

    copyToClipboard(ev, text) {
        // Check if the Clipboard API is available
        if (navigator.clipboard) {
            // Request permission to write to the clipboard
            navigator.clipboard.writeText(text)
                .then(() => {
                    this.displayToast('Text copied to clipboard');
                })
                .catch((err) => {
                    console.error('Failed to copy text: ', err);
                });
        } else {
            console.error('Clipboard API not available');
        }
    }

    displayToast(message) {
        const modalBody = this.modalRef.el;
        const toast = this.toastRef.el;
        toast.classList.remove('d-none');
        toast.textContent = message;
        modalBody.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('d-none');
        }, 1000);
    }

    onChangeLabel(label) {
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    generateCode() {
        const code = this.fieldState.code_code
        return code || ""
    }

    validateForm() {
        const {code_code, label} = this.fieldState;
        // Validation rules
        const errors = {};
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false

        // Validate code_code: must be a non-empty string
        !code_code ? errors.code_code = "Code must be a non-empty." : false

        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }

        // If no errors, form is valid
        return {isValid: true};
    }
}

CodeNode.template = "CodeNode";
CodeNode.components = {...ConfigurationBase.components, CharField, Record, AceField, CodeEditor};