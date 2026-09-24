/** @odoo-module **/

/**
 * StatusBar
 *
 * Component to manage and edit the status bar section of a form view in Odoo Studio.
 * Allows users to open a dialog to configure status bar fields and properties.
 *
 * Features:
 *   - Tracks visibility based on form sheet presence.
 *   - Listens to Studio editing events to prevent conflicting edits:
 *       - Button editing
 *       - Smart button editing
 *       - General Studio edits
 *   - Opens `StatusBarDialog` for adding or modifying fields.
 *
 * Props:
 *   - fields: Object containing the form fields available for the status bar.
 *   - viewId: Number representing the current view ID.
 *   - model: String with the current model name.
 *   - path: String representing the XPath of the status bar container.
 *   - header: String for the status bar header label.
 *
 * State:
 *   - isVisible: Boolean indicating whether the status bar component should be visible.
 *   - isEditingButton: Boolean tracking if a button is being edited.
 *   - isEditingSmartButton: Boolean tracking if a smart button is being edited.
 *   - isStudioEdit: Boolean tracking if Studio is in editing mode.
 *
 * Methods:
 *   - onClick(): Validates the current editing state and opens the `StatusBarDialog`.
 *
 * Usage:
 *   Used inside Odoo Studio form view editor to allow configuring status bar fields and interactions.
 */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { StatusBarDialog } from "@cyllo_studio/js/views/cyllo_form/status_bar/statusbar_dialog";
import { useState,onMounted } from "@odoo/owl";
import { validateEdit } from "@cyllo_studio/js/root/studio_wrapper";

export class StatusBar extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.notification = useService("effect");
        this.state = useState({
            isVisible: true,
            isEditingButton: false,
            isEditingSmartButton : false,
        })
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
    onClick() {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingButton", "Button") ||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button") ||
            !validateEdit(this.state, notification, "isStudioEdit", "Editing")
        ) {
            return;
        }

        this.dialogService.add(StatusBarDialog,{
            fields: this.props.fields,
            path: this.props.path,
            viewId: this.props.viewId,
            model: this.props.model,
            header: this.props.header,
            activeFields: this.env.model.config.activeFields,
        })
    }
}
StatusBar.template = "cyllo_studio.StatusBar";
StatusBar.props = { fields: Object, viewId: { type: [Number, String, Boolean], optional: true },
                    model: String, path: String, header: String }
