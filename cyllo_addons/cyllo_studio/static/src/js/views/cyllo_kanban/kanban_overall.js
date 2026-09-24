/** @odoo-module **/

/**
 * KanbanOverall
 *
 * This component provides the overall configuration panel for Kanban views
 * in Cyllo Studio. It allows users to manage global Kanban settings,
 * including field selection, color pickers, ribbons, progress bars,
 * menu configuration, and visibility toggles.
 *
 * Key Features:
 * 1. Kanban Field Management:
 *    - Provides a dropdown to select and validate fields for ribbons and cards.
 *    - Supports dynamic updates of field selections with validation.
 *
 * 2. View Settings Toggle:
 *    - Allows toggling of Kanban view options such as 'create', 'quick create',
 *      'records draggable', and 'groups draggable'.
 *    - Updates are persisted via RPC calls and stored for undo/redo functionality.
 *
 * 3. Menu Configuration:
 *    - Supports adding or removing the Kanban menu dynamically.
 *
 * 4. Color Picker Management:
 *    - Allows adding/removing color pickers for Kanban cards.
 *    - Handles server-side updates and undo/redo tracking.
 *
 * 5. Ribbon and Progress Bar Dialogs:
 *    - Opens RibbonDialog to edit Kanban ribbons.
 *    - Opens ProgressBarDialog to configure progress bars on Kanban cards.
 *
 * 6. Field Visibility Toggle:
 *    - Provides an 'invisible' toggle to hide/show fields dynamically.
 *    - Syncs toggle state with session storage and backend via RPC.
 *
 * 7. Notifications and Feedback:
 *    - Uses notification service to show success or warning messages.
 *
 * Dependencies:
 * - OWL hooks: useState, onWillStart.
 * - Services: rpc, action, dialog, effect.
 * - CylloStudioDropdown, RibbonDialog, ProgressBarDialog.
 * - Utility functions: validateField, sortBy.
 *
 * Purpose:
 * Enhances the overall Kanban configuration experience in Cyllo Studio,
 * enabling users to customize cards and view-level settings interactively
 * while maintaining undo/redo history and real-time server updates.
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { sortBy } from "@web/core/utils/arrays";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { validateField } from "@cyllo_studio/js/actions/utils";
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";
import { ProgressBarDialog } from "@cyllo_studio/js/view_editor/kanban/progressbar_dialog";
import { useService } from "@web/core/utils/hooks";



export class KanbanOverall extends Component {
  static template = "cyllo_studio.KanbanOverall";
  setup() {
    this.rpc = useService("rpc");
    this.action = useService("action")
    this.dialogService = useService("dialog");
    this.notification = useService('effect')
    this.state = useState({
            invisible: false,
        });
    onWillStart(() => {
        const invisible_session =  sessionStorage.getItem('invisible');
            if(invisible_session){
                this.state.invisible = true
            }
        });
    }

    /**
     * Builds a sorted dropdown list of available Kanban fields.
     * Validates fields before including them.
     *
     * @returns {Array} List of { value, label } objects.
     */
  get kanbanFields() {
    const fields = [];
    for (const [fieldName, field] of Object.entries(this.props.allFields)) {
      if (validateField(fieldName, field)) {
        fields.push({ value: fieldName, label: field.string });
      }
    }
    return [{ value: "", label: "Default"}, ...sortBy(fields, "label")];
  }

  /**
     * Handles toggling Kanban view options such as:
     * - create
     * - quick_create
     * - records_draggable
     * - groups_draggable
     *
     * Persists changes via RPC, updates undo/redo history,
     * and triggers a Studio reload.
     */
    async handleKanbanView(name, value) {
        const toggleStates = {
            'create': 'KanbanCreate',
            'quick_create': 'quickCreate',
            'records_draggable': 'recordsDraggable',
            'groups_draggable': 'groupsDraggable',
        };

        if (toggleStates[name]) {
            this.state[toggleStates[name]] = !this.state[toggleStates[name]];
        }

        const response = await this.rpc("cyllo_studio/edit/kanban_view", {
            view_id: this.props.viewId,
            view_type: this.props.viewType,
            model: this.props.model,
            name,
            value,
        });

        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }

        try {
            this.notification.add({
                title: _t("Success"),
                message: "Changes Added.",
                description: "Exit Studio Mode To View Changes",
                type: "notification_panel",
                notificationType: "success",
                time: 1000,
            });
        } finally {
            this.action.doAction('studio_reload');
        }
    }
    /**
     * Adds or removes the Kanban menu.
     * Updates the backend and refreshes the Studio view.
     *
     * @param {boolean} isAdd - Whether to add (true) or remove (false).
     */
    async menuEditor(isAdd=false){
        this.env.services.ui.block();
//        this.env.services.ui.block();
        const url = isAdd ? 'add' : 'remove'
        const message = isAdd ? 'Kanban menu added' : 'Kanban menu removed'
        try {
            await this.rpc(`cyllo_studio/kanban/${url}/menu`,{
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                model: this.props.model
            })
             this.notification.add({
                title: _t("Success"),
                message,
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
          this.env.services.ui.unblock();
//          this.env.services.ui.unblock();
        }
        this.action.doAction('studio_reload')
    }

        /**
     * Adds a color picker field to Kanban cards.
     * Creates `color` or `x_cy_color` if needed.
     * Updates backend, undo/redo, and refreshes Studio view.
     */
    async addColorPicker(){
        let hasField = false
        let field = 'x_cy_color'
        if(this.props.allFields.hasOwnProperty('color')){
            hasField = true
            field = 'color'
        } else if(this.props.allFields.hasOwnProperty('x_cy_color')){
            hasField = true
        }
        this.env.services.ui.block();

        try {
            const response = await this.rpc('cyllo_studio/kanban/add/color_picker',{
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                model: this.props.model,
                has_field: hasField,
                field,
            })
            if(response){
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        this.notification.add({
                title: _t("Success"),
                message: "Color Picker added.",
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
          this.env.services.ui.unblock();
        }
        this.action.doAction("studio_reload");
    }

        /**
     * Removes the color picker field from Kanban cards.
     * Cleans up backend and updates undo/redo state.
     */

    async removeColorPicker(){
        this.env.services.ui.block();
        try {
            const response =  await this.rpc('cyllo_studio/kanban/remove/color_picker',{
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                model: this.props.model,
                path: this.props.colorPickerPath,
            })
            if(response){
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
             }
        this.notification.add({
                title: _t("Success"),
                message: "Color Picker removed.",
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
          this.env.services.ui.unblock();
        }
        this.action.doAction("studio_reload");
    }

     /**
     * Opens the ProgressBarDialog for configuring Kanban progress bars.
     */
    editRibbon(){
        this.dialogService.add(RibbonDialog,{
           fields: this.kanbanFields,
           ribbonElement: this.props.ribbonElement,
           viewDetails: {
               viewId: this.props.viewId,
               viewType: this.props.viewType,
               model: this.props.model,
               active_fields:this.props.allFields,
           },
       })
    }

    /**
     * Opens the ProgressBarDialog for configuring Kanban progress bars.
     */
    openProgressBar(){
         this.dialogService.add(ProgressBarDialog,{
            fields: this.props.allFields,
            progressAttributes: this.props.progressAttributes,
            viewDetails: {
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                model: this.props.model,
            },
        })
    }
    /**
     * Handles the 'invisible' toggle state for fields.
     * Syncs value with session storage and backend via RPC.
     *
     * @param {Event} ev - Input change event.
     */
    async handleInvisibleClick(ev){
         if(ev.target.checked){
            this.state.invisible=true
            sessionStorage.setItem('invisible', !this.state.invisible);
       }else{
            this.state.invisible=false
            sessionStorage.removeItem('invisible');
       }
        await this.rpc("cyllo_studio/set/session", {
          key: 'invisible',
          value: this.state.invisible,
        })
    }
    async deleteProgressBar(){
        this.env.services.ui.block();
        try {
        const response=await this.rpc('cyllo_studio/kanban/remove/progressbar',{
        view_id: this.props.viewId,
        view_type: this.props.viewType,
        model: this.props.model,
        })
        if(response){
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
             }

        this.notification.add({
            title: _t("Success"),
            message: "Progressbar deleted.",
            type: "notification_panel",
            notificationType: "success",
        });
        } finally {
        this.env.services.ui.unblock();
        this.action.doAction("studio_reload");
        }
        this.action.doAction("studio_reload");

    }


}
KanbanOverall.components = {
  CylloStudioDropdown,
};
