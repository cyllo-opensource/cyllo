/** @odoo-module **/

/**
 * ChatterDialog
 *
 * A dialog component used to confirm the addition or removal
 * of the Chatter section in a form view within Odoo Studio.
 *
 * Props:
 *  - model: string, the technical model name
 *  - view_id: number, the current form view ID
 *  - path: string, the xpath of the Chatter in the view
 *  - position: string, where the Chatter should be added/removed
 *
 * Components:
 *  - Dialog: Owl core dialog component
 *
 * Services:
 *  - rpc: to call server-side methods for adding/removing Chatter
 *  - action: to trigger client-side actions (e.g., reload view)
 *  - ui: used to block/unblock the UI while processing
 *
 * Methods:
 *  - confirm(): triggers the add/remove chatter RPC call, updates
 *               Undo/Redo stack, and reloads the view
 *  - onCancel(): cancels the action, reloads the view, and refreshes the page
 */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {Dialog} from "@web/core/dialog/dialog";

export class ChatterDialog extends Component {
    static template = "cyllo_studio.ChatterDialog";
    static components = {
        Dialog,
    };
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
    }
    /**
     * Confirm adding or removing the Chatter section.
     * Calls the RPC, updates Undo/Redo, triggers bus events,
     * and reloads the view.
     */
    async confirm(){
        this.env.services.ui.block();
        try{
           const response =  await this.rpc("cyllo_studio/add_remove/chatter", {
               model: this.props.model,
               view_id: this.props.view_id,
               path: this.props.path,
               view_type: "form",
               position: this.props.position,
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
         this.env.bus.trigger('restChatter')
        this.action.doAction('studio_reload')
    }
    /**
     * Cancel the action and reload the page.
     */
    onCancel(){
        this.action.doAction('studio_reload')
        window.location.reload()
    }
}
