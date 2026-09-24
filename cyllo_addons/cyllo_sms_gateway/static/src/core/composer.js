/* @odoo-module */
import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    /**
     * Send an SMS message and open a new window for sending SMS.
     */
    async sendSMS() {
        await this.processMessage(async (value) => {
            const postData = {
                attachments: this.props.composer.attachments,
                isNote: this.props.type === "note",
                rawMentions: this.props.composer.rawMentions,
                cannedResponseIds: [...this.props.composer.cannedResponseIds],
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            await this._sendMessage(value, postData);
            // Collect follower partner IDs
            const followerIds = [];
            for (const follower of this.thread.followers) {
                followerIds.push(follower.partner.id);
            }
            // Define the action to open the 'Send SMS' form
            const action = {
                name: 'Send SMS',
                type: "ir.actions.act_window",
                res_model: "send.sms",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    'default_text': value,
                    'default_partner_ids': followerIds,
                },
            };
            // Open the 'Send SMS' form
            await this.env.services.action.doAction(action);
        });
    },
});
