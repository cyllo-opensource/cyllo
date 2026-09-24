/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";
import { _t } from "@web/core/l10n/translation";


patch(Message.prototype, {
    // Setting up additional properties and services for the Message class
    // Method to create a Ticket
    async createTicket() {
        var self= this
        this.orm.call("mail.message", "action_create_ticket", [this.message.id], {}).then(function(data) {
            if (data){
                self.actionService.doAction({
                    res_model: 'support.service.ticket',
                    res_id: data,
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
            }else{
                self.notificationService.add(_t('This is an internal message, Nothing to convert it is a Ticket'),
                    { type: "info" }
                );
            }
        })
    },
    async postReply(ev){
        var self =this
        await this.orm.call(
           "mail.message", "action_reply_message_chatter",
            [this.message.id,ev.target.value,this.reply.el.value,this.message.res_id], {}
           )
        self.reply_section.el.style.display='none'
        self.reply.el.value=''
        var thread_refresh=this.threadService.getThread('crm.lead',this.message.res_id)
        this.threadService.fetchNewMessages(thread_refresh);
        thread_refresh=this.threadService.getThread('support.service.ticket',this.message.res_id)
        this.threadService.fetchNewMessages(thread_refresh);
    }
});
