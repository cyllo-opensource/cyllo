/** @odoo-module **/

/**
 * CylloFormLabel
 *
 * Extends the default Odoo FormLabel to provide Studio editing capabilities
 * in a safe way, preventing edits during button or smart button editing.
 *
 * Features:
 *  - Tracks whether Button, Smart Button, or Studio editing is active.
 *  - Validates edit permissions using `validateEdit` before triggering events.
 *  - Emits `FIELDS_DETAILS` event with all relevant field metadata for Studio.
 *
 * Props:
 *  - cyXpath (optional): The xpath of the field for Studio tracking.
 *
 * Methods:
 *  - onItemClick(e): Handles clicks on the label. Validates editing state and
 *    triggers the `FIELDS_DETAILS` bus event with metadata such as field path,
 *    label path, type, placeholder, widget, context, visibility, and other attributes.
 */
import { useState} from "@odoo/owl";
import { FormLabel } from "@web/views/form/form_label";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { validateEdit } from "@cyllo_studio/js/root/studio_wrapper";

export class CylloFormLabel extends FormLabel {
    static template = 'cyllo_studio.FormLabel'
    setup() {
        super.setup();
        this.notification = useService("effect");
        this.state = useState({
            isEditingButton: false,
            isEditingSmartButton: false,
            isStudioEdit: false,
        });
        this.env.bus.addEventListener("BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingButton = detail.isEditingButton
        })
         this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
        this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
        })

    }
    /**
     * Handle click on the label.
     * Validates edit state and triggers Studio event with field metadata.
     * @param {MouseEvent} e - Click event
     */

    onItemClick(e) {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingButton", "Button") ||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button")
            //            !validateEdit(this.state, notification, "isStudioEdit", "Editing")
        ) {
            return;
        }
        this.env.bus.trigger("FIELDS_DETAILS", {
            type: "Properties",
            field_path: this.props.fieldInfo.MainPath,
            label_path: this.props.cyXpath,
            name:this.props.fieldInfo.name || "",
            label: this.props.string || "",
            fieldType: this.props.fieldInfo.type || "",
            placeholder: this.props.fieldInfo.attrs.placeholder || "",
            dynamic_placeholder: this.props.fieldInfo.attrs.dynamic_placeholder || "",
            help: this.props.fieldInfo.help || "",
            domain: this.props.fieldInfo.domain || "",
            edit:true,
            widget: this.props.fieldInfo.widget || "",
            context: this.props.fieldInfo.context || "",
            invisible : this.props.fieldInfo.invisible || "",
            readonly: this.props.fieldInfo.readonly || "",
            required: this.props.fieldInfo.required || "",
            options: this.props.fieldInfo.options
        });
    }

}
CylloFormLabel.props = {
    ...FormLabel.props,
    cyXpath: {
        type: String,
        optional: true
    },
    striped: {
        type: Boolean,
        optional: true
    }
};
