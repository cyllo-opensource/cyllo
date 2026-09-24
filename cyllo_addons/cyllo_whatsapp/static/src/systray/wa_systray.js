/** @odoo-module **/
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { NotificationItem } from "@mail/core/web/notification_item";
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from '@web/core/registry';
import { renderToElement } from "@web/core/utils/render";
import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import { Component, onWillStart, useState, useRef } from '@odoo/owl';
import { session } from '@web/session';

/* Add new class SwitchLanguageMenu on systray */
export class WhatsappIcon extends MessagingMenu {
    async setup() {
        super.setup(...arguments);
        this.searchBox = useRef('searchBox')
        this.whatsapp_window = useRef('whatsapp_window')
        this.chatWindowService.whatsapp=0
        this.actionService = useService("action")
        this.rpc = useService("rpc");
        this.state = useState({channel: {},
            messages: {},
            partnerHistory: {},
            countVisible: false,
            id: false,
            counter: 0,
            right: 0
        })
        this.orm = useService('orm')
        onWillStart(async () => {
            try {
                var model = await this.rpc("/check_model/whatsapp", {})
            } catch (e) {
                var model = false
            }
            if (model) {
                this.state.channel = await this.orm.searchRead("whatsapp.channel", [
                    ['user_id', '=', session.uid]
                ], []);
                this.state.channel.forEach((channel) => (
                    this.state.counter += channel.message_count
                ));
            }
        });
        this.busService = this.env.services.bus_service
        this.channel = "WHATSAPP-CHANNEL"
        this.busService.addChannel(this.channel)
        this.busService.addEventListener("notification", this.onMessageCount.bind(this))
        useBus(this.env.bus, 'UPDATE_COUNTER', (channel) => this.counterUpdate());
    }

    async counterUpdate() {
        try {
            var model = await this.rpc("/check_model/whatsapp", {})
        } catch (e) {
            var model = false
        }
        if (model) {
            this.state.channel = await this.orm.searchRead("whatsapp.channel", [
                ['user_id', '=', session.uid]
            ], []);
            this.state.counter = 0
            this.state.channel.forEach((channel) => (
                this.state.counter += channel.message_count
            ));
        }
    }

    async onMessageCount(message) {
        if (message.detail[0].type == 'notification') {
            try {
                var model = await this.rpc("/check_model/whatsapp", {})
            } catch (e) {
                var model = false
            }
            if (model) {
                this.state.channel = await this.orm.searchRead("whatsapp.channel", [
                    ['user_id', '=', session.uid]
                ], []);
                this.state.counter = 0
                this.state.channel.forEach((channel) => (
                    this.state.counter += channel.message_count
                ));
            }
        }
    }

    getChannel(channel) {
        var self = this
        this.state.id = channel.id
        return this.actionService.doAction("cyllo_whatsapp.whatsapp_action", {}).then(function(data) {
            self.state.countVisible = true
            self.env.bus.trigger('CLICK_PARTNER', {
                event: event,
                partner: channel
            })
        })
    }

    async onSelectPartner(partner) {
        var self = this
        var desiredChannel = false
        self.searchBox.el.value = ""
        self.whatsapp_window.el.classList.add("d-none")
        var whatsappChannels = await self.orm.searchRead("whatsapp.channel", [
            ['user_id', '=', session.uid]
        ], []);
        desiredChannel = whatsappChannels.find(channel => channel.partner_id[0] === partner.id);
        if (!desiredChannel) {
            var ChannelValues = {
                'name': partner.name,
                'partner_id': partner.id,
                'user_id': session.uid
            }
            var desiredChannelId = await this.orm.create("whatsapp.channel", [ChannelValues], {});
            desiredChannel = await this.orm.read("whatsapp.channel", [desiredChannelId[0]], []);
            return this.actionService.doAction("cyllo_whatsapp.whatsapp_action", {}).then(async function(data) {
                self.state.countVisible = true
                self.env.bus.trigger('CLICK_PARTNER', {
                    event: event,
                    partner: desiredChannel[0]
                })
                self.searchBox.el.value = ""
            })
        }
        return this.actionService.doAction("cyllo_whatsapp.whatsapp_action", {}).then(async function(data) {
            self.state.countVisible = true
            self.env.bus.trigger('CLICK_PARTNER', {
                event: event,
                partner: desiredChannel
            })
        })
    }

    configureChats() {
        this.state.right = CHAT_WINDOW_END_GAP_WIDTH + (this.chatWindowService.visible.length * (CHAT_WINDOW_WIDTH + CHAT_WINDOW_END_GAP_WIDTH))
        if (this.whatsapp_window.el.classList.contains("d-none")) {
                this.chatWindowService.whatsapp=this.chatWindowService.whatsapp+1
            this.whatsapp_window.el.classList.remove("d-none")
        } else {
            this.whatsapp_window.el.classList.add("d-none")
                    this.chatWindowService.whatsapp=this.chatWindowService.whatsapp-1
        }
    }

    async onKeyUpSearch(ev) {
        if (this.searchBox.el.value) {
            this.state.partnerHistory = await this.orm.searchRead(
                "res.partner",
                [
                    ["name", "ilike", this.searchBox.el.value],
                    ["whatsapp_number", "!=", null],
                ],
                []
            );
        } else {
            this.state.partnerHistory = {}
        }
    }
}

WhatsappIcon.template = 'cyllo_whatsapp.WhatsappIcon';
WhatsappIcon.components = {
    Dropdown,
    DropdownItem,
    NotificationItem,
    MessagingMenu
};
export const WhatsappIconItems = {
    Component: WhatsappIcon,
};
registry.category('systray').add('WhatsappIcon', WhatsappIconItems, {
    sequence: 1
});