/** @odoo-module */

import { Chatter } from "@mail/core/web/chatter";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useService, useBus } from "@web/core/utils/hooks";
import { Message } from "@mail/core/common/message";
import { useState , useRef } from "@odoo/owl";

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    async setup() {
        super.setup();
        this.orm = useService("orm");
        var self =this
        if (this.thread.type === "chat") {
        await this.orm.call("discuss.channel", "action_find_partner_fb", [this.thread.id], {}).then(function(data) {
        if (data.partner && data.facebook){
        self.fb_discuss_sent=true
        self.state.partner=data.partner
        }
           })
           }
        this.state.fb_sent=false
        this.state.model=this.thread.model
        this.state.res_id=this.thread.id
    },
    onChangeFbCheckbox(){
        if(this.state.fb_sent){
            this.state.fb_sent=false
        }
        else{
            this.state.fb_sent=true
        }
    },
    async sendMessage() {
        var self=this
        await super.sendMessage();
        if(self.state.fb_sent){
            await this.orm.call("res.partner", "action_message_partner_fb", [self.state.res_id,this.value], {})
        }
        if(self.fb_discuss_sent){
            await this.orm.call("discuss.channel", "action_message_chat_discuss_fb", [self.state.res_id,this.value], {})
        }
    },
});