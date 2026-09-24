/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, {
    openNewMessage({ openMessagingMenuOnClose,facebook,instagram } = {}) {
    this.store.facebook=false
    this.store.instagram=false
     if (facebook){
        this.store.facebook=true
        this.store.instagram=false
    }
    if (instagram){
        this.store.facebook=false
        this.store.instagram=true
    }
        if (this.store.discuss.chatWindows.some(({ thread }) => !thread)) {
            return;
        }
        this.store.ChatWindow.insert(assignDefined({}, { openMessagingMenuOnClose }));
    }

});