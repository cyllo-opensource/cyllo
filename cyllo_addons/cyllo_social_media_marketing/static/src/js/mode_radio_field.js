/** @odoo-module **/
import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { postPlatformAccountFields } from "./post_platform_accounts";


export class ModeRadioField extends Component {
    static template = "cyllo_social_media_marketing.ModeRadioField";
    static props = { ...standardFieldProps };

    setup() {
        useEffect(
            () => {
                const allowed = this.allowedModes;
                if (allowed.length && !allowed.includes(this.props.record.data[this.props.name])) {
                    this.props.record.update({ [this.props.name]: allowed[0] });
                }
            },
            () => [this.selectedPlatformsKey]
        );
    }

    get selectedPlatformsKey() {
        return postPlatformAccountFields
            .getEntries()
            .map(([platform, config]) => (this.props.record.data[config.boolField] ? platform : ""))
            .join("|");
    }

    get allSelectionOptions() {
        return this.props.record.fields[this.props.name].selection;
    }

    get allowedModes() {
        const selectedConfigs = postPlatformAccountFields
            .getEntries()
            .map(([, config]) => config)
            .filter((config) => this.props.record.data[config.boolField]);
        if (!selectedConfigs.length) {
            return this.allSelectionOptions.map(([value]) => value);
        }
        return selectedConfigs.reduce((commonModes, config) => {
            if (!config.allowedModes) {
                return commonModes;
            }
            return commonModes.filter((mode) => config.allowedModes.includes(mode));
        }, this.allSelectionOptions.map(([value]) => value));
    }

    get items() {
        const allowed = this.allowedModes;
        return this.allSelectionOptions.filter(([value]) => allowed.includes(value));
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    onChange(value) {
        if (this.props.readonly) {
            return;
        }
        this.props.record.update({ [this.props.name]: value });
    }
}

registry.category("fields").add("platform_filtered_mode", {
    component: ModeRadioField,
    supportedTypes: ["selection"],
});
