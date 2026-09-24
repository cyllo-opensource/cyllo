/** @odoo-module */
import {registry} from "@web/core/registry";
import {CharField, charField} from "@web/views/fields/char/char_field";
import {_t} from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";

export class Password extends CharField {
    static template = "Password"
    static defaultProps = {
        ...charField.defaultProps,
        placeholder: "Password"
    }

    setup() {
        super.setup()
        useAutofocus({ refName: "input"})
    }
}

export const password = {
    ...charField,
    component: Password,
    displayName: _t("Password"),
};

registry.category('fields').add('password', password);