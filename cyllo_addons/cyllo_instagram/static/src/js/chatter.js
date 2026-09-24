/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useService } from "@web/core/utils/hooks";

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    async setup() {
        super.setup();
        this.orm = useService("orm");
        var self =this
        if (this.thread.type === "chat") {
            await this.orm.call("discuss.channel", "action_find_partner_insta", [this.thread.id], {}).then(function(data) {
               if (data.partner && data.instagram){
            self.insta_discuss_sent=true
            self.partner=data.partner
            }
           })
           }
        this.state.insta_sent=false
        this.state.model=this.thread.model
        this.state.res_id=this.thread.id
    },
    onChangeInstaCheckbox(){
        if(this.state.insta_sent){
        this.state.insta_sent=false
        }
        else{
        this.state.insta_sent=true
        }
    },
    async sendMessage() {
        const self = this;
        await super.sendMessage();
            if(self.state.insta_sent){
            await this.orm.call(
            "res.partner", "action_message_partner_insta",
            [self.state.res_id,this.value], {}
            )}
            if(self.insta_discuss_sent){
            await this.orm.call("discuss.channel", "action_message_chat_discuss_insta", [self.state.res_id,this.value], {})
        }
    },
});
