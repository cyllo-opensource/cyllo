/** @odoo-module **/
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { NotificationItem } from "@mail/core/web/notification_item";
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from '@web/core/registry';
import { Component, onWillStart,onRendered, onMounted,useState } from '@odoo/owl';
import { session } from '@web/session';

export class FacebookIcon extends MessagingMenu {
    async setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
        onRendered(() => {
            this.fb_counter=0
            if (this.threads[0]){
                for (let i = 0; i < this.threads.length; i++) {
                    if (this.threads[i].description=="FACEBOOK"){
                        this.fb_counter=this.fb_counter+this.threads[i].message_unread_counter
                    }
                }
            }
        });
        this.state.partner_chats = await this.orm.searchRead("res.partner",[['is_fb_chat','=',true]] , ['name','id','fb_chat','fb_chat_time','image_1920']);
    }
    openForm(ev){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: ev,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
    }
}
FacebookIcon.template = 'cyllo_facebook.FacebookIcon';
FacebookIcon.components = {Dropdown, DropdownItem ,NotificationItem,MessagingMenu};
export const FacebookIconItems = {
    Component: FacebookIcon,
};
registry.category('systray').add('FacebookIcon', FacebookIconItems, {sequence: 1000});