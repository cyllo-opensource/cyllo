/** @odoo-module **/


/**
 * Chatter Patch for Cyllo Studio
 *
 * Extends the default Odoo Chatter to provide Studio-specific functionality:
 *  - Ability to remove Chatter from a form view via dialog
 *  - Prevent removal if Chatter attachments preview is active
 *  - Display notifications when removal is not allowed
 *
 * Props:
 *  - cyXpath: optional string, the xpath of the Chatter in the view
 *
 * Services:
 *  - dialogService: to open ChatterDialog
 *  - notification: to display warning messages
 *
 * Events:
 *  - Opens ChatterDialog to remove Chatter if allowed
 */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/core/web/chatter";
import {ChatterDialog} from'./chatter_dialog';
import {  onMounted } from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";

Chatter.props = [...Chatter.props, 'cyXpath?']

patch(Chatter.prototype, {
  setup() {
    /**
     * Setup the Chatter patch
     * Initializes dialog and notification services
     */
    super.setup();
        this.dialogService = useService("dialog")
            this.notification = useService('effect')
      onMounted(() => {
        const preview = document.querySelector('o_attachment_preview')
      })
    },
    /**
     * Handle click event to remove Chatter
     * @param {Event} ev - The click event
     * @param {String} position - Position information of the Chatter
     */
    async onClick(ev,position) {
        const preview = document.querySelector('.chatter-preview')
        if(!preview){
          this.dialogService.add(ChatterDialog, {
            title: 'Remove Chatter',
            model: this.env.model.config.resModel,
            view_id: this.env.config.viewId,
            path:this.props.cyXpath,
            position: position,
        });
        }else{
           this.notification.add({
                    title: _t("Unable To Remove Chatter"),
                    message: "You Cannot Remove Chatter In This Model.",
                    type: "notification_panel",
                    notificationType: "warning",
            });
        }

    }

});

Chatter.components = {
   ...Chatter.components,

}