/** @odoo-module **/

/**
 * KanbanFieldDialog
 *
 * This module defines a dialog component for adding existing fields to a
 * Kanban card in Cyllo Studio. It extends Odoo's OWL Component system
 * and integrates with RPC services for dynamic updates.
 *
 * Features:
 * 1. Field Selection:
 *    - Displays a dropdown list of available fields for the selected model.
 *    - Allows users to pick a field to add to the Kanban card.
 *
 * 2. RPC Integration:
 *    - Calls the `cyllo_studio/kanban/add/field` endpoint to update
 *      the Kanban view on the server side.
 *
 * 3. Undo/Redo Support:
 *    - Uses `handleUndoRedo` to manage undo/redo actions for field updates.
 *
 * 4. User Feedback:
 *    - Blocks the UI during RPC calls to prevent concurrent changes.
 *    - Shows notifications if no field is selected when confirming.
 *
 * 5. Lifecycle:
 *    - Supports confirm, close, and discard actions.
 *    - Reloads the Kanban view after any change.
 *
 * Components:
 * - Dialog: Provides modal dialog functionality.
 * - CylloStudioDropdown: Dropdown UI component for field selection.
 *
 * Purpose:
 * Enhances the Kanban editing experience in Cyllo Studio by enabling
 * easy, dynamic addition of existing model fields to Kanban cards.
 */
import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { sortBy } from "@web/core/utils/arrays";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";


export class KanbanFieldDialog extends Component {
    static template = "cyllo_studio.KanbanFieldDialog";
    static components = {
        Dialog,
        CylloStudioDropdown,
    };
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
        this.state = useState({
            field: "",
        })
    }

     get fields() {
      const allFields = [];
      for (const [fieldName, field] of Object.entries(this.props.fields)) {
        const obj = {value: fieldName, label:field.string}
        allFields.push(obj)
      }
      return sortBy(allFields, (item) => item[1]);
    }
     async onConfirm() {
        if (!this.state.field) {
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
            const viewDetails = this.props.viewDetails
            const elementInfo =  this.props.elementInfo
            const response = await this.rpc("cyllo_studio/kanban/add/field", {
                ...viewDetails,
                ...elementInfo,
                field: this.state.field,
                x2many: this.props.x2many ?  this.props.x2many + '/kanban' : '/kanban'
            })
            if(response){
                handleUndoRedo(response)
            }
        } finally {
            this.env.services.ui.unblock();
        }
        this.action.doAction('studio_reload')
        this.props.close()
    }
      updateField(value){
        this.state.field = value
    }
     onClose(){
        this.props.close();
        this.action.doAction('studio_reload')
    }
      onDiscard() {
        this.props.close();
        this.action.doAction('studio_reload')
    }

    }