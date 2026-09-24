/** @odoo-module **/
import {Dropdown} from '@web/core/dropdown/dropdown';
import {DropdownItem} from '@web/core/dropdown/dropdown_item';
import {MessagingMenu} from "@mail/core/web/messaging_menu";
import {NotificationItem} from "@mail/core/web/notification_item";
import {useService} from '@web/core/utils/hooks';
import {registry} from '@web/core/registry';
import {onRendered} from '@odoo/owl';

export class InstagramIcon extends MessagingMenu {
    async setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
        onRendered(() => {
            this.ig_counter = 0
            if (this.threads[0]) {
                for (let i = 0; i < this.threads.length; i++) {
                    if (this.threads[i].description == "INSTAGRAM") {
                        this.ig_counter = this.ig_counter + this.threads[i].message_unread_counter
                    }
                }
            }
        });
        this.state.partner_insta_chats = await this.orm.searchRead("res.partner", [['is_insta_chat', '=', true]], ['name', 'id', 'insta_chat', 'insta_chat_time']);

    }

    openFormInsta(ev) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: ev,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
    }
}

InstagramIcon.template = 'cyllo_instagram.InstagramIcon';
InstagramIcon.components = {Dropdown, DropdownItem, NotificationItem, MessagingMenu};
export const InstagramIconItems = {
    Component: InstagramIcon,
};
registry.category('systray').add('InstagramIcon', InstagramIconItems, {sequence: 1000});
