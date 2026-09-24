/** @odoo-module */
import {registry} from "@web/core/registry";
import {Component} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

export class LockIcon extends Component {
    static template = "LockIcon";
    static props = {
        ...standardFieldProps,
        showUnlockIcon: {type: Boolean, optional: true},
    }
    static defaultProps = {
        showUnlockIcon: false,
    }

    get value() {
        return this.props.record.data[this.props.name] || false
    }
}

export const lockIcon = {
    component: LockIcon,
    displayName: _t("Locked"),
    supportedTypes: ["boolean"],
    extractProps(fieldInfo, dynamicInfo) {
        return {
            showUnlockIcon: fieldInfo.options.show_unlock,
        };
    },
};

registry.category('fields').add('lock_icon', lockIcon);
