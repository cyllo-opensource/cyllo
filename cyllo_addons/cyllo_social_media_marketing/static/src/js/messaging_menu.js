/* @odoo-module */

import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    setup() {
            super.setup();
            this.facebook=false
            this.instagram=false
        },
    onClickNewMessagefb() {
    this.facebook=true
    this.onClickNewMessage()
    },
    onClickNewMessageInstagram() {
this.instagram=true
    this.onClickNewMessage()
    },

    onClickNewMessage() {
        if (this.ui.isSmall || this.env.inDiscussApp) {
            this.state.addingChat = true;
        } else {
            this.chatWindowService.openNewMessage({ openMessagingMenuOnClose: true,facebook:this.facebook,instagram:this.instagram});
            this.close();
        }
    }

});