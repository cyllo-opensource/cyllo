/** @odoo-module **/
import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ColorPicker extends Component {
    static props = { ...standardFieldProps };
    setup() {
        super.setup();
        this.ColorChar = useRef('ColorChar');
        this.ColorCode = useRef('ColorCode');
    }
    get value() {
        return this.props.record.data[this.props.name];
    }
    get isReadonly() {
        return this.props.readonly;
    }
    //  Function to change color code on input type field
    changeColorCode() {
        this.ColorCode.el.value = this.ColorChar.el.value;
        this.props.record.update({[this.props.name]: this.ColorChar.el.value});
    }
    //  Function to change color picker based on the value in input field
    changeColor() {
        this.ColorChar.el.value = this.ColorCode.el.value;
        this.props.record.update({ [this.props.name]: this.ColorCode.el.value });
    }
    //  Function to prevent default function if the field is readonly
    clickColorPicker(ev) {
        if (this.props.readonly) {
            ev.preventDefault();
        }
    }
};
ColorPicker.template = "cyllo_color_picker_widget.CylloColorPicker";
export const colorPicker = {
    component: ColorPicker,
    displayName: _t("Color Picker"),
    supportedTypes: ["char"],
};
registry.category("fields").add("colorpicker", colorPicker);