/** @odoo-module **/

/**
 * AvatarDialog
 *
 * Dialog component for adding or selecting avatar fields in Odoo Studio forms.
 * Users can either select an existing binary field or create a new one.
 *
 * Features:
 *  - List existing binary fields that are stored in the model.
 *  - Generate valid technical names for new fields.
 *  - Validate input for required fields.
 *  - Sends RPC requests to create or link avatar fields.
 *  - Updates Undo/Redo session storage for Studio actions.
 *
 * Props:
 *  - fields: Object containing all fields of the current model
 *  - path: String, the field path in the form view
 *  - viewId: Number, ID of the current view
 *  - model: String, name of the current model
 *  - close: Function to close the dialog
 */
import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { Dialog } from "@web/core/dialog/dialog";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";


export class AvatarDialog extends Component {
    static template = "cyllo_studio.AvatarDialog";
    static components = {
        Dialog,
        CylloStudioDropdown
    };
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
        this.state = useState({
            field: "existing",
            existingFieldTech: "",
            newFieldLabel: "",
            newFieldTechName: "",
        })
    }

    /**
     * Returns a list of stored binary fields from the model.
     */
    get existingFields() {
        const binaryFields = Object.entries(this.props.fields)
            .filter(([key, field]) => field.type === "binary" && field.store)
            .map(([key, field]) => ({ name: field.name, string: field.string }));
        return binaryFields
    }

    /**
     * Handle input for new field label.
     * Automatically updates the technical name if not manually overridden.
     */
    onInputLabel(ev) {
        if (!this.state.newFieldTechName || this.state.newFieldTechName == this.processTechName(this.state.newFieldLabel)) {
            this.onInputTechName(ev)
        }
        this.state.newFieldLabel = ev.target.value
    }

    /**
     * Handle input for new field technical name.
     */
    onInputTechName(ev) {
        let inputValue = ev.target.value;
        this.state.newFieldTechName = this.processTechName(inputValue);
    }

    /**
     * Converts a string into a valid Odoo technical field name.
     * Replaces spaces with underscores, removes invalid characters, and lowercases.
     */
    processTechName(inputValue) {
        inputValue = inputValue.replace(/ /g, "_");
        inputValue = inputValue.replace(/[^a-zA-Z0-9_]/g, "");
        return inputValue.toLowerCase()
    }

    /**
     * Maps existing binary fields to the dropdown format.
     */
    avatarExistingFields(array){
        const result = array.map(item => ({ value: item.name, label:item.string }));
        return result
    }

    handleAvatarExistingFields(value) {
        this.state.existingFieldTech = value;
    }

    get defaultAvatarExistingField() {
        return this.state.existingFieldTech
     }

    /**
     * Confirm the selection or creation of the avatar field.
     * Sends RPC request to create or link field, updates Undo/Redo, and reloads Studio view.
     */
    async onConfirm() {
        if (this.state.field === 'existing') {
            if (!this.state.existingFieldTech) {
                return this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Select an existing field',
                        'type': 'warning',
                        'sticky': false,
                    }
                })
            }
            this.env.services.ui.block();
            try{
               const response =  await this.rpc("cyllo_studio/add/avatar", {
                    path: this.props.path,
                    view_id: this.props.viewId,
                    is_new: false,
                    model: this.props.model,
                    view_type: "form",
                    field: {
                        name: this.state.existingFieldTech,
                        }
                })
              if(response){
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr)
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
            } finally {
                this.env.services.ui.unblock();
            }
            this.action.doAction('studio_reload')
        } else {
            if (!this.state.newFieldLabel || !this.state.newFieldTechName) {
                return this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Both fields are required',
                        'type': 'warning',
                        'sticky': false,
                    }
                })
            }
             this.env.services.ui.block();
            try{
                const response = await this.rpc("cyllo_studio/add/avatar", {
                    path: this.props.path,
                    view_id: this.props.viewId,
                    is_new: true,
                    model: this.props.model,
                    view_type: "form",
                    field: {
                        name: "x_cy_" + this.state.newFieldTechName,
                        label: this.state.newFieldLabel
                        }
                })
              if(response){
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr)
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                 }
            } finally {
                this.env.services.ui.unblock();
            }
            this.action.doAction('studio_reload')
        }
        this.props.close()
    }
    onDiscard() {
        this.props.close();
    }
}