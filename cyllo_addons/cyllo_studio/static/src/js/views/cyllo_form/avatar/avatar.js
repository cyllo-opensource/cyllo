/** @odoo-module **/

/**
 * AvatarComponent
 *
 * A reusable component for displaying and editing avatar images in Odoo Studio forms.
 * It handles conditional visibility, prevents editing conflicts, and opens
 * the AvatarDialog for modifying avatar fields.
 *
 * Features:
 *  - Shows/hides the avatar based on the form sheet attribute.
 *  - Listens for editing events to prevent conflicts with Buttons, Smart Buttons, or Studio edits.
 *  - Opens the AvatarDialog to edit avatar-related fields.
 *
 * Props:
 *  - fields: Object containing field definitions for the avatar
 *  - path: String representing the field path in the form
 *  - viewId: Number, current view ID
 *  - model: String, model name of the current record
 */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AvatarDialog } from "@cyllo_studio/js/views/cyllo_form/avatar_dailog/avatar_dialog";
import { useState,onMounted } from "@odoo/owl";
import { validateEdit } from "@cyllo_studio/js/root/studio_wrapper";
export class AvatarComponent extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.notification = useService("effect");
        this.state = useState({
            isVisible : true,
            isEditingButton: false,
            isEditingSmartButton : false,
            isStudioEdit : false,
        });
        onMounted(() => {
            const sheet = document.querySelector('.o_form_sheet')?.getAttribute('sheet')
            if(sheet){
                this.state.isVisible = false
            }
        })
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
     * onClick
     *
     * Opens the AvatarDialog to edit avatar fields.
     * Validates that no conflicting edits are active before opening.
     */
    onClick() {
    const notification = this.notification || useService("notification");

    if (
        !validateEdit(this.state, notification, "isEditingButton", "Button") ||
        !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button") ||
        !validateEdit(this.state, notification, "isStudioEdit", "Editing")
    ) {
        return;
    }

    this.dialogService.add(AvatarDialog, {
        fields: this.props.fields,
        path: this.props.path,
        viewId: this.props.viewId,
        model: this.props.model,
    });
}

}
AvatarComponent.template = "cyllo_studio.AvatarComponent";
AvatarComponent.props = { fields: Object, viewId: { type: [Number, String, Boolean], optional: true },
model: String, path: String }
