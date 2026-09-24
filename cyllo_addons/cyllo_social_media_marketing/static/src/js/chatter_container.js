/** @odoo-module **/
import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { patch } from "@web/core/utils/patch";
import { useService, useBus } from "@web/core/utils/hooks";
import { Message } from "@mail/core/common/message";
import { useState , useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(Message, {
    components: { ...Message.components },
});

patch(Message.prototype, {
    setup() {
        super.setup();
        this.reply=useRef('message_reply')
        this.reply_section=useRef('reply_section')
        this.actionService = useService("action");
        this.messagePinService = useState(useService("discuss.message.pin"));
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.threadService = useService("mail.thread");
    },
    async createLead() {
        var self= this
        await this.orm.call("mail.message", "action_create_lead", [this.message.id], {}).then(function(data) {
            if (data){
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    res_id: data,
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
            }
            else{
                self.notificationService.add(_t('This is an internal message, Nothing to convert it is a lead'),
                    { type: "info" }
                );
            }
        })
    },
    onClickReply(ev){
        var style=ev.target.nextElementSibling.style
        if (style.display == 'none') {
            this.reply_section.el.style.display = 'block'
        } else {
            this.reply_section.el.style.display='none'
        }
    },
    async postReply(ev){
        var self =this
        await this.orm.call("mail.message", "action_reply_message_chatter",
            [this.message.id,ev.target.value,this.reply.el.value,this.message.res_id], {}
        )
        self.reply_section.el.style.display='none'
        self.reply.el.value=''
        var thread_refresh=this.threadService.getThread('crm.lead',this.message.res_id)
        this.threadService.fetchNewMessages(thread_refresh);
    }
});

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async sendMessage() {
        await this.processMessage(async (value) => {
            const postData = {
                attachments: this.props.composer.attachments,
                isNote: this.props.type === "note",
                mentionedChannels: this.props.composer.mentionedChannels,
                mentionedPartners: this.props.composer.mentionedPartners,
                cannedResponseIds: this.props.composer.cannedResponses.map((c) => c.id),
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            this.value=value
            await this.orm.call("mail.message", "action_reply_message", [postData['parentId'],value], {})
            await this._sendMessage(value, postData);
        });
        await super.sendMessage();
    },
});