/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
/**
 * Custom Odoo component for image badge selection.
 */
export class ImageBadgeSelection extends Component {
    static template = "cyllo_sms_gateway.ImageBadge";
    static props = {
        ...standardFieldProps,
        domain: {
            type: Array,
            optional: true
        },
    };

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const { relation } = props.record.fields[props.name];
                return await orm.call(relation, "name_search", ["", props.domain]);
            });
            this.selectedRecord = useSpecialData(async (orm, props) => {
                const {relation } = props.record.fields[props.name];
                return await orm.searchRead(relation, props.domain, ['image_128']);
            });
        }
    }
    get options() {
        if (this.type === "many2one") {
            return this.specialData.data;
        }
    }
    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    get image() {
        return this.selectedRecord.data;
    }
    stringify(value) {
        return JSON.stringify(value);
    }
    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.type) {
            case "many2one":
                if (value === false) {
                    this.props.record.update({
                        [this.props.name]: false
                    });
                } else {
                    this.props.record.update({
                        [this.props.name]: this.options.find((option) => option[0] === value),
                    });
                }
                break;
            case "selection":
                this.props.record.update({
                    [this.props.name]: value
                });
                break;
        }
    }
}
/**
 * Custom Odoo field for image badge selection.
 */
export const imageSelectionField = {
    component: ImageBadgeSelection,
    displayName: _t("Badges"),
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: (fieldInfo, dynamicInfo) => ({
        domain: dynamicInfo.domain(),
    }),
};

registry.category("fields").add("image_badge", imageSelectionField);
